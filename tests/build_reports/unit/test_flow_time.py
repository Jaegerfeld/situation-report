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
from build_reports.metrics.flow_time import (
    CT_METHOD_A, CT_METHOD_B, FlowTimeMetric, _loess, _month_ticks, _point_color,
)
from build_reports.terminology import GLOBAL, SAFE

STAGES = ["Analysis", "Implementation", "Done"]


def _issue(
    key: str,
    first: datetime | None,
    closed: datetime | None,
    stage_minutes: dict | None = None,
) -> IssueRecord:
    """Create a minimal IssueRecord with given dates and optional stage minutes.

    Args:
        key:           Unique issue key.
        first:         First active date (First Date), or None.
        closed:        Closed datetime (Closed Date), or None.
        stage_minutes: Dict of stage name to minutes spent; defaults to empty.

    Returns:
        IssueRecord with project 'P' and issuetype 'Feature'.
    """
    return IssueRecord(
        project="P", key=key, issuetype="Feature", status="Done",
        created=datetime(2025, 1, 1), component="",
        first_date=first, implementation_date=None, closed_date=closed,
        stage_minutes=stage_minutes or {}, resolution="",
    )


@pytest.fixture
def metric() -> FlowTimeMetric:
    """Return a default FlowTimeMetric instance configured for Method A (date diff)."""
    return FlowTimeMetric()


@pytest.fixture
def metric_b() -> FlowTimeMetric:
    """Return a FlowTimeMetric instance configured for Method B (stage minutes)."""
    m = FlowTimeMetric()
    m.ct_method = CT_METHOD_B
    return m


