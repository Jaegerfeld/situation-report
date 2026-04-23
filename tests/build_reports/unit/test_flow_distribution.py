# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       15.04.2026
# Geändert:       24.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für FlowDistributionMetric. Prüft Zählung nach Issuetype,
#   Stage-Prominenz (längste aktive Stage je Issue, terminale Done-Stage
#   geschlossener Issues wird ausgeschlossen) und Ø Cycle Time je Issuetype,
#   sowie Render-Ausgabe (drei Pie-Charts als Subplots).
# =============================================================================

from datetime import datetime

import pytest

from build_reports.loader import IssueRecord, ReportData
from build_reports.metrics.flow_distribution import FlowDistributionMetric
from build_reports.terminology import SAFE


def _issue(
    key: str,
    issuetype: str,
    status: str,
    stage_minutes: dict[str, int] | None = None,
    first_date: datetime | None = None,
    closed_date: datetime | None = None,
) -> IssueRecord:
    """Create an IssueRecord with configurable stage_minutes, dates, type and status.

    Args:
        key:           Unique issue key (e.g. 'A-1').
        issuetype:     Issue type string (e.g. 'Feature', 'Bug').
        status:        Current status string (e.g. 'Done', 'In Progress').
        stage_minutes: Stage-to-minutes mapping; defaults to empty dict.
        first_date:    Optional first date for CT computation.
        closed_date:   Optional closed date for CT computation.

    Returns:
        IssueRecord with all unspecified optional fields set to empty/None.
    """
    return IssueRecord(
        project="P", key=key, issuetype=issuetype, status=status,
        created=datetime(2025, 1, 1), component="",
        first_date=first_date,
        implementation_date=None,
        closed_date=closed_date,
        stage_minutes=stage_minutes or {},
        resolution="",
    )


@pytest.fixture
def metric() -> FlowDistributionMetric:
    """Return a default FlowDistributionMetric instance."""
    return FlowDistributionMetric()


@pytest.fixture
def mixed_data() -> ReportData:
    """ReportData with five issues covering types, stage prominence, and CTs.

    A-1 Feature status=Completed CT=10d:
        Analysis=100, Implementation=200, Completed=5000
        → closed: exclude "Completed" → max = Implementation(200)
    A-2 Feature status=Completed CT=20d:
        Analysis=300, Implementation=100, Completed=2000
        → closed: exclude "Completed" → max = Analysis(300)
    A-3 Bug status=Analysis (in progress):
        Analysis=200, Implementation=50, Completed=0
        → open: include all → max = Analysis(200)
    A-4 Bug status=Implementation (in progress):
        Analysis=50, Implementation=300, Completed=0
        → open: include all → max = Implementation(300)
    A-5 Story status=Analysis (in progress, all zeros):
        → excluded from prominence (zero-minutes check)
    CT: Feature avg = (10+20)/2 = 15d
    """
    return ReportData(
        issues=[
            _issue("A-1", "Feature", "Completed",
                   stage_minutes={"Analysis": 100, "Implementation": 200, "Completed": 5000},
                   first_date=datetime(2025, 1, 1), closed_date=datetime(2025, 1, 11)),
            _issue("A-2", "Feature", "Completed",
                   stage_minutes={"Analysis": 300, "Implementation": 100, "Completed": 2000},
                   first_date=datetime(2025, 2, 1), closed_date=datetime(2025, 2, 21)),
            _issue("A-3", "Bug", "Analysis",
                   stage_minutes={"Analysis": 200, "Implementation": 50, "Completed": 0},
                   first_date=datetime(2025, 3, 1)),
            _issue("A-4", "Bug", "Implementation",
                   stage_minutes={"Analysis": 50, "Implementation": 300, "Completed": 0},
                   first_date=datetime(2025, 4, 1)),
            _issue("A-5", "Story", "Analysis",
                   stage_minutes={"Analysis": 0, "Implementation": 0, "Completed": 0},
                   first_date=datetime(2025, 5, 1)),
        ],
        cfd=[], stages=[], source_prefix="TEST",
    )


