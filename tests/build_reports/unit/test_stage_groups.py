# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       18.04.2026
# Geändert:       18.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für stage_groups.py: classify_stages (Stage-Klassifikation
#   nach Workflow-Position) und issue_stage_group (Gruppenbestimmung per
#   Übergangsdaten). Prüft Grenzbedingungen und Fallback-Verhalten.
# =============================================================================

from datetime import datetime

import pytest

from build_reports.loader import IssueRecord
from build_reports.stage_groups import (
    GROUP_DONE, GROUP_IN_PROGRESS, GROUP_TODO,
    classify_stages, issue_stage_group,
)


def _issue(first: datetime | None, closed: datetime | None) -> IssueRecord:
    """Create a minimal IssueRecord with the given transition dates.

    Args:
        first:  First Date (start of active work), or None.
        closed: Closed Date (completion), or None.

    Returns:
        IssueRecord with project 'P' and empty stage_minutes.
    """
    return IssueRecord(
        project="P", key="X-1", issuetype="Feature", status="Done",
        created=datetime(2025, 1, 1), component="",
        first_date=first, implementation_date=None,
        closed_date=closed, stage_minutes={}, resolution="",
    )


class TestClassifyStages:
    """Tests for classify_stages() — mapping workflow stages to To Do/In Progress/Done."""

    @pytest.fixture
    def stages(self) -> list[str]:
        """Six-stage ordered workflow with 'Analysis' as first and 'Releasing' as closed."""
        return ["New", "Analysis", "In Dev", "In Review", "Releasing", "Done"]

    def test_todo_stages_before_first(self, stages):
        """Stages before the first_stage boundary are classified as To Do."""
        groups = classify_stages(stages, "Analysis", "Releasing")
        assert groups["New"] == GROUP_TODO

    def test_in_progress_includes_first_stage(self, stages):
        """The first_stage itself is classified as In Progress (inclusive lower bound)."""
        groups = classify_stages(stages, "Analysis", "Releasing")
        assert groups["Analysis"] == GROUP_IN_PROGRESS

    def test_in_progress_stages_between_boundaries(self, stages):
        """Stages between first_stage and closed_stage are classified as In Progress."""
        groups = classify_stages(stages, "Analysis", "Releasing")
        assert groups["In Dev"] == GROUP_IN_PROGRESS
        assert groups["In Review"] == GROUP_IN_PROGRESS

    def test_done_starts_at_closed_stage(self, stages):
        """The closed_stage itself is classified as Done (inclusive lower bound)."""
        groups = classify_stages(stages, "Analysis", "Releasing")
        assert groups["Releasing"] == GROUP_DONE

    def test_done_stages_after_closed(self, stages):
        """Stages after closed_stage are classified as Done."""
        groups = classify_stages(stages, "Analysis", "Releasing")
        assert groups["Done"] == GROUP_DONE

    def test_all_keys_present(self, stages):
        """Every stage name appears exactly once in the result dict."""
        groups = classify_stages(stages, "Analysis", "Releasing")
        assert set(groups.keys()) == set(stages)

    def test_none_first_stage_all_in_progress(self, stages):
        """When first_stage is None, all stages fall back to In Progress."""
        groups = classify_stages(stages, None, "Releasing")
        assert all(v == GROUP_IN_PROGRESS for v in groups.values())

    def test_unknown_first_stage_all_in_progress(self, stages):
        """When first_stage is not in the stages list, all stages are In Progress."""
        groups = classify_stages(stages, "NonExistent", "Releasing")
        assert all(v == GROUP_IN_PROGRESS for v in groups.values())

    def test_none_closed_stage_no_done_group(self, stages):
        """When closed_stage is None, no stage is classified as Done."""
        groups = classify_stages(stages, "Analysis", None)
        assert GROUP_DONE not in groups.values()

    def test_unknown_closed_stage_no_done_group(self, stages):
        """When closed_stage is not in the stages list, no stage is classified as Done."""
        groups = classify_stages(stages, "Analysis", "NonExistent")
        assert GROUP_DONE not in groups.values()

    def test_empty_stages_returns_empty(self):
        """An empty stages list returns an empty dict."""
        assert classify_stages([], "Analysis", "Releasing") == {}

    def test_single_stage_as_first_all_in_progress(self):
        """A single-stage list where that stage is the first_stage yields In Progress."""
        groups = classify_stages(["Only"], "Only", None)
        assert groups["Only"] == GROUP_IN_PROGRESS


class TestIssueStageGroup:
    """Tests for issue_stage_group() — deriving group from an issue's transition dates."""

    def test_closed_date_returns_done(self):
        """An issue with a Closed Date is classified as Done."""
        issue = _issue(datetime(2025, 1, 2), datetime(2025, 1, 10))
        assert issue_stage_group(issue) == GROUP_DONE

    def test_first_date_only_returns_in_progress(self):
        """An issue with First Date but no Closed Date is classified as In Progress."""
        issue = _issue(datetime(2025, 1, 2), None)
        assert issue_stage_group(issue) == GROUP_IN_PROGRESS

    def test_no_dates_returns_todo(self):
        """An issue without First Date or Closed Date is classified as To Do."""
        issue = _issue(None, None)
        assert issue_stage_group(issue) == GROUP_TODO

    def test_closed_date_takes_precedence_over_first(self):
        """When both dates are set, Closed Date takes precedence — result is Done."""
        issue = _issue(datetime(2025, 1, 2), datetime(2025, 1, 10))
        assert issue_stage_group(issue) == GROUP_DONE
