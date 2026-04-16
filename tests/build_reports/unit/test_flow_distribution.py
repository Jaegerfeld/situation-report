# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       15.04.2026
# Geändert:       15.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für FlowDistributionMetric. Prüft Zählung nach Issuetype und
#   Status sowie Render-Ausgabe (zwei Pie-Charts als Subplots).
# =============================================================================

from datetime import datetime

import pytest

from build_reports.loader import IssueRecord, ReportData
from build_reports.metrics.flow_distribution import FlowDistributionMetric
from build_reports.terminology import SAFE


def _issue(key: str, issuetype: str, status: str) -> IssueRecord:
    return IssueRecord(
        project="P", key=key, issuetype=issuetype, status=status,
        created=datetime(2025, 1, 1), component="",
        first_date=None, implementation_date=None, closed_date=None,
        stage_minutes={}, resolution="",
    )


@pytest.fixture
def metric():
    return FlowDistributionMetric()


@pytest.fixture
def mixed_data():
    return ReportData(
        issues=[
            _issue("A-1", "Feature", "Done"),
            _issue("A-2", "Feature", "Done"),
            _issue("A-3", "Bug", "In Progress"),
            _issue("A-4", "Story", "Done"),
        ],
        cfd=[], stages=[], source_prefix="TEST",
    )


class TestCompute:
    def test_total_count(self, metric, mixed_data):
        result = metric.compute(mixed_data, SAFE)
        assert result.stats["total"] == 4

    def test_type_counts(self, metric, mixed_data):
        result = metric.compute(mixed_data, SAFE)
        counts = result.stats["type_counts"]
        assert counts["Feature"] == 2
        assert counts["Bug"] == 1
        assert counts["Story"] == 1

    def test_by_status_in_chart_data(self, metric, mixed_data):
        result = metric.compute(mixed_data, SAFE)
        by_status = result.chart_data.by_status
        assert by_status["Done"] == 3
        assert by_status["In Progress"] == 1

    def test_warning_on_empty(self, metric):
        data = ReportData(issues=[], cfd=[], stages=[], source_prefix="")
        result = metric.compute(data, SAFE)
        assert result.warnings

    def test_metric_id(self, metric, mixed_data):
        result = metric.compute(mixed_data, SAFE)
        assert result.metric_id == "flow_distribution"


class TestRender:
    def test_returns_one_figure(self, metric, mixed_data):
        result = metric.compute(mixed_data, SAFE)
        figs = metric.render(result, SAFE)
        assert len(figs) == 1

    def test_figure_has_two_pie_traces(self, metric, mixed_data):
        result = metric.compute(mixed_data, SAFE)
        figs = metric.render(result, SAFE)
        pie_traces = [t for t in figs[0].data if t.type == "pie"]
        assert len(pie_traces) == 2

    def test_returns_empty_on_no_data(self, metric):
        data = ReportData(issues=[], cfd=[], stages=[], source_prefix="")
        result = metric.compute(data, SAFE)
        assert metric.render(result, SAFE) == []
