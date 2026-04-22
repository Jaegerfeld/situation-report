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
    """Create a CfdRecord for the given day with Funnel and Done stage counts.

    Args:
        day:    Calendar date of this CFD snapshot.
        funnel: Count of issues in the Funnel stage.
        done:   Count of issues in the Done stage.

    Returns:
        CfdRecord with stage_counts {'Funnel': funnel, 'Done': done}.
    """
    return CfdRecord(day=day, stage_counts={"Funnel": funnel, "Done": done})


@pytest.fixture
def metric() -> CfdMetric:
    """Return a default CfdMetric instance."""
    return CfdMetric()


@pytest.fixture
def simple_cfd_data() -> ReportData:
    """ReportData with three CFD records (Jan 1–3 2025) and two stages: Funnel and Done.

    Values represent daily ENTRY COUNTS (how many issues entered each stage that day).
    build_reports accumulates these into running totals before charting.
    """
    return ReportData(
        issues=[],
        cfd=[
            _cfd(date(2025, 1, 1), funnel=10, done=0),
            _cfd(date(2025, 1, 2), funnel=5,  done=2),
            _cfd(date(2025, 1, 3), funnel=5,  done=3),
        ],
        stages=["Funnel", "Done"],
        source_prefix="TEST",
    )


class TestCompute:
    """Tests for CfdMetric.compute() — ratio and series preparation."""

    def test_days_count(self, metric, simple_cfd_data):
        """stats['days'] equals the number of CFD records loaded."""
        result = metric.compute(simple_cfd_data, SAFE)
        assert result.stats["days"] == 3

    def test_in_total_is_total_stacked_at_last_day(self, metric, simple_cfd_data):
        """in_total equals the sum of cumulated stage counts on the last day.

        Daily entries: Funnel [10,5,5] → cumulated [10,15,20]; Done [0,2,3] → [0,2,5].
        Last day cumulated: Funnel=20, Done=5 → total=25.
        """
        result = metric.compute(simple_cfd_data, SAFE)
        assert result.stats["in_total"] == 25

    def test_out_total_is_last_stage_value_at_last_day(self, metric, simple_cfd_data):
        """out_total equals the cumulated count of the last stage (Done) on the last day."""
        # Done: [0,2,3] → cumulated [0,2,5] → last day = 5
        result = metric.compute(simple_cfd_data, SAFE)
        assert result.stats["out_total"] == 5

    def test_ratio_calculation(self, metric, simple_cfd_data):
        """In/Out ratio is computed as in_total / out_total rounded to 2 decimals."""
        # 25 / 5 = 5.0
        result = metric.compute(simple_cfd_data, SAFE)
        assert result.stats["ratio"] == pytest.approx(5.0)

    def test_series_cumulated(self, metric, simple_cfd_data):
        """Stage series are accumulated into running totals before charting."""
        result = metric.compute(simple_cfd_data, SAFE)
        cd = result.chart_data
        # Funnel: daily [10,5,5] → cumulated [10,15,20]
        assert cd.stage_series["Funnel"] == [10, 15, 20]
        # Done: daily [0,2,3] → cumulated [0,2,5]
        assert cd.stage_series["Done"] == [0, 2, 5]

    def test_dates_are_iso_format(self, metric, simple_cfd_data):
        """All dates in chart_data.dates are valid ISO-8601 strings."""
        result = metric.compute(simple_cfd_data, SAFE)
        for d in result.chart_data.dates:
            assert d == date.fromisoformat(d).isoformat()  # round-trip check

    def test_warning_on_empty_cfd(self, metric):
        """A warning is produced when no CFD records are present in the dataset."""
        data = ReportData(issues=[], cfd=[], stages=["Funnel"], source_prefix="")
        result = metric.compute(data, SAFE)
        assert result.warnings

    def test_warning_on_no_stages(self, metric):
        """A warning is produced when stages list is empty."""
        data = ReportData(
            issues=[],
            cfd=[_cfd(date(2025, 1, 1), 1, 0)],
            stages=[],
            source_prefix="",
        )
        result = metric.compute(data, SAFE)
        assert result.warnings

    def test_metric_id(self, metric, simple_cfd_data):
        """MetricResult carries the correct metric ID."""
        result = metric.compute(simple_cfd_data, SAFE)
        assert result.metric_id == "cfd"


class TestRender:
    """Tests for CfdMetric.render() — stacked area chart output."""

    def test_returns_one_figure(self, metric, simple_cfd_data):
        """render() returns exactly one figure."""
        result = metric.compute(simple_cfd_data, SAFE)
        figs = metric.render(result, SAFE)
        assert len(figs) == 1

    def test_title_contains_ratio(self, metric, simple_cfd_data):
        """The figure title contains the computed In/Out ratio value (5.0)."""
        result = metric.compute(simple_cfd_data, SAFE)
        figs = metric.render(result, SAFE)
        assert "5.0" in figs[0].layout.title.text

    def test_returns_empty_on_no_data(self, metric):
        """render() returns an empty list when compute() produced no chart data."""
        data = ReportData(issues=[], cfd=[], stages=["Funnel"], source_prefix="")
        result = metric.compute(data, SAFE)
        assert metric.render(result, SAFE) == []

    def test_xaxis_type_is_date(self, metric, simple_cfd_data):
        """The x-axis type is set to 'date' for correct plotly date formatting."""
        result = metric.compute(simple_cfd_data, SAFE)
        figs = metric.render(result, SAFE)
        assert figs[0].layout.xaxis.type == "date"


class TestCfdTickLabels:
    """Tests for _cfd_tick_labels() — x-axis label generation for the CFD chart."""

    def test_empty_dates_returns_empty(self):
        """Empty input yields empty tickvals and ticktext."""
        vals, text = _cfd_tick_labels([])
        assert vals == []
        assert text == []

    def test_month_start_gets_month_label(self):
        """The first day of a month receives a 'Mon YYYY' label."""
        vals, text = _cfd_tick_labels(["2025-01-01", "2025-01-02"])
        assert "2025-01-01" in vals
        idx = vals.index("2025-01-01")
        assert text[idx] == "Jan 2025"

    def test_monday_non_month_start_gets_week_label(self):
        """A Monday that is not a month start receives an HTML-formatted week label."""
        # 2025-01-06 is a Monday, not a month start
        vals, text = _cfd_tick_labels(["2025-01-06", "2025-01-07"])
        assert "2025-01-06" in vals
        idx = vals.index("2025-01-06")
        assert "W" in text[idx]

    def test_tuesday_not_labeled(self):
        """A Tuesday that is not a month start receives no tick label."""
        # 2025-01-07 is a Tuesday
        vals, _ = _cfd_tick_labels(["2025-01-07", "2025-01-08"])
        assert "2025-01-07" not in vals

    def test_month_start_on_monday_not_duplicated(self):
        """A date that is both a Monday and a month start appears exactly once with the month label."""
        # 2025-09-01 is a Monday AND a month start — should appear exactly once
        vals, text = _cfd_tick_labels(["2025-09-01", "2025-09-02"])
        assert vals.count("2025-09-01") == 1
        idx = vals.index("2025-09-01")
        assert "Sep" in text[idx]
