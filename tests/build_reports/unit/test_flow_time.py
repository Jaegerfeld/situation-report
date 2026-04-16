# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       15.04.2026
# Geändert:       15.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für die FlowTimeMetric. Prüft Berechnung der Cycle Time,
#   Ausschluss ungültiger Issues (kein First/Closed Date, Zero-Day),
#   Statistikwerte und die Render-Ausgabe (Anzahl und Typ der Figures).
# =============================================================================

from datetime import datetime

import pytest

from build_reports.loader import IssueRecord, ReportData
from build_reports.metrics.flow_time import FlowTimeMetric
from build_reports.terminology import GLOBAL, SAFE


def _issue(key: str, first: datetime | None, closed: datetime | None) -> IssueRecord:
    """Helper: create a minimal IssueRecord with given dates."""
    return IssueRecord(
        project="P", key=key, issuetype="Feature", status="Done",
        created=datetime(2025, 1, 1), component="",
        first_date=first, implementation_date=None, closed_date=closed,
        stage_minutes={}, resolution="",
    )


@pytest.fixture
def metric() -> FlowTimeMetric:
    return FlowTimeMetric()


@pytest.fixture
def simple_data() -> ReportData:
    """Three issues: 10, 20, 30 days cycle time."""
    base = datetime(2025, 1, 1)
    return ReportData(
        issues=[
            _issue("A-1", datetime(2025, 1, 1), datetime(2025, 1, 11)),  # 10 days
            _issue("A-2", datetime(2025, 1, 1), datetime(2025, 1, 21)),  # 20 days
            _issue("A-3", datetime(2025, 1, 1), datetime(2025, 1, 31)),  # 30 days
        ],
        cfd=[], stages=[], source_prefix="TEST",
    )


class TestCompute:
    def test_count(self, metric, simple_data):
        result = metric.compute(simple_data, SAFE)
        assert result.stats["count"] == 3

    def test_median(self, metric, simple_data):
        result = metric.compute(simple_data, SAFE)
        assert result.stats["median"] == 20.0

    def test_min_max(self, metric, simple_data):
        result = metric.compute(simple_data, SAFE)
        assert result.stats["min"] == 10.0
        assert result.stats["max"] == 30.0

    def test_mean(self, metric, simple_data):
        result = metric.compute(simple_data, SAFE)
        assert result.stats["mean"] == pytest.approx(20.0)

    def test_excludes_missing_first_date(self, metric):
        data = ReportData(
            issues=[_issue("X", None, datetime(2025, 2, 1))],
            cfd=[], stages=[], source_prefix="",
        )
        result = metric.compute(data, SAFE)
        assert result.stats.get("count", 0) == 0

    def test_excludes_missing_closed_date(self, metric):
        data = ReportData(
            issues=[_issue("X", datetime(2025, 1, 1), None)],
            cfd=[], stages=[], source_prefix="",
        )
        result = metric.compute(data, SAFE)
        assert result.stats.get("count", 0) == 0

    def test_excludes_zero_day_issues(self, metric):
        data = ReportData(
            issues=[_issue("X", datetime(2025, 1, 1), datetime(2025, 1, 1))],
            cfd=[], stages=[], source_prefix="",
        )
        result = metric.compute(data, SAFE)
        assert result.stats.get("count", 0) == 0
        assert result.stats.get("zero_day_count", 0) == 1

    def test_warning_on_empty_data(self, metric):
        data = ReportData(issues=[], cfd=[], stages=[], source_prefix="")
        result = metric.compute(data, SAFE)
        assert result.warnings

    def test_metric_id(self, metric, simple_data):
        result = metric.compute(simple_data, SAFE)
        assert result.metric_id == "flow_time"


class TestRender:
    def test_returns_two_figures(self, metric, simple_data):
        result = metric.compute(simple_data, SAFE)
        figures = metric.render(result, SAFE)
        assert len(figures) == 2

    def test_returns_empty_on_no_data(self, metric):
        data = ReportData(issues=[], cfd=[], stages=[], source_prefix="")
        result = metric.compute(data, SAFE)
        figures = metric.render(result, SAFE)
        assert figures == []

    def test_global_terminology_in_title(self, metric, simple_data):
        result = metric.compute(simple_data, GLOBAL)
        figures = metric.render(result, GLOBAL)
        assert "Cycle Time" in figures[0].layout.title.text

    def test_safe_terminology_in_title(self, metric, simple_data):
        result = metric.compute(simple_data, SAFE)
        figures = metric.render(result, SAFE)
        assert "Flow Time" in figures[0].layout.title.text
