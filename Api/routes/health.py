"""Health check endpoint (public, unauthenticated).

Provides a simple liveness/readiness probe for load balancers, monitoring,
and the installer's verification phase.

GET /health → 200 if the app can start, 503 if a critical dependency fails.

Thread-safety: uses ``threading.local()`` so each thread gets its own
connection.  A module-level ``psycopg2`` connection shared across threads
is unsafe because psycopg2 connections are not thread-safe for concurrent
cursor operations.  ``threading.local()`` gives each request-handling
thread its own connection with independent lifecycle and stale-connection
handling.

The connection is lightweight (single ``SELECT 1`` probe), not a pool.
"""

from __future__ import annotations

import concurrent.futures
import logging
import os
import threading
import time

from flask import Blueprint, jsonify

logger = logging.getLogger(__name__)

health_bp = Blueprint("health", __name__)

_start_time = time.time()


def _probe_deadline_seconds() -> float:
    """How long /health waits for its database probe, in seconds.

    Bounded on purpose: a liveness probe that waits 30 s is not a probe. The
    default is two seconds - long enough for a local connect, short enough that
    a load balancer gets an answer - and ``HEALTH_DB_TIMEOUT_SECONDS`` may move
    it, clamped so a typo cannot turn the endpoint into a hanging one.
    """
    raw = os.environ.get("HEALTH_DB_TIMEOUT_SECONDS", "2")
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return 2.0
    return max(0.2, min(value, 10.0))


#: One worker is enough for a probe; two keep a single wedged connect from
#: blocking the next request's probe as well.
_probe_executor = concurrent.futures.ThreadPoolExecutor(
    max_workers=2, thread_name_prefix="health-probe")

# Thread-local storage for health-check connections.
# Each thread (i.e., each concurrent request handler) gets its own
# psycopg2 connection.  This eliminates the shared-state race that a
# module-level connection would have under Flask's threaded mode.
_local = threading.local()

# Note: there is deliberately no module-wide "connect lock". It used to be here
# to stop a thundering herd, and it made one wedged connect block every later
# probe: during the round-4 outage injection the first probe answered 503 and
# every probe after it waited on the lock instead of answering. The probe
# executor bounds concurrent connects instead (two workers), and the endpoint's
# deadline bounds the wait.


def _get_health_connection():
    """Return a thread-local psycopg2 connection for health probes.

    Each thread gets its own connection.  Stale connections (closed by the
    server, idle timeout, network reset) are detected by a ``SELECT 1``
    probe and replaced transparently.

    Returns a valid open connection, or raises if PostgreSQL is unreachable.
    """
    conn = getattr(_local, "health_conn", None)

    # Fast path: existing connection, test liveness.
    if conn is not None:
        try:
            if conn.closed:
                conn = None
            else:
                cur = conn.cursor()
                cur.execute("SELECT 1")
                cur.close()
                return conn
        except Exception:
            # Connection stale — close and fall through to create a new one.
            try:
                conn.close()
            except Exception:
                pass
            _local.health_conn = None
            conn = None

    # Slow path: create a new connection. Concurrency is bounded by the probe
    # executor, so no lock is needed here (see the note above).
    import psycopg2
    from database import get_db_config

    cfg = get_db_config()
    # The driver's own socket timeout is the second line of defence; the
    # endpoint's deadline (see health()) is the first.
    probe_ms = int(_probe_deadline_seconds() * 1000)
    conn = psycopg2.connect(
        host=cfg.get("host", "localhost"),
        port=int(cfg.get("port", 5432)),
        user=cfg.get("user", "postgres"),
        password=cfg.get("password", ""),
        dbname=cfg.get("database", "analysis"),
        connect_timeout=max(1, probe_ms // 1000),
        # a half-open connection must not hang the SELECT 1 either
        options=f"-c statement_timeout={probe_ms}",
    )
    _local.health_conn = conn
    return conn


def _probe_database() -> None:
    """Ask the database for one row; raises if it cannot answer."""
    conn = _get_health_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1")
    cur.fetchone()
    cur.close()


@health_bp.route("/health", methods=["GET"])
def health():
    """Liveness + lightweight readiness probe.

    Returns 200 with component status when the app is operational, 503 when a
    critical component is down.

    The probe runs on a worker thread under a deadline, so the answer is
    bounded even when the driver does not return (a crashed PostgreSQL, a
    half-open socket, a pool that is still retrying). The failed check is
    reported as the fixed string ``unavailable``: the body goes to whatever
    polls this endpoint, and an exception class name, message, host or SQL
    fragment has no business there.
    """
    checks: dict = {}
    all_ok = True

    deadline = _probe_deadline_seconds()
    try:
        _probe_executor.submit(_probe_database).result(timeout=deadline)
        checks["database"] = "ok"
    except concurrent.futures.TimeoutError:
        logger.warning("Health probe did not answer within %.1f s; reporting "
                       "the database as unavailable", deadline)
        checks["database"] = "unavailable"
        all_ok = False
    except Exception:
        # Deliberately not the exception: see the docstring.
        logger.warning("Health probe failed; reporting the database as unavailable")
        checks["database"] = "unavailable"
        all_ok = False

    # Settings system
    try:
        from settings import get_settings

        settings = get_settings()
        _ = settings.version
        checks["settings"] = "ok"
    except Exception:
        logger.warning("Health probe could not read the settings version")
        checks["settings"] = "unavailable"
        all_ok = False

    uptime = int(time.time() - _start_time)
    status_code = 200 if all_ok else 503
    return jsonify({
        "status": "healthy" if all_ok else "degraded",
        "uptime_seconds": uptime,
        "checks": checks,
    }), status_code


def register_health_routes(app):
    """Register the health blueprint on the app."""
    app.register_blueprint(health_bp)
    logger.info("✅ Health check endpoint registered at /health")
