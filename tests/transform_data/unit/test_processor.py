"""
Unit tests for transform_data.processor.process_issues()

Synthetic Jira JSON is built in-memory so tests are deterministic and
independent of real export files or the current system time.
"""

import json
import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path

from transform_data.workflow import Workflow
from transform_data.processor import process_issues


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REF_DT = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

SIMPLE_WORKFLOW = Workflow(
    stages=["Funnel", "Analysis", "Implementation", "Done"],
    status_to_stage={
        "Funnel": "Funnel", "New": "Funnel",
        "Analysis": "Analysis", "In Analysis": "Analysis",
        "Implementation": "Implementation", "In Progress": "Implementation",
        "Done": "Done", "Closed": "Done",
    },
    first_stage="Analysis",
    closed_stage="Done",
    inprogress_stage="Implementation",
)


def _make_json(issues: list[dict]) -> str:
    return json.dumps({"issues": issues})


def _ts(dt: datetime) -> str:
    """Format a datetime as Jira ISO string."""
    offset = dt.utcoffset() or timedelta(0)
    total_seconds = int(offset.total_seconds())
    sign = "+" if total_seconds >= 0 else "-"
    h, m = divmod(abs(total_seconds) // 60, 60)
    return dt.strftime(f"%Y-%m-%dT%H:%M:%S.000{sign}{h:02d}{m:02d}")


def _issue(
    key: str,
    created: datetime,
    status: str = "Funnel",
    transitions: list[tuple[str, str, datetime]] | None = None,
) -> dict:
    """Build a minimal Jira issue dict."""
    histories = []
    for from_s, to_s, ts in (transitions or []):
        histories.append({
            "created": _ts(ts),
            "items": [{"field": "status", "fromString": from_s, "toString": to_s}],
        })
    return {
        "key": key,
        "fields": {
            "project": {"key": "TEST"},
            "issuetype": {"name": "Story"},
            "status": {"name": status},
            "created": _ts(created),
            "components": [],
            "resolution": None,
        },
        "changelog": {"histories": histories},
    }


def _process(issues: list[dict], workflow: Workflow = SIMPLE_WORKFLOW):
    payload = _make_json(issues)
    tmp = Path(__file__).parent / "_tmp_test.json"
    tmp.write_text(payload, encoding="utf-8")
    try:
        return process_issues(tmp, workflow, REF_DT)
    finally:
        tmp.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

class TestNoTransitions:
    def test_all_stage_minutes_are_zero(self):
        created = datetime(2025, 12, 1, 10, 0, tzinfo=timezone.utc)
        records, _ = _process([_issue("T-1", created, status="Funnel")])
        assert all(v == 0 for v in records[0].stage_minutes.values())

    def test_dates_are_none(self):
        created = datetime(2025, 12, 1, 10, 0, tzinfo=timezone.utc)
        records, _ = _process([_issue("T-1", created)])
        r = records[0]
        assert r.first_date is None
        assert r.inprogress_date is None
        assert r.closed_date is None

    def test_initial_stage_falls_back_to_first_workflow_stage(self):
        """Unmapped initial status → first stage in workflow used."""
        created = datetime(2025, 12, 1, 10, 0, tzinfo=timezone.utc)
        records, _ = _process([_issue("T-1", created, status="Unknown")])
        assert records[0].initial_stage == "Funnel"


class TestPreTransitionTime:
    def test_time_before_first_transition_goes_to_initial_stage(self):
        """60 minutes elapse in Funnel before the first explicit transition."""
        created = datetime(2025, 12, 1, 10, 0, tzinfo=timezone.utc)
        t1 = datetime(2025, 12, 1, 11, 0, tzinfo=timezone.utc)  # +60 min
        records, _ = _process([_issue(
            "T-1", created, status="Analysis",
            transitions=[("Funnel", "Analysis", t1)],
        )])
        assert records[0].stage_minutes["Funnel"] == 60

    def test_time_after_last_transition_goes_to_last_stage(self):
        """From last transition to REF_DT is attributed to the last stage."""
        created = datetime(2025, 12, 1, 10, 0, tzinfo=timezone.utc)
        t1 = datetime(2025, 12, 1, 11, 0, tzinfo=timezone.utc)
        # REF_DT = 2026-01-01 00:00 UTC → 31 days - 1 hour after t1
        expected = int((REF_DT - t1).total_seconds() / 60)
        records, _ = _process([_issue(
            "T-1", created,
            transitions=[("Funnel", "Analysis", t1)],
        )])
        assert records[0].stage_minutes["Analysis"] == expected


class TestCarryForward:
    def test_unmapped_transition_time_goes_to_last_known_stage(self):
        """
        Issue path: Funnel (60 min) → UnknownStage (120 min) → Analysis
        The 120 min in UnknownStage must be carried forward to Funnel.
        """
        created = datetime(2025, 12, 1, 10, 0, tzinfo=timezone.utc)
        t1 = datetime(2025, 12, 1, 11, 0, tzinfo=timezone.utc)   # +60 min: enter Unknown
        t2 = datetime(2025, 12, 1, 13, 0, tzinfo=timezone.utc)   # +120 min: enter Analysis
        records, _ = _process([_issue(
            "T-1", created,
            transitions=[
                ("Funnel", "UnknownStage", t1),
                ("UnknownStage", "Analysis", t2),
            ],
        )])
        r = records[0]
        assert r.stage_minutes["Funnel"] == 60 + 120   # pre + carried forward
        assert r.stage_minutes["Analysis"] > 0

    def test_unmapped_status_is_reported(self):
        created = datetime(2025, 12, 1, 10, 0, tzinfo=timezone.utc)
        t1 = datetime(2025, 12, 1, 11, 0, tzinfo=timezone.utc)
        _, unmapped = _process([_issue(
            "T-1", created,
            transitions=[("Funnel", "UnknownStage", t1)],
        )])
        assert "UnknownStage" in unmapped

    def test_fully_mapped_workflow_has_no_unmapped(self, simple_workflow_file: Path):
        created = datetime(2025, 12, 1, 10, 0, tzinfo=timezone.utc)
        t1 = datetime(2025, 12, 1, 11, 0, tzinfo=timezone.utc)
        _, unmapped = _process([_issue(
            "T-1", created,
            transitions=[("Funnel", "Analysis", t1)],
        )])
        assert len(unmapped) == 0


class TestMilestoneDates:
    def test_first_date_set_on_entry_to_first_stage(self):
        created = datetime(2025, 12, 1, 10, 0, tzinfo=timezone.utc)
        t1 = datetime(2025, 12, 1, 11, 0, tzinfo=timezone.utc)
        records, _ = _process([_issue(
            "T-1", created,
            transitions=[("Funnel", "Analysis", t1)],
        )])
        assert records[0].first_date == t1

    def test_first_date_only_set_once_on_first_entry(self):
        """Re-entering the first_stage does not overwrite first_date."""
        created = datetime(2025, 12, 1, 10, 0, tzinfo=timezone.utc)
        t1 = datetime(2025, 12, 1, 11, 0, tzinfo=timezone.utc)
        t2 = datetime(2025, 12, 1, 12, 0, tzinfo=timezone.utc)
        t3 = datetime(2025, 12, 1, 13, 0, tzinfo=timezone.utc)
        records, _ = _process([_issue(
            "T-1", created,
            transitions=[
                ("Funnel", "Analysis", t1),
                ("Analysis", "Funnel", t2),
                ("Funnel", "Analysis", t3),  # re-entry
            ],
        )])
        assert records[0].first_date == t1  # not t3

    def test_closed_date_set_on_entry_to_closed_stage(self):
        created = datetime(2025, 12, 1, 10, 0, tzinfo=timezone.utc)
        t1 = datetime(2025, 12, 1, 11, 0, tzinfo=timezone.utc)
        t2 = datetime(2025, 12, 1, 12, 0, tzinfo=timezone.utc)
        records, _ = _process([_issue(
            "T-1", created,
            transitions=[
                ("Funnel", "Analysis", t1),
                ("Analysis", "Done", t2),
            ],
        )])
        assert records[0].closed_date == t2

    def test_no_first_date_if_issue_never_reaches_first_stage(self):
        created = datetime(2025, 12, 1, 10, 0, tzinfo=timezone.utc)
        t1 = datetime(2025, 12, 1, 11, 0, tzinfo=timezone.utc)
        records, _ = _process([_issue(
            "T-1", created,
            transitions=[("Funnel", "Implementation", t1)],
        )])
        assert records[0].first_date is None


class TestTransitions:
    def test_first_transition_is_always_created(self):
        created = datetime(2025, 12, 1, 10, 0, tzinfo=timezone.utc)
        records, _ = _process([_issue("T-1", created)])
        assert records[0].transitions[0].label == "Created"
        assert records[0].transitions[0].timestamp == created

    def test_transitions_are_sorted_by_timestamp(self):
        created = datetime(2025, 12, 1, 10, 0, tzinfo=timezone.utc)
        t1 = datetime(2025, 12, 1, 11, 0, tzinfo=timezone.utc)
        t2 = datetime(2025, 12, 1, 12, 0, tzinfo=timezone.utc)
        records, _ = _process([_issue(
            "T-1", created,
            transitions=[
                ("Analysis", "Implementation", t2),
                ("Funnel", "Analysis", t1),
            ],
        )])
        timestamps = [t.timestamp for t in records[0].transitions]
        assert timestamps == sorted(timestamps)
