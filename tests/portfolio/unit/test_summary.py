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

from datetime import date, datetime

from build_reports.loader import IssueRecord, ReportData
from portfolio.summary import (
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    Summary,
    _outlier_cells,
    _percentile,
    assess_quality,
    compute_summary,
    quality_figure,
    render_quality_html,
    render_summary_html,
    summary_figure,
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


# ---------------------------------------------------------------------------
# A1: data quality / confidence flag per source
# ---------------------------------------------------------------------------

def _quality_data(n_with_first: int, n_without_first: int,
                  cfd_days: int = 0) -> ReportData:
    """Build ReportData with a given first-date coverage and optional CFD."""
    from datetime import date as _date
    from datetime import timedelta

    from build_reports.loader import CfdRecord
    issues = [_issue(f"Q-{i}", 1, 5) for i in range(n_with_first)]
    issues += [_issue(f"QN-{i}", None, None) for i in range(n_without_first)]
    cfd = [CfdRecord(day=_date(2025, 1, 1) + timedelta(days=i), stage_counts={})
           for i in range(cfd_days)]
    return ReportData(issues=issues, cfd=cfd, source_prefix="ART X")


class TestAssessQuality:
    REF = date(2025, 1, 10)

    def test_counts_and_percentages(self) -> None:
        q = assess_quality(_quality_data(8, 2, cfd_days=3), "ART X", reference=self.REF)
        assert q.records == 10
        assert q.pct_missing_first == 20.0
        assert q.pct_open == 20.0
        assert q.has_cfd is True

    def test_data_as_of_is_newest_record_date(self) -> None:
        q = assess_quality(_quality_data(3, 0, cfd_days=4), "ART X", reference=self.REF)
        # newest issue date: closed 05.01.; newest CFD day: 04.01. -> 05.01.
        assert q.data_as_of == date(2025, 1, 5)
        assert q.age_days == 5

    def test_empty_source_is_low(self) -> None:
        q = assess_quality(_quality_data(0, 0), "ART X", reference=self.REF)
        assert q.records == 0
        assert q.confidence == CONFIDENCE_LOW

    def test_majority_missing_first_is_low(self) -> None:
        q = assess_quality(_quality_data(4, 6, cfd_days=1), "ART X", reference=self.REF)
        assert q.confidence == CONFIDENCE_LOW

    def test_some_missing_first_is_medium(self) -> None:
        q = assess_quality(_quality_data(8, 2, cfd_days=1), "ART X", reference=self.REF)
        assert q.confidence == CONFIDENCE_MEDIUM

    def test_missing_cfd_is_medium(self) -> None:
        q = assess_quality(_quality_data(10, 0, cfd_days=0), "ART X", reference=self.REF)
        assert q.confidence == CONFIDENCE_MEDIUM

    def test_stale_data_is_medium(self) -> None:
        q = assess_quality(_quality_data(10, 0, cfd_days=1), "ART X",
                           reference=date(2025, 3, 1))
        assert q.confidence == CONFIDENCE_MEDIUM

    def test_fresh_complete_source_is_high(self) -> None:
        q = assess_quality(_quality_data(10, 0, cfd_days=1), "ART X", reference=self.REF)
        assert q.confidence == CONFIDENCE_HIGH


class TestRenderQualityHtml:
    def test_empty_returns_empty_string(self) -> None:
        assert render_quality_html([]) == ""

    def test_confidence_cell_is_colored_and_labelled(self) -> None:
        q = assess_quality(_quality_data(10, 0, cfd_days=1), "ART X",
                           reference=date(2025, 1, 10))
        html = render_quality_html([q])
        assert "Data Quality per Source" in html
        assert "ART X" in html
        assert ">high<" in html
        assert "#e6f4e6" in html  # green fill on the confidence cell

    def test_low_confidence_uses_red_fill(self) -> None:
        q = assess_quality(_quality_data(0, 0), "Empty ART",
                           reference=date(2025, 1, 10))
        html = render_quality_html([q])
        assert ">low<" in html
        assert "#f8d7da" in html

    def test_payload_label_is_escaped(self) -> None:
        data = _quality_data(1, 0, cfd_days=1)
        q = assess_quality(data, "<script>alert(1)</script>",
                           reference=date(2025, 1, 10))
        html = render_quality_html([q])
        assert "<script>" not in html
        assert "&lt;script&gt;" in html


class TestQualityFigure:
    def test_builds_table_with_confidence_fill(self) -> None:
        q_high = assess_quality(_quality_data(10, 0, cfd_days=1), "A",
                                reference=date(2025, 1, 10))
        q_low = assess_quality(_quality_data(0, 0), "B",
                               reference=date(2025, 1, 10))
        fig = quality_figure([q_high, q_low])
        assert fig.data[0].type == "table"
        conf_col = fig.data[0].cells.values[-1]
        assert list(conf_col) == ["high", "low"]


# ---------------------------------------------------------------------------
# A2: summary extension — E2E lead time, member share, coverage
# ---------------------------------------------------------------------------

def _issue_lt(key: str, created_day: int, first_day: int | None,
              closed_day: int | None) -> IssueRecord:
    """IssueRecord with distinct Created vs. First Date (for lead-time tests)."""
    return IssueRecord(
        project="ART", key=key, issuetype="Feature", status="Done",
        created=datetime(2025, 1, created_day, 8), component="",
        first_date=datetime(2025, 1, first_day, 8) if first_day else None,
        implementation_date=None,
        closed_date=datetime(2025, 1, closed_day, 8) if closed_day else None,
        stage_minutes={}, resolution="Done")


class TestLeadTime:
    def test_lead_time_uses_created_not_first(self) -> None:
        # Created 01., First 03., Closed 11.  ->  CT 8d, LT 10d
        data = ReportData(issues=[_issue_lt("L-1", 1, 3, 11)])
        s = compute_summary(data, "X")
        assert s.median_ct == 8.0
        assert s.median_lt == 10.0

    def test_lead_time_without_first_date_still_counts(self) -> None:
        # No First Date: excluded from CT, included in LT.
        data = ReportData(issues=[_issue_lt("L-1", 1, None, 6)])
        s = compute_summary(data, "X")
        assert s.median_ct is None
        assert s.median_lt == 5.0

    def test_lead_time_percentiles_in_table(self) -> None:
        data = ReportData(issues=[_issue_lt("L-1", 1, 2, 5), _issue_lt("L-2", 1, 2, 9)])
        html = render_summary_html([compute_summary(data, "X")])
        assert "Median LT (d)" in html
        assert "85th % LT (d)" in html

    def test_open_issue_has_no_lead_time(self) -> None:
        data = ReportData(issues=[_issue_lt("L-1", 1, 2, None)])
        s = compute_summary(data, "X")
        assert s.median_lt is None


class TestShareAndCoverage:
    REF = date(2025, 1, 10)

    def test_share_is_records_over_total(self) -> None:
        q_a = assess_quality(_quality_data(6, 0, cfd_days=1), "A", reference=self.REF)
        q_b = assess_quality(_quality_data(2, 0, cfd_days=1), "B", reference=self.REF)
        html = render_quality_html([q_a, q_b])
        assert "75%" in html   # A: 6 of 8
        assert "25%" in html   # B: 2 of 8

    def test_coverage_in_title_counts_delivering_sources(self) -> None:
        q_a = assess_quality(_quality_data(5, 0, cfd_days=1), "A", reference=self.REF)
        q_empty = assess_quality(_quality_data(0, 0), "B", reference=self.REF)
        html = render_quality_html([q_a, q_empty])
        assert "1/2 sources delivered data" in html

    def test_share_column_present_in_figure(self) -> None:
        q = assess_quality(_quality_data(4, 0, cfd_days=1), "A", reference=self.REF)
        fig = quality_figure([q])
        headers = list(fig.data[0].header.values)
        assert "Share" in headers
        assert "1/1 sources delivered data" in fig.layout.title.text


# ---------------------------------------------------------------------------
# A3: outlier highlighting in the comparison summary
# ---------------------------------------------------------------------------

def _summary_with_ct(label: str, median: float | None, p95: float | None) -> Summary:
    return Summary(label=label, items=10, completed=8, median_ct=median,
                   p85_ct=None, p95_ct=p95)


class TestOutlierHighlighting:
    def test_no_flags_below_minimum_rows(self) -> None:
        rows = [_summary_with_ct("A", 10, 20), _summary_with_ct("B", 100, 200)]
        assert _outlier_cells(rows) == set()

    def test_flags_median_and_p95_of_the_outlier(self) -> None:
        rows = [_summary_with_ct("A", 10, 20), _summary_with_ct("B", 12, 22),
                _summary_with_ct("C", 40, 90)]
        flagged = _outlier_cells(rows)
        assert (2, 4) in flagged   # C's median (40 > 1.5 x 12)
        assert (2, 6) in flagged   # C's p95    (90 > 1.5 x 22)
        assert not any(row != 2 for row, _ in flagged)

    def test_none_values_are_ignored(self) -> None:
        rows = [_summary_with_ct("A", None, None), _summary_with_ct("B", 10, 20),
                _summary_with_ct("C", 11, 21)]
        assert _outlier_cells(rows) == set()

    def test_html_marks_outlier_cell(self) -> None:
        rows = [_summary_with_ct("A", 10, 20), _summary_with_ct("B", 12, 22),
                _summary_with_ct("C", 40, 90)]
        html = render_summary_html(rows)
        assert html.count("#f8d7da") == 2  # exactly the two outlier cells

    def test_pooled_single_row_is_never_highlighted(self) -> None:
        html = render_summary_html([_summary_with_ct("Solution", 40, 90)])
        assert "#f8d7da" not in html

    def test_figure_fill_matrix_marks_outlier(self) -> None:
        rows = [_summary_with_ct("A", 10, 20), _summary_with_ct("B", 12, 22),
                _summary_with_ct("C", 40, 90)]
        fig = summary_figure(rows)
        fill = fig.data[0].cells.fill.color
        assert fill[4][2] == "#f8d7da"   # column Median CT, row C
        assert fill[6][2] == "#f8d7da"   # column 95th %, row C
        assert fill[4][0] == "white"
