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

from build_reports.loader import ReportData


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
