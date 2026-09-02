# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       22.06.2026
# Geändert:       22.06.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Management-Summary für Solution-/Portfolio-Reports: eine kompakte Kennzahlen-
#   Tabelle (Items, abgeschlossen, Median / 85. / 95. Perzentil der Cycle Time)
#   je Übersichtseinheit. Im Pooled-Modus eine Zeile (Solution/Portfolio), im
#   Comparison-Modus eine Zeile je Einheit (ART bzw. Solution). Rein berechnend
#   und HTML-erzeugend — unabhängig von tkinter/plotly, daher gut testbar.
# =============================================================================

from __future__ import annotations

import html as _html
from dataclasses import dataclass
from datetime import date

from build_reports.loader import ReportData

#: Confidence levels for a data source (traffic-light semantics).
CONFIDENCE_HIGH = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW = "low"

#: Assessment thresholds (documented so the traffic light is explainable):
#: LOW    — no records at all, or more than half the issues lack a First Date
#:          (cycle-time statements would rest on a minority of the data).
#: MEDIUM — more than 10 % lack a First Date, or no CFD data was supplied,
#:          or the newest record is older than _STALE_DAYS days.
#: HIGH   — everything else.
_MISSING_FIRST_LOW = 50.0
_MISSING_FIRST_MEDIUM = 10.0
_STALE_DAYS = 30


@dataclass
class SourceQuality:
    """Data-quality figures for one source (a member ART or a comparison unit)."""
    label: str
    records: int                     # issues delivered by this source
    pct_missing_first: float         # share of issues without a First Date (0-100)
    pct_open: float                  # share without a Closed Date (= WIP share, informational)
    has_cfd: bool                    # source supplied CFD data
    data_as_of: date | None          # newest record date (created/first/closed)
    age_days: int | None             # age of data_as_of relative to the reference date

    @property
    def confidence(self) -> str:
        """Traffic-light confidence derived from the documented thresholds."""
        if self.records == 0 or self.pct_missing_first > _MISSING_FIRST_LOW:
            return CONFIDENCE_LOW
        if (self.pct_missing_first > _MISSING_FIRST_MEDIUM
                or not self.has_cfd
                or (self.age_days is not None and self.age_days > _STALE_DAYS)):
            return CONFIDENCE_MEDIUM
        return CONFIDENCE_HIGH


def assess_quality(
    data: ReportData, label: str, reference: date | None = None
) -> SourceQuality:
    """
    Assess the data quality of one source's ReportData.

    Pure and deterministic apart from the reference date, which defaults to
    today and exists as a parameter so tests can pin it.

    Args:
        data:      The source's (unfiltered) report data.
        label:     Display label for the source.
        reference: Date against which the data age is measured (default: today).

    Returns:
        A populated SourceQuality.
    """
    reference = reference or date.today()
    n = len(data.issues)
    missing_first = sum(1 for i in data.issues if not i.first_date)
    open_items = sum(1 for i in data.issues if not i.closed_date)

    newest: date | None = None
    for issue in data.issues:
        for dt in (issue.created, issue.first_date, issue.closed_date):
            if dt is not None:
                d = dt.date() if hasattr(dt, "date") else dt
                if newest is None or d > newest:
                    newest = d
    for rec in data.cfd:
        d = rec.day if isinstance(rec.day, date) else None
        if d is not None and (newest is None or d > newest):
            newest = d

    return SourceQuality(
        label=label,
        records=n,
        pct_missing_first=(missing_first / n * 100) if n else 100.0,
        pct_open=(open_items / n * 100) if n else 0.0,
        has_cfd=bool(data.cfd),
        data_as_of=newest,
        age_days=(reference - newest).days if newest else None,
    )


@dataclass
class Summary:
    """Key flow figures for one overview unit (a solution, portfolio, or ART)."""
    label: str
    items: int                  # total issues in the (filtered) data
    completed: int              # issues with a Closed Date
    median_ct: float | None     # cycle-time percentiles in days (CT = First→Closed, > 0)
    p85_ct: float | None
    p95_ct: float | None
    open_items: int = 0         # not-done issues (items − completed) = WIP
    target_ct_pct: float | None = None  # share of completed (with CT) within target_ct days


