# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       15.04.2026
# Geändert:       15.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für FlowLoadMetric. Prüft Trennung open/closed, Altersberechnung,
#   Stage-Zuordnung und Render-Ausgabe.
# =============================================================================

from datetime import datetime

import pytest

from build_reports.loader import IssueRecord, ReportData
from build_reports.metrics.flow_load import FlowLoadMetric, _age_days, _current_stage
from build_reports.terminology import SAFE


def _issue(key: str, closed: datetime | None = None,
           stage_minutes: dict | None = None,
           first: datetime | None = None) -> IssueRecord:
    return IssueRecord(
        project="P", key=key, issuetype="Feature", status="In Progress",
        created=datetime(2025, 1, 1), component="",
        first_date=first or datetime(2025, 1, 2),
        implementation_date=None, closed_date=closed,
        stage_minutes=stage_minutes or {}, resolution="",
    )


STAGES = ["Funnel", "Analysis", "Implementation", "Done"]


@pytest.fixture
def metric():
    return FlowLoadMetric()


@pytest.fixture
def mixed_data():
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
    def test_returns_last_nonzero_stage(self):
        issue = _issue("X", stage_minutes={"Funnel": 10, "Analysis": 20, "Implementation": 0, "Done": 0})
        assert _current_stage(issue, STAGES) == "Analysis"

    def test_fallback_to_first_stage_when_all_zero(self):
        issue = _issue("X", stage_minutes={"Funnel": 0, "Analysis": 0})
        assert _current_stage(issue, ["Funnel", "Analysis"]) == "Funnel"

    def test_single_stage_with_time(self):
        issue = _issue("X", stage_minutes={"Funnel": 5})
        assert _current_stage(issue, ["Funnel"]) == "Funnel"


class TestCompute:
    def test_only_open_issues_counted(self, metric, mixed_data):
        result = metric.compute(mixed_data, SAFE)
        assert result.stats["open_count"] == 2

    def test_warning_when_no_open_issues(self, metric):
        data = ReportData(
            issues=[_issue("C-1", closed=datetime(2025, 3, 1))],
            cfd=[], stages=STAGES, source_prefix="",
        )
        result = metric.compute(data, SAFE)
        assert result.warnings

    def test_done_count_from_closed_issues(self, metric, mixed_data):
        result = metric.compute(mixed_data, SAFE)
        assert result.stats["done_count"] > 0

    def test_mean_age_positive(self, metric, mixed_data):
        result = metric.compute(mixed_data, SAFE)
        assert result.stats["mean_age"] > 0

    def test_metric_id(self, metric, mixed_data):
        result = metric.compute(mixed_data, SAFE)
        assert result.metric_id == "flow_load"


class TestRender:
    def test_returns_one_figure(self, metric, mixed_data):
        result = metric.compute(mixed_data, SAFE)
        figs = metric.render(result, SAFE)
        assert len(figs) == 1

    def test_returns_empty_on_no_data(self, metric):
        data = ReportData(
            issues=[_issue("C-1", closed=datetime(2025, 3, 1))],
            cfd=[], stages=STAGES, source_prefix="",
        )
        result = metric.compute(data, SAFE)
        assert metric.render(result, SAFE) == []
