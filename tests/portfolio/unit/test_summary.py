# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       22.06.2026
# Geändert:       22.06.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für portfolio.summary: Perzentil-Berechnung, compute_summary
#   (Items/abgeschlossen/Cycle-Time-Perzentile) und render_summary_html.
# =============================================================================

from __future__ import annotations

from datetime import datetime

from build_reports.loader import IssueRecord, ReportData
from portfolio.summary import (
    Summary,
    _percentile,
    compute_summary,
    render_summary_html,
)


def _issue(key: str, first_day: int | None, closed_day: int | None) -> IssueRecord:
    fd = datetime(2025, 1, first_day, 8) if first_day else None
    cd = datetime(2025, 1, closed_day, 8) if closed_day else None
    return IssueRecord(
        project="ART", key=key, issuetype="Feature", status="Done",
        created=fd, component="", first_date=fd, implementation_date=None,
        closed_date=cd, stage_minutes={}, resolution="Done")


class TestPercentile:
    def test_empty_is_none(self) -> None:
        assert _percentile([], 50) is None

    def test_single_value(self) -> None:
        assert _percentile([7.0], 95) == 7.0

    def test_median(self) -> None:
        assert _percentile([1.0, 2.0, 3.0], 50) == 2.0

    def test_interpolates(self) -> None:
        # 85th percentile of 1..10 (linear interpolation over rank 0..9)
        assert round(_percentile([float(i) for i in range(1, 11)], 85), 2) == 8.65


class TestComputeSummary:
    def test_counts_and_percentiles(self) -> None:
        # three closed issues with CT 4, 9, 14 days; one still open (no closed)
        data = ReportData(issues=[
            _issue("A-1", 1, 5),    # 4 days
            _issue("A-2", 1, 10),   # 9 days
            _issue("A-3", 1, 15),   # 14 days
            _issue("A-4", 2, None),  # open
        ])
        s = compute_summary(data, "Solution A")
        assert s.label == "Solution A"
        assert s.items == 4
        assert s.completed == 3
        assert s.median_ct == 9.0
        assert s.open_items == 1  # items − completed

    def test_target_ct_pct(self) -> None:
        # CTs 4, 9, 14 days; with target 10d, two of three are within → 66.7%
        data = ReportData(issues=[
            _issue("A-1", 1, 5), _issue("A-2", 1, 10), _issue("A-3", 1, 15)])
        s = compute_summary(data, "X", target_ct=10)
        assert round(s.target_ct_pct, 1) == 66.7

    def test_target_ct_pct_none_without_cycle_data(self) -> None:
        data = ReportData(issues=[_issue("A-1", 2, None)])  # open only
        assert compute_summary(data, "X").target_ct_pct is None

    def test_zero_cycle_time_excluded(self) -> None:
        # first == closed → CT 0 → excluded from percentiles but still completed
        data = ReportData(issues=[_issue("A-1", 5, 5)])
        s = compute_summary(data, "X")
        assert s.completed == 1
        assert s.median_ct is None

    def test_empty_data(self) -> None:
        s = compute_summary(ReportData(issues=[]), "Empty")
        assert s.items == 0 and s.completed == 0 and s.median_ct is None


class TestRenderSummaryHtml:
    def test_empty_returns_empty_string(self) -> None:
        assert render_summary_html([]) == ""

    def test_single_row(self) -> None:
        html = render_summary_html(
            [Summary("Solution A", 10, 7, 9.0, 20.0, 30.0, open_items=3,
                     target_ct_pct=80.0)],
            target_ct=90)
        assert "Management Summary" in html
        assert "Solution A" in html
        assert "<table" in html and "Items" in html
        assert "Open (WIP)" in html and "≤ 90d" in html
        assert "80%" in html  # target-CT share rendered as a percentage

    def test_multiple_rows(self) -> None:
        html = render_summary_html([
            Summary("ART A", 5, 3, 4.0, 6.0, 8.0),
            Summary("ART B", 8, 6, 5.0, 7.0, 9.0),
        ])
        assert html.count("<tr>") == 3  # header + two data rows

    def test_missing_percentiles_render_dash(self) -> None:
        html = render_summary_html([Summary("X", 0, 0, None, None, None)])
        assert "–" in html

    def test_label_is_escaped(self) -> None:
        html = render_summary_html([Summary("A & <B>", 1, 1, 1.0, 1.0, 1.0)])
        assert "A &amp; &lt;B&gt;" in html


class TestSummaryFigure:
    def test_builds_table_figure(self) -> None:
        from portfolio.summary import summary_figure
        fig = summary_figure([Summary("Sol A", 5, 3, 4.0, 6.0, 8.0)])
        assert fig.data[0].type == "table"
        # the label cell is present in the table's first column
        assert "Sol A" in list(fig.data[0].cells.values[0])
