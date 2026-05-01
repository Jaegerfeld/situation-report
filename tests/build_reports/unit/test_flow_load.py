# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       15.04.2026
# Geändert:       30.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für FlowLoadMetric. Prüft Trennung open/closed, Statusgruppen-
#   Filterung (nur In Progress als Not Done), Stage-Filterung (Done-Stages
#   ausgeblendet), Altersberechnung, Stage-Zuordnung und Render-Ausgabe.
# =============================================================================

from datetime import datetime

import pytest

from build_reports.loader import IssueRecord, ReportData
from build_reports.metrics.flow_load import FlowLoadMetric, _age_days, _current_stage
from build_reports.terminology import SAFE


def _todo_issue(key: str, stage_minutes: dict | None = None) -> IssueRecord:
    """Create a minimal IssueRecord in To Do state (no first_date, no closed_date).

    Args:
        key:           Unique issue key.
        stage_minutes: Dict of stage name to minutes spent; defaults to empty.

    Returns:
        IssueRecord with first_date=None and closed_date=None.
    """
    return IssueRecord(
        project="P", key=key, issuetype="Feature", status="To Do",
        created=datetime(2025, 1, 1), component="",
        first_date=None, implementation_date=None, closed_date=None,
        stage_minutes=stage_minutes or {}, resolution="",
    )


def _issue(key: str, closed: datetime | None = None,
           stage_minutes: dict | None = None,
           first: datetime | None = None) -> IssueRecord:
    """Create a minimal IssueRecord with optional closed date, stage minutes, and first date.

    Args:
        key:           Unique issue key.
        closed:        Closed datetime, or None for an open issue.
        stage_minutes: Dict of stage name to minutes spent; defaults to empty.
        first:         First active date; defaults to 2025-01-02 if not given.

    Returns:
        IssueRecord with status 'In Progress' and project 'P'.
    """
    return IssueRecord(
        project="P", key=key, issuetype="Feature", status="In Progress",
        created=datetime(2025, 1, 1), component="",
        first_date=first or datetime(2025, 1, 2),
        implementation_date=None, closed_date=closed,
        stage_minutes=stage_minutes or {}, resolution="",
    )


STAGES = ["Funnel", "Analysis", "Implementation", "Done"]


@pytest.fixture
def metric() -> FlowLoadMetric:
    """Return a default FlowLoadMetric instance."""
    return FlowLoadMetric()


@pytest.fixture
def mixed_data() -> ReportData:
    """ReportData with two open issues and one closed issue across multiple stages."""
    return ReportData(
        issues=[
            _issue("O-1", closed=None,
                   stage_minutes={"Funnel": 0, "Analysis": 100, "Implementation": 50, "Done": 0}),
            _issue("O-2", closed=None,
                   stage_minutes={"Funnel": 200, "Analysis": 0, "Implementation": 0, "Done": 0}),
            _issue("C-1", closed=datetime(2025, 3, 1),
                   first=datetime(2025, 1, 1),
                   stage_minutes={"Funnel": 10, "Analysis": 20, "Implementation": 30, "Done": 5}),
        ],
        cfd=[], stages=STAGES, source_prefix="TEST",
    )


class TestCurrentStage:
    """Tests for _current_stage() — inferring an issue's active workflow stage."""

    def test_returns_last_nonzero_stage(self):
        """Returns the last stage in workflow order that has recorded time > 0."""
        issue = _issue("X", stage_minutes={"Funnel": 10, "Analysis": 20, "Implementation": 0, "Done": 0})
        assert _current_stage(issue, STAGES) == "Analysis"

    def test_fallback_to_first_stage_when_all_zero(self):
        """Falls back to the first workflow stage when all stage minutes are zero."""
        issue = _issue("X", stage_minutes={"Funnel": 0, "Analysis": 0})
        assert _current_stage(issue, ["Funnel", "Analysis"]) == "Funnel"

    def test_single_stage_with_time(self):
        """Returns the only stage when it has recorded time."""
        issue = _issue("X", stage_minutes={"Funnel": 5})
        assert _current_stage(issue, ["Funnel"]) == "Funnel"