def _percentile(sorted_values: list[float], pct: float) -> float | None:
    """
    Linear-interpolation percentile of an already-sorted list.

    Args:
        sorted_values: Ascending list of values.
        pct:           Percentile in the range 0–100.

    Returns:
        The percentile value, or None if the list is empty.
    """
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (pct / 100.0) * (len(sorted_values) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(sorted_values) - 1)
    frac = rank - lo
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * frac


def compute_summary(data: ReportData, label: str, target_ct: int = 90) -> Summary:
    """
    Compute the management-summary figures for one ReportData.

    Cycle time uses method A (First Date → Closed Date in days) and counts only
    issues with both dates and a positive cycle time — matching the Flow Time
    metric's inclusion rule. ``target_ct_pct`` is the share of those completed
    issues whose cycle time is within ``target_ct`` days.

    Args:
        data:      The (already filtered) report data for one unit.
        label:     Display label for the unit.
        target_ct: Target cycle time in days for the Target-CT share.

    Returns:
        A populated Summary.
    """
    cycle: list[float] = []
    completed = 0
    for issue in data.issues:
        if issue.closed_date is not None:
            completed += 1
        if issue.first_date and issue.closed_date:
            days = (issue.closed_date - issue.first_date).total_seconds() / 86400
            if days > 0:
                cycle.append(days)
    cycle.sort()
    target_pct = (
        sum(1 for d in cycle if d <= target_ct) / len(cycle) * 100 if cycle else None
    )
    return Summary(
        label=label,
        items=len(data.issues),
        completed=completed,
        median_ct=_percentile(cycle, 50),
        p85_ct=_percentile(cycle, 85),
        p95_ct=_percentile(cycle, 95),
        open_items=len(data.issues) - completed,
        target_ct_pct=target_pct,
    )


def _fmt(value: float | None) -> str:
    """Format a percentile value to one decimal, or an en dash when missing."""
    return f"{value:.1f}" if value is not None else "–"


def _fmt_pct(value: float | None) -> str:
    """Format a percentage to a whole number with a % sign, or an en dash."""
    return f"{value:.0f}%" if value is not None else "–"


def _summary_headers(target_ct: int) -> list[str]:
    """Column headers for the summary table (shared by HTML and the PDF figure)."""
    return ["", "Items", "Completed", "Open (WIP)",
            "Median CT (d)", "85th % (d)", "95th % (d)", f"≤ {target_ct}d"]


def _summary_cells(s: Summary) -> list[str]:
    """Row values for one Summary, in the _summary_headers() order."""
    return [
        s.label,
        str(s.items),
        str(s.completed),
        str(s.open_items),
        _fmt(s.median_ct),
        _fmt(s.p85_ct),
        _fmt(s.p95_ct),
        _fmt_pct(s.target_ct_pct),
    ]


def render_summary_html(
    summaries: list[Summary], title: str = "Management Summary", target_ct: int = 90
) -> str:
    """
    Render the management summary as a self-contained HTML table block.

    Works for one row (pooled) or many rows (comparison). Returns an empty
    string when there is nothing to show.

    Args:
        summaries: One Summary per overview unit.
        title:     Heading shown above the table.
        target_ct: Target cycle time in days (only used for the column header).

    Returns:
        An HTML fragment (heading + styled table), or "" if summaries is empty.
    """
    if not summaries:
        return ""

    head_html = "".join(f"<th>{_html.escape(h)}</th>" for h in _summary_headers(target_ct))

    rows_html = ""
    for s in summaries:
        cells = [_html.escape(c) for c in _summary_cells(s)]
        rows_html += "<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"

    style = (
        "<style>"
        "table.sr-summary{border-collapse:collapse;margin:8px 0 24px 0;font-size:0.95rem;}"
        "table.sr-summary th,table.sr-summary td{"
        "border:1px solid #d0d0d0;padding:4px 12px;text-align:right;}"
        "table.sr-summary th:first-child,table.sr-summary td:first-child{text-align:left;}"
        "table.sr-summary th{background:#f2f2f2;}"
        "</style>"
    )
    return (
        f"{style}"
        f"<h2 class='metric-heading'>{_html.escape(title)}</h2>"
        f"<table class='sr-summary'><tr>{head_html}</tr>{rows_html}</table>"
    )


