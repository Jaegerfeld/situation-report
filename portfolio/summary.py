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


def compute_summary(data: ReportData, label: str) -> Summary:
    """
    Compute the management-summary figures for one ReportData.

    Cycle time uses method A (First Date → Closed Date in days) and counts only
    issues with both dates and a positive cycle time — matching the Flow Time
    metric's inclusion rule.

    Args:
        data:  The (already filtered) report data for one unit.
        label: Display label for the unit.

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
    return Summary(
        label=label,
        items=len(data.issues),
        completed=completed,
        median_ct=_percentile(cycle, 50),
        p85_ct=_percentile(cycle, 85),
        p95_ct=_percentile(cycle, 95),
    )


def _fmt(value: float | None) -> str:
    """Format a percentile value to one decimal, or an en dash when missing."""
    return f"{value:.1f}" if value is not None else "–"


def render_summary_html(summaries: list[Summary], title: str = "Management Summary") -> str:
    """
    Render the management summary as a self-contained HTML table block.

    Works for one row (pooled) or many rows (comparison). Returns an empty
    string when there is nothing to show.

    Args:
        summaries: One Summary per overview unit.
        title:     Heading shown above the table.

    Returns:
        An HTML fragment (heading + styled table), or "" if summaries is empty.
    """
    if not summaries:
        return ""

    headers = ["", "Items", "Completed", "Median CT (d)", "85th % (d)", "95th % (d)"]
    head_html = "".join(f"<th>{_html.escape(h)}</th>" for h in headers)

    rows_html = ""
    for s in summaries:
        cells = [
            _html.escape(s.label),
            str(s.items),
            str(s.completed),
            _fmt(s.median_ct),
            _fmt(s.p85_ct),
            _fmt(s.p95_ct),
        ]
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
