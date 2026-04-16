# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       15.04.2026
# Geändert:       16.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für die FlowTimeMetric. Prüft beide CT-Berechnungsmethoden
#   (A: Datumsdifferenz, B: Stage-Minuten-Summe), Ausschluss ungültiger Issues
#   (kein First/Closed Date, Zero-Day), Statistikwerte und Render-Ausgabe.
# =============================================================================

from datetime import datetime

import pytest

from build_reports.loader import IssueRecord, ReportData
from build_reports.metrics.flow_time import CT_METHOD_A, CT_METHOD_B, FlowTimeMetric
from build_reports.terminology import GLOBAL, SAFE

STAGES = ["Analysis", "Implementation", "Done"]


def _issue(
    key: str,
    first: datetime | None,
    closed: datetime | None,
    stage_minutes: dict | None = None,
) -> IssueRecord:
    """Helper: create a minimal IssueRecord with given dates and optional stage minutes."""
    return IssueRecord(
        project="P", key=key, issuetype="Feature", status="Done",
        created=datetime(2025, 1, 1), component="",
        first_date=first, implementation_date=None, closed_date=closed,
        stage_minutes=stage_minutes or {}, resolution="",
    )


@pytest.fixture
def metric() -> FlowTimeMetric:
    return FlowTimeMetric()


@pytest.fixture
def metric_b() -> FlowTimeMetric:
    """FlowTimeMetric configured for Method B."""
    m = FlowTimeMetric()
    m.ct_method = CT_METHOD_B
    return m


@pytest.fixture
def simple_data() -> ReportData:
    """Three issues: 10, 20, 30 days cycle time (Method A)."""
    return ReportData(
        issues=[
            _issue("A-1", datetime(2025, 1, 1), datetime(2025, 1, 11)),  # 10 days
            _issue("A-2", datetime(2025, 1, 1), datetime(2025, 1, 21)),  # 20 days
            _issue("A-3", datetime(2025, 1, 1), datetime(2025, 1, 31)),  # 30 days
        ],
        cfd=[], stages=STAGES, source_prefix="TEST",
    )


@pytest.fixture
def stage_data() -> ReportData:
    """Three issues with stage minutes for Method B testing.

    Stages: Analysis, Implementation, Done (Done is excluded as last stage).
    Issue A-1: 1440 + 2880 = 4320 min = 3.0 days
    Issue A-2: 2880 + 2880 = 5760 min = 4.0 days
    Issue A-3: 1440 + 4320 = 5760 min = 4.0 days (intentionally same as A-2)
    """
    base_first = datetime(2025, 1, 1)
    base_closed = datetime(2025, 2, 1)
    return ReportData(
        issues=[
            _issue("A-1", base_first, base_closed,
                   {"Analysis": 1440, "Implementation": 2880, "Done": 0}),
            _issue("A-2", base_first, base_closed,
                   {"Analysis": 2880, "Implementation": 2880, "Done": 0}),
            _issue("A-3", base_first, base_closed,
                   {"Analysis": 1440, "Implementation": 4320, "Done": 0}),
        ],
        cfd=[], stages=STAGES, source_prefix="TEST",
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


class TestComputeMethodB:
    def test_uses_stage_minutes_not_dates(self, metric_b, stage_data):
        """Method B computes days from stage minutes, not from date difference."""
        result = metric_b.compute(stage_data, SAFE)
        # A-1: (1440 + 2880) / 1440 = 3.0 days
        assert 3.0 in [p.cycle_days for p in result.chart_data]

    def test_count(self, metric_b, stage_data):
        result = metric_b.compute(stage_data, SAFE)
        assert result.stats["count"] == 3

    def test_median(self, metric_b, stage_data):
        # values: 3.0, 4.0, 4.0 → median = 4.0
        result = metric_b.compute(stage_data, SAFE)
        assert result.stats["median"] == 4.0

    def test_min(self, metric_b, stage_data):
        result = metric_b.compute(stage_data, SAFE)
        assert result.stats["min"] == 3.0

    def test_excludes_zero_stage_minutes(self, metric_b):
        """Issue with all-zero stage minutes is treated as zero-day and excluded."""
        data = ReportData(
            issues=[_issue("X", datetime(2025, 1, 1), datetime(2025, 2, 1),
                           {"Analysis": 0, "Implementation": 0, "Done": 0})],
            cfd=[], stages=STAGES, source_prefix="",
        )
        result = metric_b.compute(data, SAFE)
        assert result.stats.get("count", 0) == 0
        assert result.stats["zero_day_count"] == 1

    def test_last_stage_excluded(self, metric_b):
        """Done stage minutes are not counted in Method B."""
        data = ReportData(
            issues=[_issue("X", datetime(2025, 1, 1), datetime(2025, 2, 1),
                           {"Analysis": 0, "Implementation": 0, "Done": 1440})],
            cfd=[], stages=STAGES, source_prefix="",
        )
        result = metric_b.compute(data, SAFE)
        # Done is excluded → 0 minutes → zero_day_count
        assert result.stats.get("count", 0) == 0

    def test_ct_method_in_stats(self, metric_b, stage_data):
        result = metric_b.compute(stage_data, SAFE)
        assert result.stats["ct_method"] == CT_METHOD_B

    def test_method_a_ct_method_in_stats(self, metric, simple_data):
        result = metric.compute(simple_data, SAFE)
        assert result.stats["ct_method"] == CT_METHOD_A


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

    def test_method_label_in_title(self, metric, simple_data):
        result = metric.compute(simple_data, SAFE)
        figures = metric.render(result, SAFE)
        assert "Methode A" in figures[0].layout.title.text

    def test_method_b_label_in_title(self, metric_b, stage_data):
        result = metric_b.compute(stage_data, SAFE)
        figures = metric_b.render(result, SAFE)
        assert "Methode B" in figures[0].layout.title.text
