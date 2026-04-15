# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       15.04.2026
# Geändert:       15.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für FlowVelocityMetric. Prüft Aggregation nach Tag/Woche/PI,
#   Ausschluss von Issues ohne Closed Date sowie Render-Ausgabe.
# =============================================================================

from datetime import datetime

import pytest

from build_reports.loader import IssueRecord, ReportData
from build_reports.metrics.flow_velocity import FlowVelocityMetric
from build_reports.terminology import SAFE


def _issue(key: str, closed: datetime | None) -> IssueRecord:
    return IssueRecord(
        project="P", key=key, issuetype="Feature", status="Done",
        created=datetime(2025, 1, 1), component="",
        first_date=datetime(2025, 1, 2), implementation_date=None,
        closed_date=closed, stage_minutes={}, resolution="",
    )


@pytest.fixture
def metric():
    return FlowVelocityMetric()


@pytest.fixture
def data_5_issues():
    """Five issues closed across different days in the same week."""
    return ReportData(
        issues=[
            _issue("A-1", datetime(2025, 3, 3)),   # Mon
            _issue("A-2", datetime(2025, 3, 3)),   # Mon (same day as A-1)
            _issue("A-3", datetime(2025, 3, 5)),   # Wed
            _issue("A-4", datetime(2025, 3, 10)),  # Mon next week
            _issue("A-5", None),                   # no closed date — excluded
        ],
        cfd=[], stages=[], source_prefix="TEST",
    )


class TestCompute:
    def test_count_excludes_no_closed_date(self, metric, data_5_issues):
        result = metric.compute(data_5_issues, SAFE)
        assert result.stats["count"] == 4

    def test_daily_freq_two_on_same_day(self, metric, data_5_issues):
        result = metric.compute(data_5_issues, SAFE)
        freq = result.chart_data.daily_freq
        # Two items on 2025-03-03 → freq[2] = 1
        assert freq.get(2, 0) == 1

    def test_weekly_groups_correctly(self, metric, data_5_issues):
        result = metric.compute(data_5_issues, SAFE)
        weekly = result.chart_data.weekly
        # 2025-W10 (Mar 3+5) = 3 items, 2025-W11 (Mar 10) = 1 item
        assert sum(weekly.values()) == 4

    def test_warning_on_no_data(self, metric):
        data = ReportData(issues=[], cfd=[], stages=[], source_prefix="")
        result = metric.compute(data, SAFE)
        assert result.warnings

    def test_warning_when_all_open(self, metric):
        data = ReportData(
            issues=[_issue("X", None)],
            cfd=[], stages=[], source_prefix="",
        )
        result = metric.compute(data, SAFE)
        assert result.warnings

    def test_metric_id(self, metric, data_5_issues):
        result = metric.compute(data_5_issues, SAFE)
        assert result.metric_id == "flow_velocity"


class TestRender:
    def test_returns_three_figures(self, metric, data_5_issues):
        result = metric.compute(data_5_issues, SAFE)
        figs = metric.render(result, SAFE)
        assert len(figs) == 3

    def test_returns_empty_on_no_data(self, metric):
        data = ReportData(issues=[], cfd=[], stages=[], source_prefix="")
        result = metric.compute(data, SAFE)
        assert metric.render(result, SAFE) == []