class TestCompute:
    """Tests for FlowLoadMetric.compute() — open issue age grouping."""

    def test_only_in_progress_issues_counted(self, metric, mixed_data):
        """open_count reflects only In Progress issues (First Date set, no Closed Date)."""
        result = metric.compute(mixed_data, SAFE)
        assert result.stats["open_count"] == 2

    def test_warning_when_no_open_issues(self, metric):
        """A warning is produced when no open issues exist in the dataset."""
        data = ReportData(
            issues=[_issue("C-1", closed=datetime(2025, 3, 1))],
            cfd=[], stages=STAGES, source_prefix="",
        )
        result = metric.compute(data, SAFE)
        assert result.warnings

    def test_done_count_from_closed_issues(self, metric, mixed_data):
        """done_count stat is derived from closed issues with valid cycle time."""
        result = metric.compute(mixed_data, SAFE)
        assert result.stats["done_count"] > 0

    def test_mean_age_positive(self, metric, mixed_data):
        """Mean age of open issues is positive when issues have a first date."""
        result = metric.compute(mixed_data, SAFE)
        assert result.stats["mean_age"] > 0

    def test_metric_id(self, metric, mixed_data):
        """MetricResult carries the correct metric ID."""
        result = metric.compute(mixed_data, SAFE)
        assert result.metric_id == "flow_load"


class TestRender:
    """Tests for FlowLoadMetric.render() — aging WIP boxplot output."""

    def test_returns_one_figure(self, metric, mixed_data):
        """render() returns exactly one figure."""
        result = metric.compute(mixed_data, SAFE)
        figs = metric.render(result, SAFE)
        assert len(figs) == 1

    def test_returns_empty_on_no_data(self, metric):
        """render() returns an empty list when compute() produced no chart data."""
        data = ReportData(
            issues=[_issue("C-1", closed=datetime(2025, 3, 1))],
            cfd=[], stages=STAGES, source_prefix="",
        )
        result = metric.compute(data, SAFE)
        assert metric.render(result, SAFE) == []

    def test_stage_count_annotations_present(self, metric, mixed_data):
        """render() adds one 'n=...' annotation per active stage at the top of each column."""
        result = metric.compute(mixed_data, SAFE)
        fig = metric.render(result, SAFE)[0]
        count_annotations = [a for a in fig.layout.annotations if a.text.startswith("n=")]
        active_stages = [s for s in STAGES if s in result.chart_data.by_stage
                         and result.chart_data.by_stage[s]]
        assert len(count_annotations) == len(active_stages)

    def test_stage_count_annotation_values(self, metric, mixed_data):
        """Each stage count annotation shows the correct number of issues for that stage."""
        result = metric.compute(mixed_data, SAFE)
        fig = metric.render(result, SAFE)[0]
        count_annotations = {a.x: int(a.text[2:]) for a in fig.layout.annotations
                              if a.text.startswith("n=")}
        for stage, ages in result.chart_data.by_stage.items():
            assert count_annotations[stage] == len(ages)

    def test_has_three_reference_shapes(self, metric, mixed_data):
        """render() produces exactly 3 hline shapes (CT Median, CT P85, Target CT)."""
        result = metric.compute(mixed_data, SAFE)
        fig = metric.render(result, SAFE)[0]
        hlines = [s for s in fig.layout.shapes if s.type == "line" and s.x0 == 0]
        assert len(hlines) == 3

    def test_target_ct_line_always_present(self, metric):
        """Target CT reference line appears even when there are no closed issues."""
        data = ReportData(
            issues=[
                _issue("O-1", closed=None,
                       stage_minutes={"Funnel": 100, "Analysis": 0}),
            ],
            cfd=[], stages=["Funnel", "Analysis"], source_prefix="",
        )
        result = metric.compute(data, SAFE)
        fig = metric.render(result, SAFE)[0]
        hlines = [s for s in fig.layout.shapes if s.type == "line" and s.x0 == 0]
        assert len(hlines) == 1  # only Target CT line; no CT Median/P85 without closed issues

    def test_legend_shows_target_ct(self, metric, mixed_data):
        """A dummy trace for Target CT appears in the legend regardless of closed issues."""
        result = metric.compute(mixed_data, SAFE)
        fig = metric.render(result, SAFE)[0]
        legend_names = [t.name for t in fig.data if t.showlegend]
        assert any("Target CT" in name for name in legend_names)

    def test_target_ct_configurable(self, metric, mixed_data):
        """FlowLoadMetric.target_ct is passed through to chart_data.target_ct_days."""
        metric.target_ct = 30
        result = metric.compute(mixed_data, SAFE)
        assert result.chart_data.target_ct_days == 30


