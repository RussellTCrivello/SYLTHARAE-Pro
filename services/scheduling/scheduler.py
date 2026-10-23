"""APScheduler wrapper: one scheduler, driven from the database schedule store.

The JobManager already knows how to run every job we need; the scheduler's
only job is to call ``JobManager.enqueue`` at the right times with the right
arguments. It reads ``schedules`` on startup (and after every CRUD change)
and keeps APScheduler in sync.

Schedule -> JobManager mapping:

* ``scenario_evaluation`` -> ``JobManager.enqueue("scenario_evaluation", ...)``
* ``retention``           -> ``JobManager.enqueue("retention", ...)``
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

if TYPE_CHECKING:
    from services.jobs.manager import JobManager
    from services.scheduling.store import ScheduleStore

log = logging.getLogger(__name__)


class ScheduleRunner:
    """Starts/stops the scheduler and keeps it in sync with the DB."""

    def __init__(self, job_manager: JobManager, store: ScheduleStore) -> None:
        self._job_manager = job_manager
        self._store = store
        self._scheduler = BackgroundScheduler(daemon=True)
        self._job_ids: dict[int, str] = {}  # schedule_id -> apscheduler job id

    def start(self) -> None:
        """Load enabled schedules and start the background scheduler."""
        schedules = self._store.list_enabled()
        for s in schedules:
            self._schedule_one(s)
        self._scheduler.start()
        log.info("Scheduler started with %d job(s)", len(schedules))

    def stop(self) -> None:
        """Shut down the scheduler cleanly."""
        self._scheduler.shutdown(wait=False)
        log.info("Scheduler stopped")

    def refresh(self, schedule_id: int) -> None:
        """Resync one schedule after create/update/delete/enable/disable."""
        self._unschedule(schedule_id)
        s = self._store.get(schedule_id)
        if s and not s.disabled:
            self._schedule_one(s)

    def refresh_all(self) -> None:
        """Full resync (used after bulk changes)."""
        for sid in list(self._job_ids):
            self._unschedule(sid)
        for s in self._store.list_enabled():
            self._schedule_one(s)

    def _schedule_one(self, s) -> None:
        trigger = IntervalTrigger(minutes=s.interval_minutes)
        job_id = f"schedule-{s.id}"
        if s.schedule_type == "scenario_evaluation":
            self._scheduler.add_job(
                self._run_scenario_evaluation, trigger, id=job_id,
                args=[s.id],
                replace_existing=True,
            )
        elif s.schedule_type == "retention":
            self._scheduler.add_job(
                self._run_retention, trigger, id=job_id,
                args=[s.id],
                replace_existing=True,
            )
        else:
            log.warning("Unknown schedule type %r for schedule %d", s.schedule_type, s.id)
            return
        self._job_ids[s.id] = job_id
        log.debug("Scheduled %s (id=%d) every %d minutes", s.schedule_type, s.id, s.interval_minutes)

    def _unschedule(self, schedule_id: int) -> None:
        job_id = self._job_ids.pop(schedule_id, None)
        if job_id:
            try:
                self._scheduler.remove_job(job_id)
            except Exception:
                pass

    # --- job entry points -------------------------------------------------

    def _run_scenario_evaluation(self, schedule_id: int) -> None:
        s = self._store.get(schedule_id)
        if not s or s.disabled:
            log.info("Schedule %d disabled or missing; skipping", schedule_id)
            return
        owner = self._store.get_user(s.owner_id)
        if not owner:
            self._store.disable(schedule_id, "owner_missing")
            log.info("Schedule %d disabled: owner missing", schedule_id)
            return
        from services.scheduling.model import owner_eligible
        ok, reason = owner_eligible(s.schedule_type, owner.get("role"), owner.get("is_active", True))
        if not ok:
            self._store.disable(schedule_id, reason)
            log.info("Schedule %d disabled: %s", schedule_id, reason)
            return
        self._job_manager.enqueue("scenario_evaluation", schedule_id=schedule_id)

    def _run_retention(self, schedule_id: int) -> None:
        s = self._store.get(schedule_id)
        if not s or s.disabled:
            log.info("Schedule %d disabled or missing; skipping", schedule_id)
            return
        owner = self._store.get_user(s.owner_id)
        if not owner:
            self._store.disable(schedule_id, "owner_missing")
            log.info("Schedule %d disabled: owner missing", schedule_id)
            return
        from services.scheduling.model import owner_eligible
        ok, reason = owner_eligible(s.schedule_type, owner.get("role"), owner.get("is_active", True))
        if not ok:
            self._store.disable(schedule_id, reason)
            log.info("Schedule %d disabled: %s", schedule_id, reason)
            return
        self._job_manager.enqueue("retention", schedule_id=schedule_id)