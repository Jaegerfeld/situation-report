# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       22.04.2026
# Geändert:       22.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für transform_data.writers.write_cfd. Prüft, dass tägliche
#   Eintrittszählungen je Stage korrekt berechnet werden (nicht Snapshots):
#   Initialstage bei Erstellung, gemappte Transitionen, unmappte Statuses
#   werden ignoriert.
# =============================================================================

"""Unit tests for transform_data.writers.write_cfd."""

from datetime import date, datetime, timezone, timedelta
from pathlib import Path

import openpyxl
import pytest

from transform_data.processor import IssueRecord, Transition
from transform_data.workflow import parse_workflow
from transform_data.writers import write_cfd


WORKFLOW_TEXT = "\n".join([
    "Funnel",
    "Analysis",
    "Done",
    "<First>Analysis",
    "<Closed>Done",
])

_TZ = timezone(timedelta(hours=1))


def _dt(d: date, h: int = 9) -> datetime:
    """Return a datetime at the given date and hour in the test timezone."""
    return datetime(d.year, d.month, d.day, h, 0, 0, tzinfo=_TZ)


def _record(
    key: str,
    created: datetime,
    initial_stage: str,
    transitions: list[tuple[str, datetime]],
) -> IssueRecord:
    """Build a minimal IssueRecord for write_cfd testing.

    Args:
        key:           Issue key string.
        created:       Issue creation datetime.
        initial_stage: Stage the issue was in before its first transition.
        transitions:   List of (stage_label, timestamp) tuples after creation.

    Returns:
        IssueRecord with only the fields relevant to write_cfd populated.
    """
    trans = [Transition(key=key, label="Created", timestamp=created)]
    for label, ts in transitions:
        trans.append(Transition(key=key, label=label, timestamp=ts))
    return IssueRecord(
        project="TEST", key=key, issuetype="Story", status="Open",
        created=created, component="", first_date=None, inprogress_date=None,
        closed_date=None, stage_minutes={}, resolution="",
        initial_stage=initial_stage, transitions=trans,
    )


@pytest.fixture
def workflow(tmp_path):
    """Parse a three-stage workflow (Funnel → Analysis → Done)."""
    wf_file = tmp_path / "workflow.txt"
    wf_file.write_text(WORKFLOW_TEXT)
    return parse_workflow(wf_file)


def _read_cfd(path: Path) -> dict[str, dict[str, int]]:
    """Read CFD.xlsx and return {date_str: {stage: count}}."""
    wb = openpyxl.load_workbook(path)
    ws = wb.active
    headers = [cell.value for cell in ws[1]]
    result = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        day = row[0]
        result[day] = {headers[i]: row[i] for i in range(1, len(headers))}
    return result


class TestWriteCfd:
    """Tests for write_cfd — daily entry count semantics."""

    def test_initial_stage_counted_on_creation_date(self, workflow, tmp_path):
        """Issue with no transitions: initial_stage counted on creation day."""
        day = date(2025, 1, 1)
        record = _record("A-1", _dt(day), "Funnel", [])
        ref = _dt(date(2025, 1, 2))
        out = tmp_path / "CFD.xlsx"

        write_cfd([record], workflow, out, ref)
        data = _read_cfd(out)

        assert data["01.01.2025"]["Funnel"] == 1
        assert data["01.01.2025"]["Analysis"] == 0
        assert data["01.01.2025"]["Done"] == 0

    def test_transition_counted_on_transition_date(self, workflow, tmp_path):
        """Transition to Analysis on Jan 2 is counted on that day, not creation day."""
        create_day = date(2025, 1, 1)
        trans_day = date(2025, 1, 2)
        record = _record("A-1", _dt(create_day), "Funnel", [
            ("Analysis", _dt(trans_day)),
        ])
        ref = _dt(date(2025, 1, 3))
        out = tmp_path / "CFD.xlsx"

        write_cfd([record], workflow, out, ref)
        data = _read_cfd(out)

        assert data["01.01.2025"]["Funnel"] == 1
        assert data["01.01.2025"]["Analysis"] == 0
        assert data["02.01.2025"]["Analysis"] == 1
        assert data["02.01.2025"]["Funnel"] == 0

    def test_two_issues_same_day(self, workflow, tmp_path):
        """Two issues entering the same stage on the same day are summed."""
        day = date(2025, 1, 1)
        r1 = _record("A-1", _dt(day), "Funnel", [])
        r2 = _record("A-2", _dt(day), "Funnel", [])
        out = tmp_path / "CFD.xlsx"

        write_cfd([r1, r2], workflow, out, _dt(date(2025, 1, 1)))
        data = _read_cfd(out)

        assert data["01.01.2025"]["Funnel"] == 2

    def test_unmapped_label_not_counted(self, workflow, tmp_path):
        """Transitions with unmapped stage labels are not counted in any stage column."""
        day = date(2025, 1, 1)
        trans_day = date(2025, 1, 2)
        # "Unknown Status" is not a stage in the workflow
        record = _record("A-1", _dt(day), "Funnel", [
            ("Unknown Status", _dt(trans_day)),
        ])
        out = tmp_path / "CFD.xlsx"

        write_cfd([record], workflow, out, _dt(date(2025, 1, 2)))
        data = _read_cfd(out)

        assert data["02.01.2025"]["Funnel"] == 0
        assert data["02.01.2025"]["Analysis"] == 0
        assert data["02.01.2025"]["Done"] == 0

    def test_days_with_no_entries_are_zero(self, workflow, tmp_path):
        """Days without any transitions have zero counts for all stages."""
        record = _record("A-1", _dt(date(2025, 1, 1)), "Funnel", [
            ("Done", _dt(date(2025, 1, 5))),
        ])
        out = tmp_path / "CFD.xlsx"

        write_cfd([record], workflow, out, _dt(date(2025, 1, 5)))
        data = _read_cfd(out)

        # Jan 2–4: no transitions, all zeros
        for d in ["02.01.2025", "03.01.2025", "04.01.2025"]:
            assert all(v == 0 for v in data[d].values())

    def test_empty_records_writes_no_file(self, workflow, tmp_path):
        """write_cfd with empty records does not create a file."""
        out = tmp_path / "CFD.xlsx"
        write_cfd([], workflow, out, _dt(date(2025, 1, 1)))
        assert not out.exists()
