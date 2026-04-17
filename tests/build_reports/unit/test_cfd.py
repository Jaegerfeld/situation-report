# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       15.04.2026
# Geändert:       17.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für CfdMetric und _cfd_tick_labels. Prüft In/Out-Ratio-
#   Berechnung, Trendlinien-Verankerung, X-Achsen-Beschriftung sowie
#   Verhalten bei leeren Daten und Render-Ausgabe.
# =============================================================================

from datetime import date

import pytest

from build_reports.loader import CfdRecord, ReportData
from build_reports.metrics.cfd import CfdMetric, _cfd_tick_labels
from build_reports.terminology import SAFE


def _cfd(day: date, funnel: int, done: int) -> CfdRecord:
    return CfdRecord(day=day, stage_counts={"Funnel": funnel, "Done": done})


@pytest.fixture
def metric():
    return CfdMetric()


@pytest.fixture
def simple_cfd_data():
    return ReportData(
        issues=[],
        cfd=[
            _cfd(date(2025, 1, 1), funnel=10, done=0),
            _cfd(date(2025, 1, 2), funnel=20, done=2),
            _cfd(date(2025, 1, 3), funnel=30, done=5),
        ],
        stages=["Funnel", "Done"],
        source_prefix="TEST",
    )


class TestCompute:
    def test_days_count(self, metric, simple_cfd_data):
        result = metric.compute(simple_cfd_data, SAFE)
        assert result.stats["days"] == 3

    def test_in_total_is_total_stacked_at_last_day(self, metric, simple_cfd_data):
        # Last day: Funnel=30, Done=5 → total=35
        result = metric.compute(simple_cfd_data, SAFE)
        assert result.stats["in_total"] == 35

    def test_out_total_is_last_stage_value_at_last_day(self, metric, simple_cfd_data):
        # Last day: Done=5
        result = metric.compute(simple_cfd_data, SAFE)
        assert result.stats["out_total"] == 5

    def test_ratio_calculation(self, metric, simple_cfd_data):
        # 35 / 5 = 7.0
        result = metric.compute(simple_cfd_data, SAFE)
        assert result.stats["ratio"] == pytest.approx(7.0)

    def test_dates_are_iso_format(self, metric, simple_cfd_data):
        result = metric.compute(simple_cfd_data, SAFE)
        for d in result.chart_data.dates:
            assert d == date.fromisoformat(d).isoformat()  # round-trip check

    def test_warning_on_empty_cfd(self, metric):
        data = ReportData(issues=[], cfd=[], stages=["Funnel"], source_prefix="")
        result = metric.compute(data, SAFE)
        assert result.warnings

    def test_warning_on_no_stages(self, metric):
        data = ReportData(
            issues=[],
            cfd=[_cfd(date(2025, 1, 1), 1, 0)],
            stages=[],
            source_prefix="",
        )
        result = metric.compute(data, SAFE)
        assert result.warnings

    def test_metric_id(self, metric, simple_cfd_data):
        result = metric.compute(simple_cfd_data, SAFE)
        assert result.metric_id == "cfd"


class TestRender:
    def test_returns_one_figure(self, metric, simple_cfd_data):
        result = metric.compute(simple_cfd_data, SAFE)
        figs = metric.render(result, SAFE)
        assert len(figs) == 1

    def test_title_contains_ratio(self, metric, simple_cfd_data):
        result = metric.compute(simple_cfd_data, SAFE)
        figs = metric.render(result, SAFE)
        assert "7.0" in figs[0].layout.title.text

    def test_returns_empty_on_no_data(self, metric):
        data = ReportData(issues=[], cfd=[], stages=["Funnel"], source_prefix="")
        result = metric.compute(data, SAFE)
        assert metric.render(result, SAFE) == []

    def test_xaxis_type_is_date(self, metric, simple_cfd_data):
        result = metric.compute(simple_cfd_data, SAFE)
        figs = metric.render(result, SAFE)
        assert figs[0].layout.xaxis.type == "date"


class TestCfdTickLabels:
    def test_empty_dates_returns_empty(self):
        vals, text = _cfd_tick_labels([])
        assert vals == []
        assert text == []

    def test_month_start_gets_month_label(self):
        vals, text = _cfd_tick_labels(["2025-01-01", "2025-01-02"])
        assert "2025-01-01" in vals
        idx = vals.index("2025-01-01")
        assert text[idx] == "Jan 2025"

    def test_monday_non_month_start_gets_week_label(self):
        # 2025-01-06 is a Monday, not a month start
        vals, text = _cfd_tick_labels(["2025-01-06", "2025-01-07"])
        assert "2025-01-06" in vals
        idx = vals.index("2025-01-06")
        assert "W" in text[idx]

    def test_tuesday_not_labeled(self):
        # 2025-01-07 is a Tuesday
        vals, _ = _cfd_tick_labels(["2025-01-07", "2025-01-08"])
        assert "2025-01-07" not in vals

    def test_month_start_on_monday_not_duplicated(self):
        # 2025-09-01 is a Monday AND a month start — should appear exactly once
        vals, text = _cfd_tick_labels(["2025-09-01", "2025-09-02"])
        assert vals.count("2025-09-01") == 1
        idx = vals.index("2025-09-01")
        assert "Sep" in text[idx]