class TestCompute:
    """Tests for FlowDistributionMetric.compute()."""

    def test_total_count(self, metric, mixed_data):
        """Total issue count equals the number of issues in the dataset."""
        result = metric.compute(mixed_data, SAFE)
        assert result.stats["total"] == 5

    def test_type_counts(self, metric, mixed_data):
        """Each issuetype is counted correctly across all issues."""
        result = metric.compute(mixed_data, SAFE)
        counts = result.stats["type_counts"]
        assert counts["Feature"] == 2
        assert counts["Bug"] == 2
        assert counts["Story"] == 1

    def test_by_prominence_counts_longest_active_stage(self, metric, mixed_data):
        """by_prominence counts all issues by their longest active stage."""
        result = metric.compute(mixed_data, SAFE)
        prom = result.chart_data.by_prominence
        # A-1 (closed): Completed excluded → Implementation(200) wins
        # A-2 (closed): Completed excluded → Analysis(300) wins
        # A-3 (open):   all included → Analysis(200) wins
        # A-4 (open):   all included → Implementation(300) wins
        assert prom["Analysis"] == 2
        assert prom["Implementation"] == 2

    def test_by_prominence_excludes_terminal_stage_for_closed_issues(self, metric, mixed_data):
        """For closed issues the terminal Done stage (issue.status) is excluded from prominence."""
        result = metric.compute(mixed_data, SAFE)
        prom = result.chart_data.by_prominence
        # A-1 and A-2 have Completed=5000/2000; without exclusion "Completed" would dominate
        assert "Completed" not in prom

    def test_by_prominence_includes_closed_issues(self, metric, mixed_data):
        """Closed issues contribute to prominence via their active stages."""
        result = metric.compute(mixed_data, SAFE)
        # All 4 issues with stage data (A-1..A-4) contribute; A-5 zeros-out
        assert result.stats["prominence_n"] == 4
        assert sum(result.chart_data.by_prominence.values()) == 4

    def test_by_prominence_skips_zero_minutes(self, metric, mixed_data):
        """Issues where all stage_minutes are zero are excluded from prominence."""
        result = metric.compute(mixed_data, SAFE)
        # A-5 has all zeros → not counted despite having first_date
        assert result.stats["prominence_n"] == 4

    def test_by_prominence_skips_empty_stage_minutes(self, metric):
        """Issues with no stage_minutes at all are excluded from prominence."""
        data = ReportData(
            issues=[_issue("X-1", "Feature", "Funnel")],
            cfd=[], stages=[], source_prefix="",
        )
        result = metric.compute(data, SAFE)
        assert result.chart_data.by_prominence == {}

    def test_ct_by_type_average(self, metric, mixed_data):
        """Avg CT per issuetype is computed correctly from first_date and closed_date."""
        result = metric.compute(mixed_data, SAFE)
        ct = result.chart_data.ct_by_type
        # Feature: (10 + 20) / 2 = 15 days
        assert abs(ct["Feature"] - 15.0) < 0.01

    def test_ct_by_type_excludes_open_issues(self, metric, mixed_data):
        """Issues without a closed_date are not included in CT averages."""
        result = metric.compute(mixed_data, SAFE)
        ct = result.chart_data.ct_by_type
        assert "Bug" not in ct
        assert "Story" not in ct

    def test_warning_on_empty(self, metric):
        """A warning is produced when the dataset contains no issues."""
        data = ReportData(issues=[], cfd=[], stages=[], source_prefix="")
        result = metric.compute(data, SAFE)
        assert result.warnings

    def test_metric_id(self, metric, mixed_data):
        """MetricResult carries the correct metric ID."""
        result = metric.compute(mixed_data, SAFE)
        assert result.metric_id == "flow_distribution"


class TestRender:
    """Tests for FlowDistributionMetric.render()."""

    def test_returns_one_figure(self, metric, mixed_data):
        """render() returns exactly one figure (containing three subplot pies)."""
        result = metric.compute(mixed_data, SAFE)
        figs = metric.render(result, SAFE)
        assert len(figs) == 1

    def test_figure_has_two_pie_and_one_bar_trace(self, metric, mixed_data):
        """The single figure contains two pie traces and one bar trace."""
        result = metric.compute(mixed_data, SAFE)
        figs = metric.render(result, SAFE)
        pie_traces = [t for t in figs[0].data if t.type == "pie"]
        bar_traces = [t for t in figs[0].data if t.type == "bar"]
        assert len(pie_traces) == 2
        assert len(bar_traces) == 1

    def test_returns_empty_on_no_data(self, metric):
        """render() returns an empty list when compute() produced no chart data."""
        data = ReportData(issues=[], cfd=[], stages=[], source_prefix="")
        result = metric.compute(data, SAFE)
        assert metric.render(result, SAFE) == []

    def test_ct_bar_has_formatted_text(self, metric, mixed_data):
        """The CT bar trace uses pre-formatted text values ending in 'd'."""
        result = metric.compute(mixed_data, SAFE)
        figs = metric.render(result, SAFE)
        bar_trace = next(t for t in figs[0].data if t.type == "bar")
        assert all(t.endswith("d") for t in bar_trace.text)
