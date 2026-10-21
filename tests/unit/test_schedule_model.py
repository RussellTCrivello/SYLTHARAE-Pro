"""Step 20: the schedule model — what may be scheduled, and what it carries.

Pure validation (no database): the schedule types map onto existing
JobManager jobs, the payload is validated against the scenario/retention
jobs at creation and edit time (never silently stored invalid), and the owner
eligibility rule is the authorization the scheduler re-decides at every
fire.
"""

import pytest

from services.scheduling.model import (
    MAX_INTERVAL_MINUTES, SCHEDULE_TYPES,
    ScheduleError, describe, owner_eligible, required_role, validate_interval,
    validate_payload,
)


class TestTheVocabulary:
    def test_the_job_types_map_onto_existing_jobs(self):
        # Only scenario_evaluation and retention remain after consolidation.
        assert set(SCHEDULE_TYPES) == {"scenario_evaluation", "retention"}

    def test_evaluations_are_administrative_retention_is_administrative(self):
        assert required_role("scenario_evaluation") == "admin"
        assert required_role("retention") == "admin"
        with pytest.raises(ScheduleError):
            required_role("nonsense")

    def test_the_interval_is_bounded(self):
        assert validate_interval(5) == 5
        assert validate_interval(1440) == 1440
        assert validate_interval(MAX_INTERVAL_MINUTES) == MAX_INTERVAL_MINUTES
        for bad in (4, MAX_INTERVAL_MINUTES + 1, 0, -5, 10.5, True, "60", None):
            with pytest.raises(ScheduleError):
                validate_interval(bad)


class TestThePayload:
    def test_scenario_evaluation_payload_carries_scenario_id(self):
        stored = validate_payload("scenario_evaluation", {
            "scenario_id": 42, "version": 1})
        assert stored["scenario_id"] == 42 and stored["version"] == 1

    def test_empty_scenario_evaluation_payload_is_valid(self):
        # Empty payload means "every active scenario"
        assert validate_payload("scenario_evaluation", {}) == {}
        assert validate_payload("scenario_evaluation", None) == {}

    def test_retention_payload_carries_policy(self):
        stored = validate_payload("retention", {
            "policy": "jobs", "max_age_days": 30})
        assert stored["policy"] == "jobs" and stored["max_age_days"] == 30

    def test_empty_retention_payload_is_valid(self):
        # Empty payload means "all enabled retention policies"
        assert validate_payload("retention", {}) == {}
        assert validate_payload("retention", None) == {}

    def test_payload_shapes_are_strict(self):
        for bad in ({"scenario_id": 1, "junk": 1},
                    {"scenario_id": "x"},
                    {"scenario_id": 1, "version": "1"},
                    {"policy": "jobs"}):
            with pytest.raises(ScheduleError):
                validate_payload("scenario_evaluation", bad)
        for bad in ({"policy": "jobs", "junk": 1},
                    {"policy": "jobs", "max_age_days": "x"}):
            with pytest.raises(ScheduleError):
                validate_payload("retention", bad)

    def test_the_type_is_validated_first(self):
        with pytest.raises(ScheduleError, match="schedule_type must be one of"):
            validate_payload("nonsense", {})


class TestOwnerEligibility:
    def test_the_role_is_read_at_fire_time_not_stored(self):
        assert owner_eligible("scenario_evaluation", "admin", True) == (True, None)
        assert owner_eligible("scenario_evaluation", "analyst", True) == \
            (False, "owner_role"), "evaluate is administrative"
        assert owner_eligible("retention", "admin", True) == (True, None)
        assert owner_eligible("retention", "analyst", True) == \
            (False, "owner_role"), "retention is administrative"
        assert owner_eligible("scenario_evaluation", None, True) == \
            (False, "owner_role")
        assert owner_eligible("scenario_evaluation", "admin", False) == \
            (False, "owner_inactive"), "a deactivated owner never fires"


class TestDescription:
    def test_the_page_can_say_what_the_schedule_runs(self):
        assert "scenario" in describe("scenario_evaluation", {
            "scenario_id": 42})
        assert "retention" in describe("retention", {
            "policy": "jobs"})