class TestStatusGroupFiltering:
    """Tests for status-group-aware issue and stage filtering in FlowLoadMetric."""

    def test_todo_issues_excluded_from_open_count(self, metric):
        """To Do issues (no First Date) are not counted as Not Done items."""
        data = ReportData(
            issues=[
                _issue("IP-1", closed=None,
                       stage_minutes={"Funnel": 100, "Analysis": 0}),
                _todo_issue("TD-1", stage_minutes={"Funnel": 50, "Analysis": 0}),
            ],
            cfd=[], stages=["Funnel", "Analysis"], source_prefix="",
        )
        result = metric.compute(data, SAFE)
        assert result.stats["open_count"] == 1

    def test_todo_only_dataset_produces_warning(self, metric):
        """A dataset with only To Do issues triggers the no-open-issues warning."""
        data = ReportData(
            issues=[_todo_issue("TD-1", stage_minutes={"Funnel": 100})],
            cfd=[], stages=["Funnel", "Analysis"], source_prefix="",
        )
        result = metric.compute(data, SAFE)
        assert result.warnings

    def test_done_stages_excluded_from_boxplot(self, metric):
        """Stages in the Done group are not rendered as boxplot columns."""
        data = ReportData(
            issues=[
                _issue("IP-1", closed=None,
                       stage_minutes={"Analysis": 100, "Closed": 10}),
            ],
            cfd=[], stages=["Funnel", "Analysis", "Closed"],
            source_prefix="", first_stage="Analysis", closed_stage="Closed",
        )
        result = metric.compute(data, SAFE)
        assert "Closed" not in result.chart_data.stages_ordered

    def test_in_progress_stages_included_in_boxplot(self, metric):
        """Stages in the In Progress group appear in the boxplot when they have issues."""
        data = ReportData(
            issues=[
                _issue("IP-1", closed=None,
                       stage_minutes={"Analysis": 100}),
            ],
            cfd=[], stages=["Funnel", "Analysis", "Closed"],
            source_prefix="", first_stage="Analysis", closed_stage="Closed",
        )
        result = metric.compute(data, SAFE)
        assert "Analysis" in result.chart_data.stages_ordered

    def test_done_stage_excluded_via_allowlist(self, metric):
        """The explicit GROUP_TODO/GROUP_IN_PROGRESS allowlist excludes Done stages.

        This is equivalent to ``!= GROUP_DONE`` when all stages are classified,
        but the allowlist form makes the intent explicit and is more readable.
        Two issues: one currently in Analysis (In Progress), one in Closed
        (Done). Only the Analysis stage should appear in the boxplot.
        """
        data = ReportData(
            issues=[
                _issue("IP-1", closed=None, stage_minutes={"Analysis": 100}),
                _issue("IP-2", closed=None, stage_minutes={"Closed": 50}),
            ],
            cfd=[], stages=["Funnel", "Analysis", "Closed"],
            source_prefix="", first_stage="Analysis", closed_stage="Closed",
        )
        result = metric.compute(data, SAFE)
        # "Closed" is GROUP_DONE — must not appear in the boxplot.
        assert "Closed" not in result.chart_data.stages_ordered
        assert "Analysis" in result.chart_data.stages_ordered

    def test_without_boundary_stages_all_stages_shown(self, metric):
        """When first_stage and closed_stage are unknown, stages are not filtered by group."""
        data = ReportData(
            issues=[
                _issue("IP-1", closed=None, stage_minutes={"Funnel": 50, "Analysis": 0}),
                _issue("IP-2", closed=None, stage_minutes={"Funnel": 0, "Analysis": 100}),
            ],
            cfd=[], stages=["Funnel", "Analysis"], source_prefix="",
        )
        result = metric.compute(data, SAFE)
        assert set(result.chart_data.stages_ordered) == {"Funnel", "Analysis"}