@pytest.fixture
def simple_data() -> ReportData:
    """ReportData with three issues with cycle times of 10, 20, and 30 days (Method A)."""
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
    """ReportData with three issues containing stage minutes for Method B testing.

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
    """Tests for FlowTimeMetric.compute() with Method A (calendar day difference)."""

    def test_count(self, metric, simple_data):
        """count stat equals the number of eligible issues."""
        result = metric.compute(simple_data, SAFE)
        assert result.stats["count"] == 3

    def test_median(self, metric, simple_data):
        """Median cycle time is computed correctly from the sorted values."""
        result = metric.compute(simple_data, SAFE)
        assert result.stats["median"] == 20.0

    def test_min_max(self, metric, simple_data):
        """min and max stats reflect the smallest and largest cycle times."""
        result = metric.compute(simple_data, SAFE)
        assert result.stats["min"] == 10.0
        assert result.stats["max"] == 30.0

    def test_mean(self, metric, simple_data):
        """Mean cycle time is approximately the arithmetic average."""
        result = metric.compute(simple_data, SAFE)
        assert result.stats["mean"] == pytest.approx(20.0)

    def test_excludes_missing_first_date(self, metric):
        """Issues without a First Date are excluded from cycle time computation."""
        data = ReportData(
            issues=[_issue("X", None, datetime(2025, 2, 1))],
            cfd=[], stages=[], source_prefix="",
        )
        result = metric.compute(data, SAFE)
        assert result.stats.get("count", 0) == 0

    def test_excludes_missing_closed_date(self, metric):
        """Issues without a Closed Date are excluded from cycle time computation."""
        data = ReportData(
            issues=[_issue("X", datetime(2025, 1, 1), None)],
            cfd=[], stages=[], source_prefix="",
        )
        result = metric.compute(data, SAFE)
        assert result.stats.get("count", 0) == 0

    def test_excludes_zero_day_issues(self, metric):
        """Issues with cycle time ≤ 0 are excluded and counted as zero_day_count."""
        data = ReportData(
            issues=[_issue("X", datetime(2025, 1, 1), datetime(2025, 1, 1))],
            cfd=[], stages=[], source_prefix="",
        )
        result = metric.compute(data, SAFE)
        assert result.stats.get("count", 0) == 0
        assert result.stats.get("zero_day_count", 0) == 1

    def test_zero_day_records_stored(self, metric):
        """Zero-day issues are stored in stats['zero_day_records'] for export."""
        data = ReportData(
            issues=[_issue("X", datetime(2025, 1, 1), datetime(2025, 1, 1))],
            cfd=[], stages=[], source_prefix="",
        )
        result = metric.compute(data, SAFE)
        records = result.stats.get("zero_day_records", [])
        assert len(records) == 1
        assert records[0].key == "X"

    def test_normal_issues_not_in_zero_day_records(self, metric, simple_data):
        """Issues with positive cycle time do not appear in zero_day_records."""
        result = metric.compute(simple_data, SAFE)
        assert result.stats.get("zero_day_records", []) == []

    def test_warning_on_empty_data(self, metric):
        """A warning is produced when no eligible issues exist."""
        data = ReportData(issues=[], cfd=[], stages=[], source_prefix="")
        result = metric.compute(data, SAFE)
        assert result.warnings

    def test_metric_id(self, metric, simple_data):
        """MetricResult carries the correct metric ID."""
        result = metric.compute(simple_data, SAFE)
        assert result.metric_id == "flow_time"


class TestComputeMethodB:
    """Tests for FlowTimeMetric.compute() with Method B (sum of stage minutes)."""

    def test_uses_stage_minutes_not_dates(self, metric_b, stage_data):
        """Method B computes cycle time from stage minutes, not from date difference."""
        result = metric_b.compute(stage_data, SAFE)
        # A-1: (1440 + 2880) / 1440 = 3.0 days
        assert 3.0 in [p.cycle_days for p in result.chart_data]

    def test_count(self, metric_b, stage_data):
        """count stat equals the number of eligible issues under Method B."""
        result = metric_b.compute(stage_data, SAFE)
        assert result.stats["count"] == 3

    def test_median(self, metric_b, stage_data):
        """Median is correct: values 3.0, 4.0, 4.0 → median = 4.0."""
        result = metric_b.compute(stage_data, SAFE)
        assert result.stats["median"] == 4.0

    def test_min(self, metric_b, stage_data):
        """Minimum cycle time under Method B is 3.0 days."""
        result = metric_b.compute(stage_data, SAFE)
        assert result.stats["min"] == 3.0

    def test_excludes_zero_stage_minutes(self, metric_b):
        """An issue with all-zero stage minutes is treated as zero-day and excluded."""
        data = ReportData(
            issues=[_issue("X", datetime(2025, 1, 1), datetime(2025, 2, 1),
                           {"Analysis": 0, "Implementation": 0, "Done": 0})],
            cfd=[], stages=STAGES, source_prefix="",
        )
        result = metric_b.compute(data, SAFE)
        assert result.stats.get("count", 0) == 0
        assert result.stats["zero_day_count"] == 1

    def test_last_stage_excluded(self, metric_b):
        """Done stage minutes are not counted towards cycle time in Method B."""
        data = ReportData(
            issues=[_issue("X", datetime(2025, 1, 1), datetime(2025, 2, 1),
                           {"Analysis": 0, "Implementation": 0, "Done": 1440})],
            cfd=[], stages=STAGES, source_prefix="",
        )
        result = metric_b.compute(data, SAFE)
        # Done is excluded → 0 minutes → zero_day_count
        assert result.stats.get("count", 0) == 0

    def test_ct_method_in_stats(self, metric_b, stage_data):
        """stats['ct_method'] is set to CT_METHOD_B when Method B is active."""
        result = metric_b.compute(stage_data, SAFE)
        assert result.stats["ct_method"] == CT_METHOD_B

    def test_method_a_ct_method_in_stats(self, metric, simple_data):
        """stats['ct_method'] is set to CT_METHOD_A when Method A is active."""
        result = metric.compute(simple_data, SAFE)
        assert result.stats["ct_method"] == CT_METHOD_A


class TestRender:
    """Tests for FlowTimeMetric.render() — boxplot and scatterplot output."""

    def test_returns_two_figures(self, metric, simple_data):
        """render() returns exactly two figures: boxplot and scatterplot."""
        result = metric.compute(simple_data, SAFE)
        figures = metric.render(result, SAFE)
        assert len(figures) == 2

    def test_returns_empty_on_no_data(self, metric):
        """render() returns an empty list when compute() produced no chart data."""
        data = ReportData(issues=[], cfd=[], stages=[], source_prefix="")
        result = metric.compute(data, SAFE)
        figures = metric.render(result, SAFE)
        assert figures == []

    def test_global_terminology_in_title(self, metric, simple_data):
        """Global mode uses 'Cycle Time' in the figure title."""
        result = metric.compute(simple_data, GLOBAL)
        figures = metric.render(result, GLOBAL)
        assert "Cycle Time" in figures[0].layout.title.text

    def test_safe_terminology_in_title(self, metric, simple_data):
        """SAFe mode uses 'Flow Time' in the figure title."""
        result = metric.compute(simple_data, SAFE)
        figures = metric.render(result, SAFE)
        assert "Flow Time" in figures[0].layout.title.text

    def test_method_label_in_title(self, metric, simple_data):
        """Method A is identified as 'Methode A' in the figure title."""
        result = metric.compute(simple_data, SAFE)
        figures = metric.render(result, SAFE)
        assert "Methode A" in figures[0].layout.title.text

    def test_method_b_label_in_title(self, metric_b, stage_data):
        """Method B is identified as 'Methode B' in the figure title."""
        result = metric_b.compute(stage_data, SAFE)
        figures = metric_b.render(result, SAFE)
        assert "Methode B" in figures[0].layout.title.text

    def test_scatterplot_has_loess_trace(self, metric, simple_data):
        """The scatterplot contains a LOESS trendline trace."""
        result = metric.compute(simple_data, SAFE)
        figures = metric.render(result, SAFE)
        scatter = figures[1]
        trace_names = [t.name for t in scatter.data]
        assert any("LOESS" in (n or "") for n in trace_names)

    def test_scatterplot_has_three_reference_lines(self, metric, simple_data):
        """The scatterplot contains three reference lines (median, 85th, 95th pct)."""
        result = metric.compute(simple_data, SAFE)
        figures = metric.render(result, SAFE)
        scatter = figures[1]
        # add_hline creates layout shapes
        assert len(scatter.layout.shapes) == 3

    def test_scatterplot_reference_lines_dotted(self, metric, simple_data):
        """All reference lines in the scatterplot use a dotted line style."""
        result = metric.compute(simple_data, SAFE)
        figures = metric.render(result, SAFE)
        scatter = figures[1]
        for shape in scatter.layout.shapes:
            assert shape.line.dash == "dot"

    def test_scatterplot_has_month_ticks(self, metric, simple_data):
        """The scatterplot x-axis uses array tick mode with custom month labels."""
        result = metric.compute(simple_data, SAFE)
        figures = metric.render(result, SAFE)
        scatter = figures[1]
        assert scatter.layout.xaxis.tickmode == "array"
        assert len(scatter.layout.xaxis.tickvals) > 0

    def test_stats_has_pct85_and_pct95(self, metric, simple_data):
        """stats contains both 85th and 95th percentile values."""
        result = metric.compute(simple_data, SAFE)
        assert "pct85" in result.stats
        assert "pct95" in result.stats

    def test_boxplot_outlier_marker_color_is_red(self, metric, simple_data):
        """Outlier markers in the boxplot are colored red."""
        result = metric.compute(simple_data, SAFE)
        figures = metric.render(result, SAFE)
        boxplot = figures[0]
        assert boxplot.data[0].marker.color == "red"

    def test_boxplot_fill_color_is_orange(self, metric, simple_data):
        """The boxplot fill color is orange."""
        result = metric.compute(simple_data, SAFE)
        figures = metric.render(result, SAFE)
        boxplot = figures[0]
        assert boxplot.data[0].fillcolor == "orange"

    def test_boxplot_has_issue_key_tooltips(self, metric, simple_data):
        """The boxplot trace includes issue key tooltips for each data point."""
        result = metric.compute(simple_data, SAFE)
        figures = metric.render(result, SAFE)
        boxplot = figures[0]
        trace = boxplot.data[0]
        assert trace.text is not None
        assert len(trace.text) == len(simple_data.issues)
        assert trace.hovertemplate is not None
        assert "%{text}" in trace.hovertemplate


class TestLoess:
    """Tests for _loess() — locally weighted regression helper."""

    def test_same_length_as_input(self):
        """Output list has the same length as the input lists."""
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [2.0, 4.0, 5.0, 4.0, 2.0]
        assert len(_loess(x, y)) == 5

    def test_returns_list_of_floats(self):
        """All output values are floats."""
        x = list(range(10))
        y = [float(i) for i in range(10)]
        result = _loess(x, y)
        assert all(isinstance(v, float) for v in result)

    def test_constant_input_returns_constant(self):
        """A constant y series produces a constant smoothed output."""
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [7.0] * 5
        result = _loess(x, y)
        assert all(abs(v - 7.0) < 1e-6 for v in result)

    def test_short_input_returned_unchanged(self):
        """Inputs shorter than 3 points are returned unchanged."""
        assert _loess([1.0], [5.0]) == [5.0]
        assert _loess([1.0, 2.0], [3.0, 4.0]) == [3.0, 4.0]

    def test_linear_input_approximately_linear(self):
        """LOESS on a linear series stays close to the original values."""
        x = [float(i) for i in range(20)]
        y = [2.0 * i + 1.0 for i in range(20)]
        result = _loess(x, y)
        for i, v in enumerate(result):
            assert abs(v - y[i]) < 3.0  # LOESS on a line should stay close


class TestMonthTicks:
    """Tests for _month_ticks() — monthly x-axis label generation."""

    def test_empty_input_returns_empty(self):
        """Empty date list produces empty tick lists."""
        vals, text = _month_ticks([])
        assert vals == []
        assert text == []

    def test_equal_length_output(self):
        """tickvals and ticktext always have the same length."""
        dates = [datetime(2025, 3, 15), datetime(2025, 5, 20)]
        vals, text = _month_ticks(dates)
        assert len(vals) == len(text)

    def test_january_includes_year(self):
        """January tick labels include the year (e.g. 'Jan 2025')."""
        dates = [datetime(2025, 1, 10), datetime(2025, 3, 10)]
        _, text = _month_ticks(dates)
        jan_labels = [t for t in text if "2025" in t]
        assert len(jan_labels) >= 1

    def test_odd_months_have_name(self):
        """Odd-numbered months receive an abbreviated name label."""
        dates = [datetime(2025, 1, 1), datetime(2025, 6, 30)]
        vals, text = _month_ticks(dates)
        # Month 3 (Mär) is odd → should appear as text label
        mar_entry = next(
            (text[i] for i, v in enumerate(vals) if v == "2025-03-01"), None
        )
        assert mar_entry is not None
        assert mar_entry != "·"

    def test_even_months_have_dot(self):
        """Even-numbered months receive a small dot marker '·' as label."""
        dates = [datetime(2025, 1, 1), datetime(2025, 6, 30)]
        vals, text = _month_ticks(dates)
        # Month 2 (Feb) is even → should be "·"
        feb_entry = next(
            (text[i] for i, v in enumerate(vals) if v == "2025-02-01"), None
        )
        assert feb_entry == "·"

    def test_tickvals_are_iso_strings(self):
        """All tickvals are valid ISO-8601 date strings in YYYY-MM-DD format."""
        dates = [datetime(2025, 4, 10)]
        vals, _ = _month_ticks(dates)
        for v in vals:
            assert len(v) == 10 and v[4] == "-" and v[7] == "-"


class TestPointColor:
    """Tests for _point_color() — percentile-based scatter point colour coding."""

    def test_below_pct85_is_steelblue(self):
        """Points below the 85th percentile are colored steelblue."""
        assert _point_color(5.0, pct85=10.0, pct95=20.0) == "steelblue"

    def test_at_pct85_is_orange(self):
        """Points exactly at the 85th percentile are colored orange."""
        assert _point_color(10.0, pct85=10.0, pct95=20.0) == "orange"

    def test_between_pct85_and_pct95_is_orange(self):
        """Points between the 85th and 95th percentiles are colored orange."""
        assert _point_color(15.0, pct85=10.0, pct95=20.0) == "orange"

    def test_at_pct95_is_red(self):
        """Points exactly at the 95th percentile are colored red."""
        assert _point_color(20.0, pct85=10.0, pct95=20.0) == "red"

    def test_above_pct95_is_red(self):
        """Points above the 95th percentile are colored red."""
        assert _point_color(25.0, pct85=10.0, pct95=20.0) == "red"

    def test_pct85_equals_pct95_at_value_is_red(self):
        """When both thresholds collapse to the same value, the 95th rule applies."""
        assert _point_color(30.0, pct85=30.0, pct95=30.0) == "red"

    def test_pct85_equals_pct95_below_is_steelblue(self):
        """Points below collapsed thresholds are colored steelblue."""
        assert _point_color(29.0, pct85=30.0, pct95=30.0) == "steelblue"


class TestScatterColors:
    """Verify per-point colour coding in the scatterplot figure."""

    @pytest.fixture
    def many_data(self) -> ReportData:
        """ReportData with 10 issues with cycle times 1–10 days for deterministic percentile checks."""
        base = datetime(2025, 1, 1)
        issues = [
            _issue(f"A-{i}", base, datetime(2025, 1, 1 + i), {})
            for i in range(1, 11)
        ]
        return ReportData(issues=issues, cfd=[], stages=STAGES, source_prefix="TEST")

    def test_scatter_marker_color_is_list(self, many_data):
        """Scatter point colors are represented as a list (one per data point)."""
        metric = FlowTimeMetric()
        result = metric.compute(many_data, SAFE)
        figures = metric.render(result, SAFE)
        scatter_trace = figures[1].data[0]
        assert isinstance(scatter_trace.marker.color, (list, tuple))

    def test_highest_point_is_red(self, many_data):
        """The data point with the highest cycle time is colored red (≥ 95th pct)."""
        metric = FlowTimeMetric()
        result = metric.compute(many_data, SAFE)
        figures = metric.render(result, SAFE)
        scatter_trace = figures[1].data[0]
        colors = list(scatter_trace.marker.color)
        y_values = list(scatter_trace.y)
        max_idx = y_values.index(max(y_values))
        assert colors[max_idx] == "red"

    def test_lowest_point_is_steelblue(self, many_data):
        """The data point with the lowest cycle time is colored steelblue (< 85th pct)."""
        metric = FlowTimeMetric()
        result = metric.compute(many_data, SAFE)
        figures = metric.render(result, SAFE)
        scatter_trace = figures[1].data[0]
        colors = list(scatter_trace.marker.color)
        y_values = list(scatter_trace.y)
        min_idx = y_values.index(min(y_values))
        assert colors[min_idx] == "steelblue"
