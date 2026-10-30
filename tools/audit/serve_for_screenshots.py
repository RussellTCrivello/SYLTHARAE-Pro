"""Boot the real application against a disposable PostgreSQL, for screenshots.

Written for the Round 22 wrap-up: the three migrated templates have to be
looked at in a browser, before and after, not inferred from a diff. This is the
smallest server that serves the real routes against a real database.

    python3 tools/audit/serve_for_screenshots.py --port 5055 --data-dir /tmp/shots-data

It prints a JSON line with the port and the admin password location when the
server is ready, then serves until killed.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def _point_settings_at(settings: dict) -> None:
    path = ROOT / "data" / "settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    if not isinstance(data, dict):
        data = {}
    data["database"] = settings
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=5055)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--data-dir", default=None)
    args = parser.parse_args(argv)

    data_dir = pathlib.Path(args.data_dir or tempfile.mkdtemp(prefix="shots_"))
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ["APP_DATA_DIR"] = str(data_dir)
    os.environ["SYLTHARAE_TAXONOMY_SYNC"] = "check"

    import urllib.parse

    import pgserver

    server = pgserver.get_server(str(data_dir / "pgdata"))
    parsed = urllib.parse.urlparse(server.get_uri())
    query = urllib.parse.parse_qs(parsed.query)
    settings = {
        "host": query.get("host", [None])[0] or parsed.hostname or "localhost",
        "port": int(parsed.port or 5432),
        "user": urllib.parse.unquote(parsed.username or "postgres"),
        "password": urllib.parse.unquote(parsed.password or ""),
        "database": "syltharae_shots",
    }
    os.environ["DB_HOST"] = str(settings["host"])
    os.environ["DB_PORT"] = str(settings["port"])
    os.environ["DB_USER"] = str(settings["user"])
    os.environ["DB_PASSWORD"] = str(settings["password"])
    os.environ["DB_NAME"] = settings["database"]
    _point_settings_at(settings)

    from database.bootstrap import bootstrap_database

    bootstrap_database(settings)

    from apps.web.app import app

    app.config["TESTING"] = False
    app.config["WTF_CSRF_ENABLED"] = False

    from core.initialization import mark_system_initialized
    from core.security.bootstrap_admin import ensure_initial_admin

    mark_system_initialized()
    ensure_initial_admin()

    # The bootstrap writes a generated password unless APP_ADMIN_PASSWORD is
    # set, and the app module already ran its own bootstrap at import; setting
    # the password here makes the server's credentials the ones this script was
    # told to expect, whichever bootstrap ran first.
    from core.security.service import get_auth_service

    admin_password = os.environ.get("APP_ADMIN_PASSWORD")
    if admin_password:
        service = get_auth_service()
        name = os.environ.get("APP_ADMIN_USERNAME", "admin")
        rows = service.list_users() if hasattr(service, "list_users") else []
        for user in rows:
            username = user.get("username") if isinstance(user, dict) else getattr(user, "username", None)
            user_id = user.get("id") if isinstance(user, dict) else getattr(user, "id", None)
            if username == name and user_id is not None:
                service.set_password(user_id, admin_password)
                print(json.dumps({"admin_password": "set"}), flush=True)

    password_file = None
    for candidate in data_dir.rglob("initial_admin_password.txt"):
        password_file = candidate
        break

    print(json.dumps({"ready": True, "port": args.port,
                      "password_file": str(password_file)}), flush=True)
    app.run(host=args.host, port=args.port, threaded=True, use_reloader=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