#: Cell background per confidence level (traffic light).
_CONF_COLORS = {
    CONFIDENCE_HIGH: "#e6f4e6",
    CONFIDENCE_MEDIUM: "#fff3cd",
    CONFIDENCE_LOW: "#f8d7da",
}


def _quality_headers() -> list[str]:
    """Column headers for the data-quality table (shared by HTML and PDF)."""
    return ["Source", "Records", "No First Date", "Open share", "CFD",
            "Data as of", "Confidence"]


def _quality_cells(q: SourceQuality) -> list[str]:
    """Row values for one SourceQuality, in the _quality_headers() order."""
    as_of = (f"{q.data_as_of.strftime('%d.%m.%Y')} ({q.age_days}d)"
             if q.data_as_of else "–")
    return [
        q.label,
        str(q.records),
        _fmt_pct(q.pct_missing_first),
        _fmt_pct(q.pct_open),
        "yes" if q.has_cfd else "no",
        as_of,
        q.confidence,
    ]


def render_quality_html(
    qualities: list[SourceQuality], title: str = "Data Quality per Source"
) -> str:
    """
    Render the per-source data-quality table as an HTML fragment.

    The Confidence cell is colored per level (green/yellow/red) so the weakest
    source is visible at a glance. Returns "" when there is nothing to show.

    Args:
        qualities: One SourceQuality per source.
        title:     Heading shown above the table.

    Returns:
        An HTML fragment (heading + styled table), or "" if qualities is empty.
    """
    if not qualities:
        return ""

    head_html = "".join(f"<th>{_html.escape(h)}</th>" for h in _quality_headers())
    rows_html = ""
    for q in qualities:
        cells = [_html.escape(c) for c in _quality_cells(q)]
        color = _CONF_COLORS.get(q.confidence, "#ffffff")
        body = "".join(f"<td>{c}</td>" for c in cells[:-1])
        rows_html += (f"<tr>{body}"
                      f"<td style='background:{color};font-weight:600'>{cells[-1]}</td></tr>")

    return (
        f"<h2 class='metric-heading'>{_html.escape(title)}</h2>"
        f"<table class='sr-summary'><tr>{head_html}</tr>{rows_html}</table>"
    )


def quality_figure(
    qualities: list[SourceQuality], title: str = "Data Quality per Source"
):
    """
    Render the data-quality table as a plotly Table figure (for the PDF export).

    Mirrors render_quality_html(); the Confidence column carries the traffic-light
    fill per row.

    Args:
        qualities: One SourceQuality per source.
        title:     Figure title.

    Returns:
        A plotly Figure containing a single Table trace.
    """
    import plotly.graph_objects as go

    headers = _quality_headers()
    rows = [_quality_cells(q) for q in qualities]
    columns = [[row[c] for row in rows] for c in range(len(headers))]
    conf_fill = [_CONF_COLORS.get(q.confidence, "#ffffff") for q in qualities]
    fill_colors = [["white"] * len(rows)] * (len(headers) - 1) + [conf_fill]
    fig = go.Figure(go.Table(
        header=dict(values=headers, fill_color="#f2f2f2", align="left"),
        cells=dict(values=columns, align="left", fill_color=fill_colors),
    ))
    fig.update_layout(title=title, title_font_size=14, margin=dict(t=40, b=10))
    return fig


def summary_figure(
    summaries: list[Summary], title: str = "Management Summary", target_ct: int = 90
):
    """
    Render the management summary as a plotly Table figure (for the PDF export).

    Mirrors render_summary_html() but produces a figure so it can be a PDF page.

    Args:
        summaries: One Summary per overview unit.
        title:     Figure title.
        target_ct: Target cycle time in days (column header only).

    Returns:
        A plotly Figure containing a single Table trace.
    """
    import plotly.graph_objects as go

    headers = _summary_headers(target_ct)
    rows = [_summary_cells(s) for s in summaries]
    columns = [[row[c] for row in rows] for c in range(len(headers))]
    fig = go.Figure(go.Table(
        header=dict(values=headers, fill_color="#f2f2f2", align="left"),
        cells=dict(values=columns, align="left"),
    ))
    fig.update_layout(title=title, title_font_size=14, margin=dict(t=40, b=10))
    return fig
