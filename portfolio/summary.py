# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       22.06.2026
# Geändert:       19.09.2026
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
from portfolio.capability_config import (
    HEALTH_ORDER,
    Capability,
)
from portfolio.decision_config import (
    ASSUMPTION_OPEN,
    KIND_ASSUMPTION,
    KIND_DECISION,
    LogEntry,
)
from portfolio.dependency_config import (
    DEP_BLOCKED,
    DEP_DONE,
    DEP_STATUS_ORDER,
    Dependency,
)
from portfolio.dora_config import (
    DORA_TIER_FUNCS,
    TIER_ORDER,
    TIER_UNKNOWN,
    unit_tier,
)
from portfolio.flow_problems_config import (
    FLOW_OPEN,
    FLOW_STATUS_ORDER,
    SURVIVED_CONFERENCES_THRESHOLD,
    FlowProblem,
)
from portfolio.nfr_config import (
    NFR_STATUS_ORDER,
    RUNWAY_IN_PLACE,
    RUNWAY_STATUS_ORDER,
    Nfr,
    RunwayItem,
)
from portfolio.report_texts import DEFAULT_LANG, t
from portfolio.risks_config import (
    IMPACT_HIGH,
    IMPACT_LOW,
    IMPACT_ORDER,
    ROAM_ORDER,
    ROAM_OWNED,
    Risk,
)
from portfolio.slo_config import (
    SLO_STATUS_ORDER,
    error_budget_remaining_pct,
    slo_status,
)
from portfolio.themes_config import (
    HORIZONS,
    Epic,
    StrategicTheme,
)
from sources.base import DoraRecord, QualityRecord, SloRecord

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
    median_lt: float | None = None      # E2E lead time Created→Closed in days (A2)
    p85_lt: float | None = None


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
    lead: list[float] = []
    completed = 0
    for issue in data.issues:
        if issue.closed_date is not None:
            completed += 1
        if issue.first_date and issue.closed_date:
            days = (issue.closed_date - issue.first_date).total_seconds() / 86400
            if days > 0:
                cycle.append(days)
        if issue.created and issue.closed_date:
            days = (issue.closed_date - issue.created).total_seconds() / 86400
            if days > 0:
                lead.append(days)
    cycle.sort()
    lead.sort()
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
        median_lt=_percentile(lead, 50),
        p85_lt=_percentile(lead, 85),
    )


def _fmt(value: float | None) -> str:
    """Format a percentile value to one decimal, or an en dash when missing."""
    return f"{value:.1f}" if value is not None else "–"


def _fmt_pct(value: float | None) -> str:
    """Format a percentage to a whole number with a % sign, or an en dash."""
    return f"{value:.0f}%" if value is not None else "–"


#: Katalogschlüssel je Statuswert. Die Farbtabellen weiter unten sagen, *wie*
#: ein Status aussieht; diese Tabellen, *wie er heißt* — in der gewählten
#: Sprache. Beide haben dieselben Schlüssel; ein Test hält sie deckungsgleich,
#: damit ein neuer Status nicht in der einen Tabelle steht und in der anderen
#: fehlt.
_CONF_TEXT_KEYS = {
    CONFIDENCE_HIGH: "conf.high",
    CONFIDENCE_MEDIUM: "conf.medium",
    CONFIDENCE_LOW: "conf.low",
}
_ROAM_TEXT_KEYS = {
    "resolved": "roam.resolved",
    "owned": "roam.owned",
    "accepted": "roam.accepted",
    "mitigated": "roam.mitigated",
}
_IMPACT_TEXT_KEYS = {
    IMPACT_HIGH: "impact.high",
    "medium": "impact.medium",
    IMPACT_LOW: "impact.low",
}
_NFR_TEXT_KEYS = {
    "met": "status.met",
    "at_risk": "status.at_risk",
    "violated": "status.violated",
}
_RUNWAY_TEXT_KEYS = {
    "in_place": "status.in_place",
    "building": "status.building",
    "gap": "status.gap",
}
_HEALTH_TEXT_KEYS = {
    "healthy": "health.healthy",
    "at_risk": "health.at_risk",
    "critical": "health.critical",
}
_DEP_TEXT_KEYS = {
    "blocked": "dep.blocked",
    "at_risk": "status.at_risk",
    "on_track": "dep.on_track",
    "done": "dep.done",
}
_LOG_TEXT_KEYS = {
    "proposed": "log.proposed",
    "accepted": "log.accepted",
    "superseded": "log.superseded",
    "open": "log.open",
    "confirmed": "log.confirmed",
    "invalidated": "log.invalidated",
}
_KIND_TEXT_KEYS = {
    KIND_DECISION: "kind.decision",
    KIND_ASSUMPTION: "kind.assumption",
}
_SLO_TEXT_KEYS = {
    "breached": "slo.breached",
    "at_risk": "status.at_risk",
    "met": "status.met",
    "unknown": "slo.unknown",
}
_TIER_TEXT_KEYS = {
    "elite": "tier.elite",
    "high": "tier.high",
    "medium": "tier.medium",
    "low": "tier.low",
    TIER_UNKNOWN: "tier.unknown",
}
_FLOW_TEXT_KEYS = {
    "open": "log.open",
    "committed": "flow.committed",
    "resolved": "roam.resolved",
    "dropped": "flow.dropped",
}


# =============================================================================
# Colour legend
#
# Every coloured cell in every report draws from the same five backgrounds.
# The legend is *derived* from the colour dictionaries below rather than
# written out by hand: when a status is added or recoloured, the legend
# follows automatically and cannot drift out of step with the table.
# =============================================================================

#: The shared palette: colour plus the catalogue key of its meaning.
#: Order = the order the overall key is shown in.
LEGEND_PALETTE: tuple[tuple[str, str], ...] = (
    ("#e6f4e6", "legend.green"),
    ("#d1ecf1", "legend.blue"),
    ("#fff3cd", "legend.yellow"),
    ("#f8d7da", "legend.red"),
    ("#e2e3e5", "legend.grey"),
)


def _legend_label(key: str) -> str:
    """Display text for a status key ('at_risk' -> 'at risk')."""
    return key.replace("_", " ")


def _swatch(color: str, text: str) -> str:
    """A single legend item: colour chip plus its plain-text meaning."""
    return (f"<span class='sr-legend-item'>"
            f"<span class='sr-legend-chip' style='background:{color}'></span>"
            f"{_html.escape(text)}</span>")


def _legend_group(caption: str, colors: dict[str, str],
                  text_keys: dict[str, str] | None = None,
                  lang: str = DEFAULT_LANG) -> str:
    """
    One legend group for a coloured column, e.g. "Status: ■ open ■ blocked".

    Statuses that share a colour are folded into one chip ("open / proposed"),
    because the reader cannot tell them apart by colour anyway. The words come
    from the catalogue via ``text_keys``; without an entry the raw status name
    is shown, which is a visible reminder that a key is missing.
    """
    by_color: dict[str, list[str]] = {}
    for key, color in colors.items():
        catalogue_key = (text_keys or {}).get(key)
        label = t(catalogue_key, lang) if catalogue_key else _legend_label(key)
        by_color.setdefault(color, []).append(label)
    items = "".join(_swatch(c, " / ".join(ls)) for c, ls in by_color.items())
    return f"<span class='sr-legend-group'><b>{_html.escape(caption)}:</b> {items}</span>"


def _legend_flag(caption: str, color: str, text: str) -> str:
    """
    One legend group for a single-purpose flag colour (overdue, aging, ...).

    Callers pass these only when the flag actually occurs on the page. A status
    scale is different: it describes the column and is shown in full, because
    knowing that "blocked" exists is part of reading an all-green table.
    """
    return (f"<span class='sr-legend-group'><b>{_html.escape(caption)}:</b> "
            f"{_swatch(color, text)}</span>")


#: Shared styling for both the per-table legend lines and the overall key.
LEGEND_STYLE = (
    "<style>"
    "p.sr-legend{font-size:0.82rem;color:#555;margin:-16px 0 20px 0;"
    "line-height:1.9;}"
    "span.sr-legend-group{margin-right:18px;white-space:nowrap;}"
    "span.sr-legend-item{margin-right:10px;white-space:nowrap;}"
    "span.sr-legend-chip{display:inline-block;width:11px;height:11px;"
    "border:1px solid #b0b0b0;margin-right:4px;vertical-align:-1px;}"
    "div.sr-legend-key{border:1px solid #d0d0d0;background:#fbfbfb;"
    "padding:10px 14px;margin:12px 0 22px 0;font-size:0.85rem;color:#444;}"
    "div.sr-legend-key b.sr-legend-title{display:block;margin-bottom:6px;"
    "color:#2b5b84;}"
    "</style>"
)


def _legend_line(*groups: str) -> str:
    """Assemble the legend line placed underneath a coloured table."""
    filled = [g for g in groups if g]
    if not filled:
        return ""
    return LEGEND_STYLE + "<p class='sr-legend'>" + "".join(filled) + "</p>"


def render_legend_key_html(lang: str = DEFAULT_LANG,
                           title: str | None = None) -> str:
    """
    Render the overall colour key shown once at the top of a report.

    The five backgrounds carry the same meaning in every table; the individual
    statuses behind them are named in the legend line under each table, because
    the same colour stands for different words depending on the register (grey
    is "done" for a dependency and "accepted" for a ROAM risk).
    """
    title = title or t("legend.key.title", lang)
    items = "".join(_swatch(color, t(key, lang))
                    for color, key in LEGEND_PALETTE)
    return (f"{LEGEND_STYLE}<div class='sr-legend-key'>"
            f"<b class='sr-legend-title'>{_html.escape(title)}</b>{items}"
            f"<div style='margin-top:6px;font-size:0.8rem;color:#666'>"
            f"{_html.escape(t('legend.key.note', lang))}"
            f"</div></div>")


def _summary_headers(target_ct: int, lang: str = DEFAULT_LANG) -> list[str]:
    """Column headers for the summary table (shared by HTML and the PDF figure)."""
    return ["", t("summary.items", lang), t("summary.completed", lang),
            t("summary.open_wip", lang), t("summary.median_ct", lang),
            t("summary.p85_ct", lang), t("summary.p95_ct", lang),
            t("summary.target_ct", lang, days=target_ct),
            t("summary.median_lt", lang), t("summary.p85_lt", lang)]


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
        _fmt(s.median_lt),
        _fmt(s.p85_lt),
    ]


def render_summary_html(
    summaries: list[Summary], title: str | None = None, target_ct: int = 90,
    lang: str = DEFAULT_LANG,
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

    title = title or t("summary.heading", lang)
    head_html = "".join(f"<th>{_html.escape(h)}</th>"
                        for h in _summary_headers(target_ct, lang))

    outliers = _outlier_cells(summaries)
    rows_html = ""
    for row, s in enumerate(summaries):
        cells = [_html.escape(c) for c in _summary_cells(s)]
        tds = "".join(
            (f"<td style='background:{_OUTLIER_COLOR};font-weight:600'>{c}</td>"
             if (row, col) in outliers else f"<td>{c}</td>")
            for col, c in enumerate(cells))
        rows_html += f"<tr>{tds}</tr>"

    style = (
        "<style>"
        "table.sr-summary{border-collapse:collapse;margin:8px 0 24px 0;font-size:0.95rem;}"
        "table.sr-summary th,table.sr-summary td{"
        "border:1px solid #d0d0d0;padding:4px 12px;text-align:right;}"
        "table.sr-summary th:first-child,table.sr-summary td:first-child{text-align:left;}"
        "table.sr-summary th{background:#f2f2f2;}"
        "</style>"
    )
    # The legend only earns its place when something is actually shaded.
    legend = _legend_line(_legend_flag(
        t("legend.outlier", lang), _OUTLIER_COLOR,
        t("legend.outlier.text", lang, factor=f"{_OUTLIER_FACTOR:g}"))
    ) if outliers else ""

    return (
        f"{style}"
        f"<h2 class='metric-heading'>{_html.escape(title)}</h2>"
        f"<table class='sr-summary'><tr>{head_html}</tr>{rows_html}</table>"
        f"{legend}"
    )


#: Outlier highlighting (comparison mode): a Median-CT or 95th-percentile cell
#: is flagged when its value exceeds _OUTLIER_FACTOR x the median of that column
#: across all rows. Requires at least _OUTLIER_MIN_ROWS rows — with fewer there
#: is no group to be an outlier of.
_OUTLIER_FACTOR = 1.5
_OUTLIER_MIN_ROWS = 3
_OUTLIER_COLOR = "#f8d7da"


def _outlier_cells(summaries: list[Summary]) -> set[tuple[int, int]]:
    """
    Identify outlier cells for the comparison summary.

    Checked columns: Median CT (index 4) and 95th percentile (index 6) in the
    _summary_cells() order. Returns a set of (row_index, column_index) pairs.
    """
    if len(summaries) < _OUTLIER_MIN_ROWS:
        return set()
    flagged: set[tuple[int, int]] = set()
    for col, attr in ((4, "median_ct"), (6, "p95_ct")):
        values = [getattr(s, attr) for s in summaries]
        present = sorted(v for v in values if v is not None)
        if not present:
            continue
        threshold = _OUTLIER_FACTOR * (_percentile(present, 50) or 0)
        if threshold <= 0:
            continue
        for row, value in enumerate(values):
            if value is not None and value > threshold:
                flagged.add((row, col))
    return flagged


#: Cell background per confidence level (traffic light).
_CONF_COLORS = {
    CONFIDENCE_HIGH: "#e6f4e6",
    CONFIDENCE_MEDIUM: "#fff3cd",
    CONFIDENCE_LOW: "#f8d7da",
}


def _quality_headers(lang: str = DEFAULT_LANG) -> list[str]:
    """Column headers for the data-quality table (shared by HTML and PDF)."""
    return [t("quality.col.source", lang), t("quality.col.records", lang),
            t("quality.col.share", lang), t("quality.col.no_first", lang),
            t("quality.col.open_share", lang), t("quality.col.cfd", lang),
            t("quality.col.as_of", lang), t("quality.col.confidence", lang)]


def _quality_cells(q: SourceQuality, total_records: int,
                   lang: str = DEFAULT_LANG) -> list[str]:
    """Row values for one SourceQuality, in the _quality_headers(lang) order.

    Args:
        q:             The quality record to format.
        total_records: Sum of records across all sources (for the member share).
    """
    as_of = (t("quality.age", lang,
               date=q.data_as_of.strftime(t("fmt.date", lang)),
               days=q.age_days)
             if q.data_as_of else "–")
    share = (q.records / total_records * 100) if total_records else None
    return [
        q.label,
        str(q.records),
        _fmt_pct(share),
        _fmt_pct(q.pct_missing_first),
        _fmt_pct(q.pct_open),
        t("cell.yes", lang) if q.has_cfd else t("cell.no", lang),
        as_of,
        t(_CONF_TEXT_KEYS[q.confidence], lang),
    ]


def _coverage_title(qualities: list[SourceQuality], title: str,
                    lang: str = DEFAULT_LANG) -> str:
    """Append the coverage ratio (sources that delivered data) to the title."""
    delivered = sum(1 for q in qualities if q.records > 0)
    return t("quality.coverage", lang, title=title, delivered=delivered,
             total=len(qualities))


def render_quality_html(
    qualities: list[SourceQuality], title: str | None = None,
    lang: str = DEFAULT_LANG,
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

    total_records = sum(q.records for q in qualities)
    title = _coverage_title(qualities, title or t("quality.heading", lang), lang)
    head_html = "".join(f"<th>{_html.escape(h)}</th>"
                        for h in _quality_headers(lang))
    rows_html = ""
    for q in qualities:
        cells = [_html.escape(c)
                 for c in _quality_cells(q, total_records, lang)]
        color = _CONF_COLORS.get(q.confidence, "#ffffff")
        body = "".join(f"<td>{c}</td>" for c in cells[:-1])
        rows_html += (f"<tr>{body}"
                      f"<td style='background:{color};font-weight:600'>{cells[-1]}</td></tr>")

    legend = _legend_line(_legend_group(
        t("quality.col.confidence", lang), _CONF_COLORS, _CONF_TEXT_KEYS, lang))

    return (
        f"<h2 class='metric-heading'>{_html.escape(title)}</h2>"
        f"<table class='sr-summary'><tr>{head_html}</tr>{rows_html}</table>"
        f"{legend}"
    )


def quality_figure(
    qualities: list[SourceQuality], title: str | None = None,
    lang: str = DEFAULT_LANG,
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

    headers = _quality_headers(lang)
    total_records = sum(q.records for q in qualities)
    title = _coverage_title(qualities, title or t("quality.heading", lang), lang)
    rows = [_quality_cells(q, total_records, lang) for q in qualities]
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
    summaries: list[Summary], title: str | None = None,
    target_ct: int = 90, lang: str = DEFAULT_LANG,
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

    headers = _summary_headers(target_ct, lang)
    rows = [_summary_cells(s) for s in summaries]
    columns = [[row[c] for row in rows] for c in range(len(headers))]
    outliers = _outlier_cells(summaries)
    fill = [["white" if (r, c) not in outliers else _OUTLIER_COLOR
             for r in range(len(rows))] for c in range(len(headers))]
    fig = go.Figure(go.Table(
        header=dict(values=headers, fill_color="#f2f2f2", align="left"),
        cells=dict(values=columns, align="left", fill_color=fill),
    ))
    fig.update_layout(title=title, title_font_size=14, margin=dict(t=40, b=10))
    return fig


# ---------------------------------------------------------------------------
# ROAM risk board (B3)
# ---------------------------------------------------------------------------

#: Cell background per ROAM category (board colours).
_ROAM_COLORS = {
    "resolved": "#e6f4e6",
    "owned": "#fff3cd",
    "accepted": "#e2e3e5",
    "mitigated": "#d1ecf1",
}

#: Cell background per impact level (mirrors the confidence traffic light).
_IMPACT_COLORS = {
    IMPACT_HIGH: "#f8d7da",
    "medium": "#fff3cd",
    IMPACT_LOW: "#e6f4e6",
}

#: An *owned* risk older than this many days is flagged as aging — ownership
#: without visible movement is exactly what the board exists to surface.
#: Resolved/accepted/mitigated risks do not age (their state is a decision).
_RISK_AGING_DAYS = 30
_AGING_COLOR = "#f8d7da"


def _risk_age_days(risk: Risk, reference: date | None = None) -> int | None:
    """Days since the risk entered its current ROAM category (None = unknown)."""
    if risk.status_since is None:
        return None
    return ((reference or date.today()) - risk.status_since).days


def _risk_is_aging(risk: Risk, reference: date | None = None) -> bool:
    """True when an owned risk has sat in 'owned' longer than _RISK_AGING_DAYS."""
    age = _risk_age_days(risk, reference)
    return risk.roam == ROAM_OWNED and age is not None and age > _RISK_AGING_DAYS


def _sorted_roam(entries: list[tuple[str, Risk]]) -> list[tuple[str, Risk]]:
    """Board order: ROAM category, then impact (high first), then source."""
    return sorted(entries, key=lambda e: (
        ROAM_ORDER.index(e[1].roam), IMPACT_ORDER.index(e[1].impact), e[0]))


def _roam_headers(include_source: bool, lang: str = DEFAULT_LANG) -> list[str]:
    """Column headers for the ROAM board (shared by HTML and PDF)."""
    head = [t("roam.col.roam", lang), t("roam.col.risk", lang),
            t("roam.col.impact", lang), t("col.owner", lang), t("col.since", lang)]
    return ([t("col.solution", lang)] + head) if include_source else head


def _roam_cells(
    source: str, risk: Risk, include_source: bool, reference: date | None = None,
    lang: str = DEFAULT_LANG,
) -> list[str]:
    """Row values for one risk, in the _roam_headers() order."""
    age = _risk_age_days(risk, reference)
    since = (t("quality.age", lang,
               date=risk.status_since.strftime(t("fmt.date", lang)), days=age)
             if risk.status_since else "–")
    row = [t(_ROAM_TEXT_KEYS[risk.roam], lang).capitalize(),
           f"{risk.risk_id}: {risk.title}",
           t(_IMPACT_TEXT_KEYS[risk.impact], lang), risk.owner or "–", since]
    return ([source] + row) if include_source else row


def _roam_title(
    entries: list[tuple[str, Risk]], title: str, reference: date | None = None,
    lang: str = DEFAULT_LANG,
) -> str:
    """Append risk counts (total, owned, aging) to the board title."""
    owned = sum(1 for _, r in entries if r.roam == ROAM_OWNED)
    aging = sum(1 for _, r in entries if _risk_is_aging(r, reference))
    out = t("roam.title", lang, title=title, total=len(entries), owned=owned)
    if aging:
        out += t("roam.title.aging", lang, aging=aging, days=_RISK_AGING_DAYS)
    return out


def _roam_include_source(entries: list[tuple[str, Risk]]) -> bool:
    """Show the Solution column only when risks come from several sources."""
    return len({source for source, _ in entries}) > 1


def render_roam_html(
    entries: list[tuple[str, Risk]],
    title: str | None = None,
    lang: str = DEFAULT_LANG,
    reference: date | None = None,
) -> str:
    """
    Render the ROAM risk board as an HTML fragment.

    Rows are grouped in R-O-A-M order with coloured category and impact cells;
    the Since cell of an aging owned risk is highlighted. A Solution column is
    prepended when the entries stem from more than one source (portfolio mode).

    Args:
        entries:   (source label, Risk) pairs, unordered.
        title:     Heading shown above the board.
        reference: Age reference date (default: today) — injectable for tests.

    Returns:
        An HTML fragment (heading + styled table), or "" if entries is empty.
    """
    if not entries:
        return ""

    include_source = _roam_include_source(entries)
    ordered = _sorted_roam(entries)
    title = _roam_title(entries, title or t("roam.heading", lang), reference, lang)
    aging_seen = False
    head_html = "".join(
        f"<th>{_html.escape(h)}</th>" for h in _roam_headers(include_source, lang))

    offset = 1 if include_source else 0
    rows_html = ""
    for source, risk in ordered:
        cells = [_html.escape(c)
                 for c in _roam_cells(source, risk, include_source, reference, lang)]
        tds = []
        for col, c in enumerate(cells):
            if col == offset:  # ROAM category
                color = _ROAM_COLORS.get(risk.roam, "#ffffff")
                tds.append(f"<td style='background:{color};font-weight:600'>{c}</td>")
            elif col == offset + 2:  # impact
                color = _IMPACT_COLORS.get(risk.impact, "#ffffff")
                tds.append(f"<td style='background:{color}'>{c}</td>")
            elif col == offset + 4 and _risk_is_aging(risk, reference):  # since
                aging_seen = True
                tds.append(f"<td style='background:{_AGING_COLOR};font-weight:600'>{c}</td>")
            else:
                tds.append(f"<td>{c}</td>")
        rows_html += f"<tr>{''.join(tds)}</tr>"

    legend = _legend_line(
        _legend_group(t("roam.col.roam", lang), _ROAM_COLORS,
                      _ROAM_TEXT_KEYS, lang),
        _legend_group(t("roam.col.impact", lang), _IMPACT_COLORS,
                      _IMPACT_TEXT_KEYS, lang),
        _legend_flag(t("col.since", lang), _AGING_COLOR, t("legend.aging", lang))
        if aging_seen else "",
    )

    return (
        f"<h2 class='metric-heading'>{_html.escape(title)}</h2>"
        f"<table class='sr-summary'><tr>{head_html}</tr>{rows_html}</table>"
        f"{legend}"
    )


def roam_figure(
    entries: list[tuple[str, Risk]],
    title: str | None = None,
    lang: str = DEFAULT_LANG,
    reference: date | None = None,
):
    """
    Render the ROAM risk board as a plotly Table figure (for the PDF export).

    Mirrors render_roam_html(): coloured ROAM and impact columns, aging
    highlight in the Since column.

    Args:
        entries:   (source label, Risk) pairs, unordered.
        title:     Figure title.
        reference: Age reference date (default: today).

    Returns:
        A plotly Figure containing a single Table trace.
    """
    import plotly.graph_objects as go

    include_source = _roam_include_source(entries)
    ordered = _sorted_roam(entries)
    headers = _roam_headers(include_source, lang)
    title = _roam_title(entries, title or t("roam.heading", lang), reference, lang)
    rows = [_roam_cells(source, risk, include_source, reference, lang)
            for source, risk in ordered]
    columns = [[row[c] for row in rows] for c in range(len(headers))]

    offset = 1 if include_source else 0
    white = ["white"] * len(rows)
    fill_colors: list[list[str]] = [list(white) for _ in headers]
    fill_colors[offset] = [_ROAM_COLORS.get(r.roam, "#ffffff") for _, r in ordered]
    fill_colors[offset + 2] = [_IMPACT_COLORS.get(r.impact, "#ffffff")
                               for _, r in ordered]
    fill_colors[offset + 4] = [_AGING_COLOR if _risk_is_aging(r, reference) else "white"
                               for _, r in ordered]
    fig = go.Figure(go.Table(
        header=dict(values=headers, fill_color="#f2f2f2", align="left"),
        cells=dict(values=columns, align="left", fill_color=fill_colors),
    ))
    fig.update_layout(title=title, title_font_size=14, margin=dict(t=40, b=10))
    return fig


# ---------------------------------------------------------------------------
# NFR / architecture-runway dashboard (B2)
# ---------------------------------------------------------------------------

#: Cell background per NFR status (traffic light).
_NFR_STATUS_COLORS = {
    "met": "#e6f4e6",
    "at_risk": "#fff3cd",
    "violated": "#f8d7da",
}

#: Cell background per runway status.
_RUNWAY_COLORS = {
    "in_place": "#e6f4e6",
    "building": "#fff3cd",
    "gap": "#f8d7da",
}

#: A runway element whose needed_by lies in the past while it is not in place
#: renders as overdue (red date cell) — the runway detonates on a date.
_OVERDUE_COLOR = "#f8d7da"

#: Human-readable status labels (the JSON keys stay machine-friendly).
_STATUS_LABELS = {
    "met": "met",
    "at_risk": "at risk",
    "violated": "violated",
    "in_place": "in place",
    "building": "building",
    "gap": "gap",
}


def _runway_is_overdue(item: RunwayItem, reference: date | None = None) -> bool:
    """True when needed_by has passed and the element is not in place."""
    return (item.needed_by is not None
            and item.status != RUNWAY_IN_PLACE
            and item.needed_by < (reference or date.today()))


def _sorted_nfrs(entries: list[tuple[str, Nfr]]) -> list[tuple[str, Nfr]]:
    """Dashboard order: violated first, then at risk, then met; then source."""
    return sorted(entries, key=lambda e: (
        NFR_STATUS_ORDER.index(e[1].status), e[0], e[1].nfr_id))


def _sorted_runway(
    entries: list[tuple[str, RunwayItem]]
) -> list[tuple[str, RunwayItem]]:
    """Dashboard order: gaps first, then building, then in place; then source."""
    return sorted(entries, key=lambda e: (
        RUNWAY_STATUS_ORDER.index(e[1].status), e[0], e[1].item_id))


def _nfr_headers(include_source: bool, lang: str = DEFAULT_LANG) -> list[str]:
    """Column headers for the NFR table (shared by HTML and PDF)."""
    head = [t("nfr.col.nfr", lang), t("nfr.col.target", lang),
            t("nfr.col.actual", lang), t("col.status", lang), t("col.owner", lang)]
    return ([t("col.solution", lang)] + head) if include_source else head


def _nfr_cells(source: str, nfr: Nfr, include_source: bool,
               lang: str = DEFAULT_LANG) -> list[str]:
    """Row values for one NFR, in the _nfr_headers() order."""
    row = [f"{nfr.nfr_id}: {nfr.title}", nfr.target, nfr.actual or "–",
           t(_NFR_TEXT_KEYS[nfr.status], lang), nfr.owner or "–"]
    return ([source] + row) if include_source else row


def _runway_headers(include_source: bool, lang: str = DEFAULT_LANG) -> list[str]:
    """Column headers for the runway table (shared by HTML and PDF)."""
    head = [t("runway.col.element", lang), t("col.status", lang),
            t("runway.col.needed_by", lang), t("col.owner", lang)]
    return ([t("col.solution", lang)] + head) if include_source else head


def _runway_cells(
    source: str, item: RunwayItem, include_source: bool,
    reference: date | None = None, lang: str = DEFAULT_LANG,
) -> list[str]:
    """Row values for one runway element, in the _runway_headers() order."""
    needed = (item.needed_by.strftime(t("fmt.date", lang))
              if item.needed_by else "–")
    if _runway_is_overdue(item, reference):
        needed += t("cell.overdue", lang)
    row = [f"{item.item_id}: {item.title}", t(_RUNWAY_TEXT_KEYS[item.status], lang),
           needed, item.owner or "–"]
    return ([source] + row) if include_source else row


def _nfr_title(
    nfrs: list[tuple[str, Nfr]],
    runway: list[tuple[str, RunwayItem]],
    title: str,
    reference: date | None = None,
    lang: str = DEFAULT_LANG,
) -> str:
    """Append NFR/runway counts (violated, at risk, gaps, overdue) to the title."""
    parts = []
    if nfrs:
        violated = sum(1 for _, n in nfrs if n.status == "violated")
        at_risk = sum(1 for _, n in nfrs if n.status == "at_risk")
        parts.append(t("nfr.seg", lang, total=len(nfrs), violated=violated,
                       at_risk=at_risk))
    if runway:
        gaps = sum(1 for _, r in runway if r.status == "gap")
        overdue = sum(1 for _, r in runway if _runway_is_overdue(r, reference))
        seg = t("runway.seg", lang, total=len(runway), gaps=gaps)
        seg += (t("runway.seg.overdue", lang, overdue=overdue)
                if overdue else ")")
        parts.append(seg)
    return f"{title} — " + " · ".join(parts)


def _nfr_include_source(
    nfrs: list[tuple[str, Nfr]], runway: list[tuple[str, RunwayItem]]
) -> bool:
    """Show the Solution column only when entries stem from several sources."""
    return len({source for source, _ in nfrs + runway}) > 1


def render_nfr_html(
    nfrs: list[tuple[str, Nfr]],
    runway: list[tuple[str, RunwayItem]],
    title: str | None = None,
    lang: str = DEFAULT_LANG,
    reference: date | None = None,
) -> str:
    """
    Render the NFR/runway dashboard as an HTML fragment.

    Two tables under one heading: the NFRs (violated first, coloured status
    cells) and the runway elements (gaps first, coloured status cells, overdue
    needed-by highlighted). A Solution column is prepended when the entries
    stem from more than one source (portfolio mode).

    Args:
        nfrs:      (source label, Nfr) pairs, unordered.
        runway:    (source label, RunwayItem) pairs, unordered.
        title:     Heading shown above the dashboard.
        reference: Overdue reference date (default: today) — injectable for tests.

    Returns:
        An HTML fragment, or "" when both lists are empty.
    """
    if not nfrs and not runway:
        return ""

    include_source = _nfr_include_source(nfrs, runway)
    offset = 1 if include_source else 0
    heading = _nfr_title(nfrs, runway, title or t("nfr.heading", lang), reference, lang)
    html = f"<h2 class='metric-heading'>{_html.escape(heading)}</h2>"

    if nfrs:
        head = "".join(f"<th>{_html.escape(h)}</th>"
                       for h in _nfr_headers(include_source, lang))
        rows = ""
        for source, nfr in _sorted_nfrs(nfrs):
            cells = [_html.escape(c)
                     for c in _nfr_cells(source, nfr, include_source, lang)]
            tds = []
            for col, c in enumerate(cells):
                if col == offset + 3:  # status
                    color = _NFR_STATUS_COLORS.get(nfr.status, "#ffffff")
                    tds.append(f"<td style='background:{color};font-weight:600'>{c}</td>")
                else:
                    tds.append(f"<td>{c}</td>")
            rows += f"<tr>{''.join(tds)}</tr>"
        html += (f"<table class='sr-summary'><tr>{head}</tr>{rows}</table>"
                 + _legend_line(_legend_group(
                     t("col.status", lang), _NFR_STATUS_COLORS,
                     _NFR_TEXT_KEYS, lang)))

    if runway:
        runway_overdue = False
        head = "".join(f"<th>{_html.escape(h)}</th>"
                       for h in _runway_headers(include_source, lang))
        rows = ""
        for source, item in _sorted_runway(runway):
            cells = [_html.escape(c)
                     for c in _runway_cells(source, item, include_source, reference, lang)]
            tds = []
            for col, c in enumerate(cells):
                if col == offset + 1:  # status
                    color = _RUNWAY_COLORS.get(item.status, "#ffffff")
                    tds.append(f"<td style='background:{color};font-weight:600'>{c}</td>")
                elif col == offset + 2 and _runway_is_overdue(item, reference):
                    runway_overdue = True
                    tds.append(f"<td style='background:{_OVERDUE_COLOR};font-weight:600'>{c}</td>")
                else:
                    tds.append(f"<td>{c}</td>")
            rows += f"<tr>{''.join(tds)}</tr>"
        html += (f"<table class='sr-summary'><tr>{head}</tr>{rows}</table>"
                 + _legend_line(
                     _legend_group(t("col.status", lang), _RUNWAY_COLORS,
                                   _RUNWAY_TEXT_KEYS, lang),
                     _legend_flag(t("runway.col.needed_by", lang),
                                  _OVERDUE_COLOR, t("legend.overdue", lang))
                     if runway_overdue else ""))

    return html


def nfr_figure(
    nfrs: list[tuple[str, Nfr]],
    runway: list[tuple[str, RunwayItem]],
    title: str | None = None,
    lang: str = DEFAULT_LANG,
    reference: date | None = None,
):
    """
    Render the NFR/runway dashboard as a plotly figure (for the PDF export).

    Mirrors render_nfr_html(): both tables stacked on one page, coloured
    status columns, overdue highlight.

    Args:
        nfrs:      (source label, Nfr) pairs, unordered.
        runway:    (source label, RunwayItem) pairs, unordered.
        title:     Figure title.
        reference: Overdue reference date (default: today).

    Returns:
        A plotly Figure containing one Table trace per non-empty block.
    """
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    include_source = _nfr_include_source(nfrs, runway)
    offset = 1 if include_source else 0
    blocks = []

    if nfrs:
        ordered_n = _sorted_nfrs(nfrs)
        headers = _nfr_headers(include_source, lang)
        rows = [_nfr_cells(source, nfr, include_source, lang)
                for source, nfr in ordered_n]
        fills = [["white"] * len(rows) for _ in headers]
        fills[offset + 3] = [_NFR_STATUS_COLORS.get(n.status, "#ffffff")
                             for _, n in ordered_n]
        blocks.append((headers, rows, fills))

    if runway:
        ordered_r = _sorted_runway(runway)
        headers = _runway_headers(include_source, lang)
        rows = [_runway_cells(source, item, include_source, reference, lang)
                for source, item in ordered_r]
        fills = [["white"] * len(rows) for _ in headers]
        fills[offset + 1] = [_RUNWAY_COLORS.get(r.status, "#ffffff")
                             for _, r in ordered_r]
        fills[offset + 2] = [_OVERDUE_COLOR if _runway_is_overdue(r, reference)
                             else "white" for _, r in ordered_r]
        blocks.append((headers, rows, fills))

    fig = make_subplots(
        rows=len(blocks), cols=1,
        specs=[[{"type": "table"}]] * len(blocks))
    for i, (headers, rows, fills) in enumerate(blocks, start=1):
        columns = [[row[c] for row in rows] for c in range(len(headers))]
        fig.add_trace(go.Table(
            header=dict(values=headers, fill_color="#f2f2f2", align="left"),
            cells=dict(values=columns, align="left", fill_color=fills),
        ), row=i, col=1)
    fig.update_layout(title=_nfr_title(nfrs, runway, title or t("nfr.heading", lang), reference, lang),
                      title_font_size=14, margin=dict(t=40, b=10))
    return fig


# ---------------------------------------------------------------------------
# Capability map & health (B1)
# ---------------------------------------------------------------------------

#: Cell background per capability health (traffic light).
_HEALTH_COLORS = {
    "healthy": "#e6f4e6",
    "at_risk": "#fff3cd",
    "critical": "#f8d7da",
}

#: A capability no ART contributes to is uncovered — business value nobody
#: delivers. Its ARTs cell is flagged yellow.
_UNCOVERED_COLOR = "#fff3cd"

#: Human-readable health labels (the JSON keys stay machine-friendly).
_HEALTH_LABELS = {
    "healthy": "healthy",
    "at_risk": "at risk",
    "critical": "critical",
}


def _sorted_capabilities(
    entries: list[tuple[str, Capability]]
) -> list[tuple[str, Capability]]:
    """Display order: critical first, then at risk, then healthy; then source."""
    return sorted(entries, key=lambda e: (
        HEALTH_ORDER.index(e[1].health), e[0], e[1].cap_id))


def _capability_headers(include_source: bool,
                        lang: str = DEFAULT_LANG) -> list[str]:
    """Column headers for the capability table (shared by HTML and PDF)."""
    head = [t("cap.col.capability", lang), t("cap.col.health", lang),
            t("cap.col.arts", lang), t("col.owner", lang),
            t("cap.col.assessed", lang)]
    return ([t("col.solution", lang)] + head) if include_source else head


def _capability_cells(
    source: str, cap: Capability, include_source: bool,
    lang: str = DEFAULT_LANG,
) -> list[str]:
    """Row values for one capability, in the _capability_headers() order."""
    assessed = (cap.assessed_on.strftime(t("fmt.date", lang))
                if cap.assessed_on else "–")
    row = [f"{cap.cap_id}: {cap.title}", t(_HEALTH_TEXT_KEYS[cap.health], lang),
           ", ".join(cap.arts) if cap.arts else "–",
           cap.owner or "–", assessed]
    return ([source] + row) if include_source else row


def _capability_title(
    entries: list[tuple[str, Capability]], title: str,
    lang: str = DEFAULT_LANG,
) -> str:
    """Append capability counts (critical, at risk, uncovered) to the title."""
    critical = sum(1 for _, c in entries if c.health == "critical")
    at_risk = sum(1 for _, c in entries if c.health == "at_risk")
    out = t("cap.title", lang, title=title, total=len(entries),
            critical=critical, at_risk=at_risk)
    uncovered = sum(1 for _, c in entries if not c.arts)
    if uncovered:
        out += t("cap.title.uncovered", lang, uncovered=uncovered)
    return out


def render_capabilities_html(
    entries: list[tuple[str, Capability]],
    title: str | None = None,
    lang: str = DEFAULT_LANG,
) -> str:
    """
    Render the capability map as an HTML fragment.

    Rows sort critical first with coloured health cells; a capability without
    contributing ARTs gets a flagged ARTs cell (uncovered business value). A
    Solution column is prepended when the entries stem from more than one
    source (portfolio mode).

    Args:
        entries: (source label, Capability) pairs, unordered.
        title:   Heading shown above the table.

    Returns:
        An HTML fragment (heading + styled table), or "" if entries is empty.
    """
    if not entries:
        return ""

    include_source = _capability_include_source(entries)
    offset = 1 if include_source else 0
    heading = _capability_title(entries, title or t("cap.heading", lang), lang)
    uncovered_seen = False
    head_html = "".join(
        f"<th>{_html.escape(h)}</th>"
        for h in _capability_headers(include_source, lang))

    rows_html = ""
    for source, cap in _sorted_capabilities(entries):
        cells = [_html.escape(c)
                 for c in _capability_cells(source, cap, include_source, lang)]
        tds = []
        for col, c in enumerate(cells):
            if col == offset + 1:  # health
                color = _HEALTH_COLORS.get(cap.health, "#ffffff")
                tds.append(f"<td style='background:{color};font-weight:600'>{c}</td>")
            elif col == offset + 2 and not cap.arts:  # uncovered
                uncovered_seen = True
                tds.append(f"<td style='background:{_UNCOVERED_COLOR};font-weight:600'>{c}</td>")
            else:
                tds.append(f"<td>{c}</td>")
        rows_html += f"<tr>{''.join(tds)}</tr>"

    legend = _legend_line(
        _legend_group(t("cap.col.health", lang), _HEALTH_COLORS,
                      _HEALTH_TEXT_KEYS, lang),
        _legend_flag(t("cap.col.arts", lang), _UNCOVERED_COLOR,
                     t("legend.uncovered", lang))
        if uncovered_seen else "",
    )

    return (
        f"<h2 class='metric-heading'>{_html.escape(heading)}</h2>"
        f"<table class='sr-summary'><tr>{head_html}</tr>{rows_html}</table>"
        f"{legend}"
    )


def _capability_include_source(entries: list[tuple[str, Capability]]) -> bool:
    """Show the Solution column only when entries stem from several sources."""
    return len({source for source, _ in entries}) > 1


def capability_figure(
    entries: list[tuple[str, Capability]],
    title: str | None = None,
    lang: str = DEFAULT_LANG,
):
    """
    Render the capability map as a plotly Table figure (for the PDF export).

    Mirrors render_capabilities_html(): coloured health column, flagged ARTs
    cell for uncovered capabilities.

    Args:
        entries: (source label, Capability) pairs, unordered.
        title:   Figure title.

    Returns:
        A plotly Figure containing a single Table trace.
    """
    import plotly.graph_objects as go

    include_source = _capability_include_source(entries)
    offset = 1 if include_source else 0
    ordered = _sorted_capabilities(entries)
    headers = _capability_headers(include_source, lang)
    rows = [_capability_cells(source, cap, include_source, lang)
            for source, cap in ordered]
    columns = [[row[c] for row in rows] for c in range(len(headers))]

    fill_colors: list[list[str]] = [["white"] * len(rows) for _ in headers]
    fill_colors[offset + 1] = [_HEALTH_COLORS.get(c.health, "#ffffff")
                               for _, c in ordered]
    fill_colors[offset + 2] = [_UNCOVERED_COLOR if not c.arts else "white"
                               for _, c in ordered]
    fig = go.Figure(go.Table(
        header=dict(values=headers, fill_color="#f2f2f2", align="left"),
        cells=dict(values=columns, align="left", fill_color=fill_colors),
    ))
    fig.update_layout(title=_capability_title(entries, title or t("cap.heading", lang), lang),
                      title_font_size=14, margin=dict(t=40, b=10))
    return fig


# ---------------------------------------------------------------------------
# Dependency / integration heatmap (B5)
# ---------------------------------------------------------------------------

#: Cell background per dependency status.
_DEP_STATUS_COLORS = {
    "blocked": "#f8d7da",
    "at_risk": "#fff3cd",
    "on_track": "#e6f4e6",
    "done": "#e2e3e5",
}

#: Human-readable status labels (the JSON keys stay machine-friendly).
_DEP_STATUS_LABELS = {
    "blocked": "blocked",
    "at_risk": "at risk",
    "on_track": "on track",
    "done": "done",
}


def _dep_is_overdue(dep: Dependency, reference: date | None = None) -> bool:
    """True when the due date has passed and the dependency is not done."""
    return (dep.due is not None
            and dep.status != DEP_DONE
            and dep.due < (reference or date.today()))


def _sorted_dependencies(
    entries: list[tuple[str, Dependency]]
) -> list[tuple[str, Dependency]]:
    """Display order: blocked first, then at risk/on track/done; then source."""
    return sorted(entries, key=lambda e: (
        DEP_STATUS_ORDER.index(e[1].status), e[0], e[1].dep_id))


def _dep_headers(include_source: bool, lang: str = DEFAULT_LANG) -> list[str]:
    """Column headers for the dependency table (shared by HTML and PDF)."""
    head = [t("dep.col.dependency", lang), t("dep.col.from", lang),
            t("dep.col.to", lang), t("col.status", lang), t("dep.col.due", lang)]
    return ([t("col.solution", lang)] + head) if include_source else head


def _dep_cells(
    source: str, dep: Dependency, include_source: bool,
    reference: date | None = None, lang: str = DEFAULT_LANG,
) -> list[str]:
    """Row values for one dependency, in the _dep_headers() order."""
    due = dep.due.strftime(t("fmt.date", lang)) if dep.due else "–"
    if _dep_is_overdue(dep, reference):
        due += t("cell.overdue", lang)
    row = [f"{dep.dep_id}: {dep.title}", dep.from_art, dep.to_art,
           t("dep." + dep.status if dep.status in ("blocked", "on_track",
                                                    "done")
             else "status.at_risk", lang), due]
    return ([source] + row) if include_source else row


def _dep_title(
    entries: list[tuple[str, Dependency]], title: str,
    reference: date | None = None,
    lang: str = DEFAULT_LANG,
) -> str:
    """Append dependency counts (blocked, at risk, overdue) to the title."""
    blocked = sum(1 for _, d in entries if d.status == DEP_BLOCKED)
    at_risk = sum(1 for _, d in entries if d.status == "at_risk")
    out = t("dep.title", lang, title=title, total=len(entries),
            blocked=blocked, at_risk=at_risk)
    overdue = sum(1 for _, d in entries if _dep_is_overdue(d, reference))
    out += t("dep.title.overdue", lang, overdue=overdue) if overdue else ")"
    return out


def _dep_include_source(entries: list[tuple[str, Dependency]]) -> bool:
    """Show the Solution column only when entries stem from several sources."""
    return len({source for source, _ in entries}) > 1


def _heatmap_grid(
    entries: list[tuple[str, Dependency]]
) -> tuple[list[str], list[str], dict[tuple[str, str], list[Dependency]]]:
    """
    Group the open dependencies (status != done) into a from x to grid.

    Returns:
        (from-unit names, to-unit names, {(from, to): dependencies}) —
        names sorted alphabetically for a stable layout.
    """
    cells: dict[tuple[str, str], list[Dependency]] = {}
    for _, dep in entries:
        if dep.status == DEP_DONE:
            continue
        cells.setdefault((dep.from_art, dep.to_art), []).append(dep)
    froms = sorted({f for f, _ in cells})
    tos = sorted({t for _, t in cells})
    return froms, tos, cells


def _heatmap_cell_color(deps: list[Dependency]) -> str:
    """Colour of one heatmap cell: its most urgent open status wins."""
    worst = min(DEP_STATUS_ORDER.index(d.status) for d in deps)
    return _DEP_STATUS_COLORS[DEP_STATUS_ORDER[worst]]


def render_dependencies_html(
    entries: list[tuple[str, Dependency]],
    title: str | None = None,
    lang: str = DEFAULT_LANG,
    reference: date | None = None,
) -> str:
    """
    Render the dependency heatmap and detail table as an HTML fragment.

    The heatmap counts open dependencies (status != done) per from/to pair;
    each cell carries the colour of its most urgent status. Below it, the
    detail table lists every dependency (blocked first, overdue due dates
    highlighted). A Solution column is prepended when the entries stem from
    more than one source (portfolio mode).

    Args:
        entries:   (source label, Dependency) pairs, unordered.
        title:     Heading shown above the heatmap.
        reference: Overdue reference date (default: today) — injectable for tests.

    Returns:
        An HTML fragment, or "" if entries is empty.
    """
    if not entries:
        return ""

    include_source = _dep_include_source(entries)
    offset = 1 if include_source else 0
    heading = _dep_title(entries, title or t("dep.heading", lang), reference, lang)
    html = f"<h2 class='metric-heading'>{_html.escape(heading)}</h2>"

    froms, tos, cells = _heatmap_grid(entries)
    if cells:
        head = f"<th>{_html.escape(t('dep.grid.header', lang))}</th>" + "".join(
            f"<th>{_html.escape(to)}</th>" for to in tos)
        rows = ""
        for f in froms:
            grid_tds = f"<td style='font-weight:600'>{_html.escape(f)}</td>"
            for to in tos:
                deps = cells.get((f, to))
                if deps:
                    color = _heatmap_cell_color(deps)
                    grid_tds += (f"<td style='background:{color};text-align:center;"
                                 f"font-weight:600'>{len(deps)}</td>")
                else:
                    grid_tds += "<td style='text-align:center'>–</td>"
            rows += f"<tr>{grid_tds}</tr>"
        html += (f"<table class='sr-summary'><tr>{head}</tr>{rows}</table>"
                 + _legend_line(_legend_group(
                     t("legend.worst_pair", lang),
                     _DEP_STATUS_COLORS, _DEP_TEXT_KEYS, lang)))

    dep_overdue = False
    head = "".join(f"<th>{_html.escape(h)}</th>"
                   for h in _dep_headers(include_source, lang))
    rows = ""
    for source, dep in _sorted_dependencies(entries):
        cells_row = [_html.escape(c)
                     for c in _dep_cells(source, dep, include_source, reference, lang)]
        tds = []
        for col, c in enumerate(cells_row):
            if col == offset + 3:  # status
                color = _DEP_STATUS_COLORS.get(dep.status, "#ffffff")
                tds.append(f"<td style='background:{color};font-weight:600'>{c}</td>")
            elif col == offset + 4 and _dep_is_overdue(dep, reference):
                dep_overdue = True
                tds.append(f"<td style='background:{_OVERDUE_COLOR};font-weight:600'>{c}</td>")
            else:
                tds.append(f"<td>{c}</td>")
        rows += f"<tr>{''.join(tds)}</tr>"
    html += (f"<table class='sr-summary'><tr>{head}</tr>{rows}</table>"
             + _legend_line(
                 _legend_group(t("col.status", lang), _DEP_STATUS_COLORS,
                               _DEP_TEXT_KEYS, lang),
                 _legend_flag(t("dep.col.due", lang), _OVERDUE_COLOR,
                              t("legend.overdue", lang))
                 if dep_overdue else ""))

    return html


def dependency_figure(
    entries: list[tuple[str, Dependency]],
    title: str | None = None,
    lang: str = DEFAULT_LANG,
    reference: date | None = None,
):
    """
    Render the dependency heatmap and detail table as a plotly figure (PDF).

    Mirrors render_dependencies_html(): heatmap grid on top (open
    dependencies, most urgent status colours the cell), detail table below.

    Args:
        entries:   (source label, Dependency) pairs, unordered.
        title:     Figure title.
        reference: Overdue reference date (default: today).

    Returns:
        A plotly Figure with one or two Table traces.
    """
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    include_source = _dep_include_source(entries)
    offset = 1 if include_source else 0
    blocks = []

    froms, tos, cells = _heatmap_grid(entries)
    if cells:
        headers = [t("dep.grid.header", lang)] + tos
        rows = []
        fills: list[list[str]] = [["white"] * len(froms) for _ in headers]
        for r, f in enumerate(froms):
            row = [f]
            for c, to in enumerate(tos, start=1):
                deps = cells.get((f, to))
                row.append(str(len(deps)) if deps else "–")
                if deps:
                    fills[c][r] = _heatmap_cell_color(deps)
            rows.append(row)
        blocks.append((headers, rows, fills))

    ordered = _sorted_dependencies(entries)
    headers = _dep_headers(include_source, lang)
    rows = [_dep_cells(source, dep, include_source, reference, lang)
            for source, dep in ordered]
    fills = [["white"] * len(rows) for _ in headers]
    fills[offset + 3] = [_DEP_STATUS_COLORS.get(d.status, "#ffffff")
                         for _, d in ordered]
    fills[offset + 4] = [_OVERDUE_COLOR if _dep_is_overdue(d, reference)
                         else "white" for _, d in ordered]
    blocks.append((headers, rows, fills))

    fig = make_subplots(
        rows=len(blocks), cols=1,
        specs=[[{"type": "table"}]] * len(blocks))
    for i, (headers, rows, fills) in enumerate(blocks, start=1):
        columns = [[row[c] for row in rows] for c in range(len(headers))]
        fig.add_trace(go.Table(
            header=dict(values=headers, fill_color="#f2f2f2", align="left"),
            cells=dict(values=columns, align="left", fill_color=fills),
        ), row=i, col=1)
    fig.update_layout(title=_dep_title(entries, title or t("dep.heading", lang), reference, lang),
                      title_font_size=14, margin=dict(t=40, b=10))
    return fig


# ---------------------------------------------------------------------------
# Decision / assumption log (B4)
# ---------------------------------------------------------------------------

#: Cell background per log-entry status (decision and assumption sets).
_LOG_STATUS_COLORS = {
    "proposed": "#fff3cd",
    "accepted": "#e6f4e6",
    "superseded": "#e2e3e5",
    "open": "#fff3cd",
    "confirmed": "#e6f4e6",
    "invalidated": "#f8d7da",
}

#: Display order: overdue assumptions surface via _sorted_log_entries; among
#: statuses the actionable ones come first, history last.
_LOG_STATUS_RANK = {
    "open": 0,
    "proposed": 1,
    "accepted": 2,
    "confirmed": 3,
    "invalidated": 4,
    "superseded": 5,
}


def _entry_review_due(entry: LogEntry, reference: date | None = None) -> bool:
    """True when an open assumption's review date has passed."""
    return (entry.kind == KIND_ASSUMPTION
            and entry.status == ASSUMPTION_OPEN
            and entry.review_by is not None
            and entry.review_by < (reference or date.today()))


def _sorted_log_entries(
    entries: list[tuple[str, LogEntry]], reference: date | None = None
) -> list[tuple[str, LogEntry]]:
    """Display order: review-due assumptions first, then by status, source, id."""
    return sorted(entries, key=lambda e: (
        0 if _entry_review_due(e[1], reference) else 1,
        _LOG_STATUS_RANK.get(e[1].status, 9), e[0], e[1].entry_id))


def _log_headers(include_source: bool, lang: str = DEFAULT_LANG) -> list[str]:
    """Column headers for the decision-log table (shared by HTML and PDF)."""
    head = [t("log.col.type", lang), t("log.col.entry", lang),
            t("col.status", lang), t("col.owner", lang),
            t("log.col.logged", lang), t("log.col.review_by", lang)]
    return ([t("col.solution", lang)] + head) if include_source else head


def _log_cells(
    source: str, entry: LogEntry, include_source: bool,
    reference: date | None = None, lang: str = DEFAULT_LANG,
) -> list[str]:
    """Row values for one log entry, in the _log_headers() order."""
    text = f"{entry.entry_id}: {entry.title}"
    if entry.supersedes:
        text += t("cell.supersedes", lang, id=entry.supersedes)
    fmt = t("fmt.date", lang)
    logged = entry.logged_on.strftime(fmt) if entry.logged_on else "–"
    review = entry.review_by.strftime(fmt) if entry.review_by else "–"
    if _entry_review_due(entry, reference):
        review += t("cell.review_due", lang)
    row = [t(_KIND_TEXT_KEYS[entry.kind], lang), text, t(_LOG_TEXT_KEYS[entry.status], lang),
           entry.owner or "–", logged, review]
    return ([source] + row) if include_source else row


def _log_title(
    entries: list[tuple[str, LogEntry]], title: str,
    reference: date | None = None,
    lang: str = DEFAULT_LANG,
) -> str:
    """Append entry counts (decisions, assumptions, due for review)."""
    decisions = sum(1 for _, e in entries if e.kind == KIND_DECISION)
    assumptions = sum(1 for _, e in entries if e.kind == KIND_ASSUMPTION)
    out = t("log.title", lang, title=title, decisions=decisions,
            assumptions=assumptions)
    due = sum(1 for _, e in entries if _entry_review_due(e, reference))
    if due:
        out += t("log.title.due", lang, due=due)
    return out


def _log_include_source(entries: list[tuple[str, LogEntry]]) -> bool:
    """Show the Solution column only when entries stem from several sources."""
    return len({source for source, _ in entries}) > 1


def render_decisions_html(
    entries: list[tuple[str, LogEntry]],
    title: str | None = None,
    lang: str = DEFAULT_LANG,
    reference: date | None = None,
) -> str:
    """
    Render the decision/assumption log as an HTML fragment.

    Open assumptions whose review date has passed sort first with a red
    Review-by cell; otherwise actionable statuses (open/proposed) precede
    history (superseded). A Solution column is prepended when the entries
    stem from more than one source (portfolio mode).

    Args:
        entries:   (source label, LogEntry) pairs, unordered.
        title:     Heading shown above the table.
        reference: Review-due reference date (default: today) — injectable
                   for tests.

    Returns:
        An HTML fragment (heading + styled table), or "" if entries is empty.
    """
    if not entries:
        return ""

    include_source = _log_include_source(entries)
    offset = 1 if include_source else 0
    heading = _log_title(entries, title or t("log.heading", lang), reference, lang)
    review_due = False
    head_html = "".join(f"<th>{_html.escape(h)}</th>"
                        for h in _log_headers(include_source, lang))

    rows_html = ""
    for source, entry in _sorted_log_entries(entries, reference):
        cells = [_html.escape(c)
                 for c in _log_cells(source, entry, include_source, reference, lang)]
        tds = []
        for col, c in enumerate(cells):
            if col == offset + 2:  # status
                color = _LOG_STATUS_COLORS.get(entry.status, "#ffffff")
                tds.append(f"<td style='background:{color};font-weight:600'>{c}</td>")
            elif col == offset + 5 and _entry_review_due(entry, reference):
                review_due = True
                tds.append(f"<td style='background:{_OVERDUE_COLOR};font-weight:600'>{c}</td>")
            else:
                tds.append(f"<td>{c}</td>")
        rows_html += f"<tr>{''.join(tds)}</tr>"

    legend = _legend_line(
        _legend_group(t("col.status", lang), _LOG_STATUS_COLORS,
                      _LOG_TEXT_KEYS, lang),
        _legend_flag(t("log.col.review_by", lang), _OVERDUE_COLOR,
                     t("legend.review_due", lang))
        if review_due else "",
    )

    return (
        f"<h2 class='metric-heading'>{_html.escape(heading)}</h2>"
        f"<table class='sr-summary'><tr>{head_html}</tr>{rows_html}</table>"
        f"{legend}"
    )


def decisions_figure(
    entries: list[tuple[str, LogEntry]],
    title: str | None = None,
    lang: str = DEFAULT_LANG,
    reference: date | None = None,
):
    """
    Render the decision/assumption log as a plotly Table figure (PDF export).

    Mirrors render_decisions_html(): coloured status column, review-due
    highlight in the Review-by column.

    Args:
        entries:   (source label, LogEntry) pairs, unordered.
        title:     Figure title.
        reference: Review-due reference date (default: today).

    Returns:
        A plotly Figure containing a single Table trace.
    """
    import plotly.graph_objects as go

    include_source = _log_include_source(entries)
    offset = 1 if include_source else 0
    ordered = _sorted_log_entries(entries, reference)
    headers = _log_headers(include_source, lang)
    rows = [_log_cells(source, entry, include_source, reference, lang)
            for source, entry in ordered]
    columns = [[row[c] for row in rows] for c in range(len(headers))]

    fill_colors: list[list[str]] = [["white"] * len(rows) for _ in headers]
    fill_colors[offset + 2] = [_LOG_STATUS_COLORS.get(e.status, "#ffffff")
                               for _, e in ordered]
    fill_colors[offset + 5] = [_OVERDUE_COLOR if _entry_review_due(e, reference)
                               else "white" for _, e in ordered]
    fig = go.Figure(go.Table(
        header=dict(values=headers, fill_color="#f2f2f2", align="left"),
        cells=dict(values=columns, align="left", fill_color=fill_colors),
    ))
    fig.update_layout(title=_log_title(entries, title or t("log.heading", lang), reference, lang),
                      title_font_size=14, margin=dict(t=40, b=10))
    return fig


# ---------------------------------------------------------------------------
# SLO / error budgets (C1) and DORA / code quality (C2)
# ---------------------------------------------------------------------------

_SLO_STATUS_COLORS = {
    "breached": "#f8d7da",
    "at_risk": "#fff3cd",
    "met": "#e6f4e6",
    "unknown": "#e2e3e5",
}

_TIER_COLORS = {
    "elite": "#e6f4e6",
    "high": "#e6f4e6",
    "medium": "#fff3cd",
    "low": "#f8d7da",
    "unknown": "#e2e3e5",
}

_RATING_COLORS = {"A": "#e6f4e6", "B": "#e6f4e6", "C": "#fff3cd",
                  "D": "#f8d7da", "E": "#f8d7da"}


def _fmt_num(value: float | int | None, digits: int = 1) -> str:
    if value is None:
        return "–"
    return f"{value:.{digits}f}"


def _slo_sorted(entries: list[tuple[str, SloRecord]]) -> list[tuple[str, SloRecord]]:
    return sorted(entries, key=lambda e: (
        SLO_STATUS_ORDER.index(slo_status(e[1])), e[0], e[1].service))


def _slo_title(entries: list[tuple[str, SloRecord]], title: str,
               lang: str = DEFAULT_LANG) -> str:
    statuses = [slo_status(r) for _, r in entries]
    breached = statuses.count("breached")
    at_risk = statuses.count("at_risk")
    return t("slo.title", lang, title=title, total=len(entries),
             breached=breached, at_risk=at_risk)


def _slo_headers(include_source: bool, lang: str = DEFAULT_LANG) -> list[str]:
    head = [t("slo.col.service", lang), t("slo.col.slo", lang),
            t("slo.col.target", lang), t("slo.col.sli", lang),
            t("slo.col.budget", lang), t("col.window", lang),
            t("col.source", lang), t("col.status", lang)]
    return ([t("col.solution", lang)] + head) if include_source else head


def _slo_cells(source: str, r: SloRecord, include_source: bool) -> list[str]:
    row = [r.service, r.slo, _fmt_num(r.target_pct, 2), _fmt_num(r.sli_pct, 2),
           _fmt_num(error_budget_remaining_pct(r)), r.window,
           r.source or "–", slo_status(r).replace("_", " ")]
    return ([source] + row) if include_source else row


def render_slo_html(
    entries: list[tuple[str, SloRecord]],
    title: str | None = None,
    lang: str = DEFAULT_LANG,
) -> str:
    """
    Render the SLO register as an HTML fragment (C1).

    Status and error budget are derived centrally (portfolio.slo_config),
    so every data source is judged by the same rule; breached SLOs sort
    first. A Solution column appears in portfolio mode.
    """
    if not entries:
        return ""
    include_source = _log_include_source(entries)  # type: ignore[arg-type]
    offset = 1 if include_source else 0
    head = "".join(f"<th>{_html.escape(h)}</th>"
                   for h in _slo_headers(include_source, lang))
    rows = ""
    for source, record in _slo_sorted(entries):
        status = slo_status(record)
        cells = [_html.escape(c)
                 for c in _slo_cells(source, record, include_source)]
        tds = []
        for col, c in enumerate(cells):
            if col == offset + 7:
                color = _SLO_STATUS_COLORS.get(status, "#ffffff")
                tds.append(
                    f"<td style='background:{color};font-weight:600'>{c}</td>")
            else:
                tds.append(f"<td>{c}</td>")
        rows += f"<tr>{''.join(tds)}</tr>"
    heading = _slo_title(entries, title or t("slo.heading", lang), lang)
    legend = _legend_line(_legend_group("Status", _SLO_STATUS_COLORS))
    return (f"<h2 class='metric-heading'>{_html.escape(heading)}</h2>"
            f"<table class='sr-summary'><tr>{head}</tr>{rows}</table>"
            f"{legend}")


def slo_figure(
    entries: list[tuple[str, SloRecord]],
    title: str | None = None,
    lang: str = DEFAULT_LANG,
):
    """Render the SLO register as a plotly Table figure (PDF export)."""
    import plotly.graph_objects as go

    include_source = _log_include_source(entries)  # type: ignore[arg-type]
    offset = 1 if include_source else 0
    ordered = _slo_sorted(entries)
    headers = _slo_headers(include_source, lang)
    rows = [_slo_cells(source, r, include_source) for source, r in ordered]
    columns = [[row[c] for row in rows] for c in range(len(headers))]
    fills: list[list[str]] = [["white"] * len(rows) for _ in headers]
    fills[offset + 7] = [_SLO_STATUS_COLORS.get(slo_status(r), "#ffffff")
                         for _, r in ordered]
    fig = go.Figure(go.Table(
        header=dict(values=headers, fill_color="#f2f2f2", align="left"),
        cells=dict(values=columns, align="left", fill_color=fills),
    ))
    fig.update_layout(title=_slo_title(entries, title or t("slo.heading", lang), lang),
                      title_font_size=14, margin=dict(t=40, b=10))
    return fig


def _dora_title(entries: list[tuple[str, DoraRecord]], title: str,
                lang: str = DEFAULT_LANG) -> str:
    tiers = [unit_tier(r) for _, r in entries]
    known = [t for t in tiers if t != TIER_UNKNOWN]
    worst = min(known, key=TIER_ORDER.index) if known else TIER_UNKNOWN
    return t("dora.title", lang, title=title, total=len(entries),
             worst=t(_TIER_TEXT_KEYS[worst], lang))


def _dora_headers(include_source: bool, lang: str = DEFAULT_LANG) -> list[str]:
    # Die vier DORA-Kennzahlnamen sind stehende Fachbegriffe und bleiben,
    # wie build_reports sie fuehrt — uebersetzt werden die Spalten drumherum.
    head = [t("col.unit", lang)] + [label for label, _f in DORA_TIER_FUNCS] + [
        t("dora.col.overall", lang), t("col.window", lang), t("col.source", lang)]
    return ([t("col.solution", lang)] + head) if include_source else head


def _dora_values(r: DoraRecord) -> list[str]:
    return [_fmt_num(r.deployments_per_day, 2), _fmt_num(r.lead_time_hours),
            _fmt_num(r.change_failure_rate_pct), _fmt_num(r.time_to_restore_hours)]


def _dora_sorted(entries: list[tuple[str, DoraRecord]]) -> list[tuple[str, DoraRecord]]:
    order = {t: i for i, t in enumerate(TIER_ORDER)}
    return sorted(entries, key=lambda e: (
        order.get(unit_tier(e[1]), len(order)), e[0], e[1].unit))


def render_dora_html(
    dora_entries: list[tuple[str, DoraRecord]],
    quality_entries: list[tuple[str, QualityRecord]],
    title: str | None = None,
    lang: str = DEFAULT_LANG,
) -> str:
    """
    Render DORA and quality registers as an HTML fragment (C2).

    Each DORA metric cell is coloured by its own tier (published DORA
    thresholds, applied centrally); the overall tier is the unit's worst
    metric. Worst units sort first. The quality table follows below.
    """
    if not dora_entries and not quality_entries:
        return ""
    html = ""
    if dora_entries:
        include_source = _log_include_source(dora_entries)  # type: ignore[arg-type]
        head = "".join(f"<th>{_html.escape(h)}</th>"
                       for h in _dora_headers(include_source, lang))
        rows = ""
        for source, r in _dora_sorted(dora_entries):
            tiers = [func(r) for _label, func in DORA_TIER_FUNCS]
            values = _dora_values(r)
            tds = ([f"<td>{_html.escape(source)}</td>"] if include_source else [])
            tds.append(f"<td>{_html.escape(r.unit)}</td>")
            for value, tier in zip(values, tiers):
                color = _TIER_COLORS.get(tier, "#ffffff")
                tds.append(f"<td style='background:{color}'>{value}</td>")
            overall = unit_tier(r)
            color = _TIER_COLORS.get(overall, "#ffffff")
            tds.append(f"<td style='background:{color};font-weight:600'>"
                       f"{overall}</td>")
            tds.append(f"<td>{_html.escape(r.window)}</td>")
            tds.append(f"<td>{_html.escape(r.source or '–')}</td>")
            rows += f"<tr>{''.join(tds)}</tr>"
        heading = _dora_title(dora_entries, title or t("dora.heading", lang), lang)
        html += (f"<h2 class='metric-heading'>{_html.escape(heading)}</h2>"
                 f"<table class='sr-summary'><tr>{head}</tr>{rows}</table>"
                 + _legend_line(_legend_group(
                     t("legend.tier", lang), _TIER_COLORS,
                     _TIER_TEXT_KEYS, lang)))

    if quality_entries:
        include_source = _log_include_source(quality_entries)  # type: ignore[arg-type]
        head_cols = ["Unit", "Coverage %", "Maintainability",
                     "Critical issues", "Data source"]
        if include_source:
            head_cols = ["Solution"] + head_cols
        head = "".join(f"<th>{_html.escape(h)}</th>" for h in head_cols)
        rows = ""
        crit_seen = False
        for source, q in sorted(quality_entries,
                                key=lambda e: (e[0], e[1].unit)):
            tds = ([f"<td>{_html.escape(source)}</td>"] if include_source else [])
            tds.append(f"<td>{_html.escape(q.unit)}</td>")
            tds.append(f"<td>{_fmt_num(q.coverage_pct)}</td>")
            rating = q.maintainability or "–"
            color = _RATING_COLORS.get(rating, "#ffffff")
            tds.append(f"<td style='background:{color}'>"
                       f"{_html.escape(rating)}</td>")
            crit = q.critical_issues
            crit_seen = crit_seen or bool(crit)
            crit_style = (f" style='background:{_SLO_STATUS_COLORS['breached']};"
                          f"font-weight:600'" if crit else "")
            tds.append(f"<td{crit_style}>{'–' if crit is None else crit}</td>")
            tds.append(f"<td>{_html.escape(q.source or '–')}</td>")
            rows += f"<tr>{''.join(tds)}</tr>"
        html += (f"<h3 class='metric-heading'>Code quality</h3>"
                 f"<table class='sr-summary'><tr>{head}</tr>{rows}</table>"
                 + _legend_line(
                     _legend_group(t("legend.rating", lang), _RATING_COLORS),
                     _legend_flag(t("quality.col.critical", lang),
                                  _SLO_STATUS_COLORS["breached"],
                                  t("legend.crit_issue", lang))
                     if crit_seen else ""))
    return html


def dora_figure(
    dora_entries: list[tuple[str, DoraRecord]],
    quality_entries: list[tuple[str, QualityRecord]],
    title: str | None = None,
    lang: str = DEFAULT_LANG,
):
    """Render DORA + quality as a plotly figure (PDF export)."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    blocks = []
    if dora_entries:
        include_source = _log_include_source(dora_entries)  # type: ignore[arg-type]
        ordered = _dora_sorted(dora_entries)
        headers = _dora_headers(include_source, lang)
        rows = []
        fills: list[list[str]] = []
        for source, r in ordered:
            row = ([source] if include_source else []) + [r.unit] \
                + _dora_values(r) + [unit_tier(r), r.window, r.source or "–"]
            rows.append(row)
        for _c in range(len(headers)):
            fills.append(["white"] * len(rows))
        offset = (1 if include_source else 0) + 1
        for m, (_label, func) in enumerate(DORA_TIER_FUNCS):
            fills[offset + m] = [_TIER_COLORS.get(func(r), "white")
                                 for _, r in ordered]
        fills[offset + 4] = [_TIER_COLORS.get(unit_tier(r), "white")
                             for _, r in ordered]
        blocks.append((headers, rows, fills))
    if quality_entries:
        include_source = _log_include_source(quality_entries)  # type: ignore[arg-type]
        headers = (["Solution"] if include_source else []) + [
            "Unit", "Coverage %", "Maintainability", "Critical issues",
            "Data source"]
        ordered_q = sorted(quality_entries, key=lambda e: (e[0], e[1].unit))
        rows = [([s] if include_source else []) + [
            q.unit, _fmt_num(q.coverage_pct), q.maintainability or "–",
            "–" if q.critical_issues is None else str(q.critical_issues),
            q.source or "–"] for s, q in ordered_q]
        fills = [["white"] * len(rows) for _ in headers]
        offset = (1 if include_source else 0) + 2
        fills[offset] = [_RATING_COLORS.get(q.maintainability, "white")
                         for _, q in ordered_q]
        fills[offset + 1] = [_SLO_STATUS_COLORS["breached"]
                             if q.critical_issues else "white"
                             for _, q in ordered_q]
        blocks.append((headers, rows, fills))

    fig = make_subplots(rows=len(blocks), cols=1,
                        specs=[[{"type": "table"}]] * len(blocks))
    for i, (headers, rows, fills) in enumerate(blocks, start=1):
        columns = [[row[c] for row in rows] for c in range(len(headers))]
        fig.add_trace(go.Table(
            header=dict(values=headers, fill_color="#f2f2f2", align="left"),
            cells=dict(values=columns, align="left", fill_color=fills),
        ), row=i, col=1)
    fig.update_layout(
        title=_dora_title(dora_entries, title or t("dora.heading", lang), lang) if dora_entries else title,
        title_font_size=14, margin=dict(t=40, b=10))
    return fig


# ---------------------------------------------------------------------------
# Flow-problem backlog (B6, VSC-1)
# ---------------------------------------------------------------------------

_FLOW_STATUS_COLORS = {
    "open": "#fff3cd",
    "committed": "#d1ecf1",
    "resolved": "#e6f4e6",
    "dropped": "#e2e3e5",
}


def _flow_sorted(
    entries: list[tuple[str, FlowProblem]]
) -> list[tuple[str, FlowProblem]]:
    """Survivors first (the workshop pattern), then by status/source/id."""
    return sorted(entries, key=lambda e: (
        not e[1].survived,
        FLOW_STATUS_ORDER.index(e[1].status), e[0], e[1].problem_id))


def _flow_title(entries: list[tuple[str, FlowProblem]], title: str,
                lang: str = DEFAULT_LANG) -> str:
    problems = [p for _, p in entries]
    open_count = sum(1 for p in problems
                     if p.status in (FLOW_OPEN, "committed"))
    cross = sum(1 for p in problems if p.cross_vs)
    survived = sum(1 for p in problems if p.survived)
    return t("flow.title", lang, title=title, total=len(problems),
             unresolved=open_count, cross=cross, survived=survived,
             threshold=SURVIVED_CONFERENCES_THRESHOLD)


def _flow_headers(include_source: bool, lang: str = DEFAULT_LANG) -> list[str]:
    head = [t("flow.col.problem", lang), t("flow.col.raised_by", lang),
            t("flow.col.streams", lang), t("col.status", lang),
            t("flow.col.commitment", lang), t("flow.col.follow_up", lang),
            t("flow.col.conferences", lang), t("col.since", lang)]
    return ([t("col.solution", lang)] + head) if include_source else head


def _flow_cells(
    source: str, p: FlowProblem, include_source: bool,
    reference: date | None = None, lang: str = DEFAULT_LANG,
) -> list[str]:
    streams = ", ".join(p.value_streams)
    if p.cross_vs:
        streams = t("cell.cross", lang) + streams
    since = "–"
    if p.raised_on:
        days = ((reference or date.today()) - p.raised_on).days
        since = t("quality.age", lang,
                  date=p.raised_on.strftime(t("fmt.date", lang)), days=days)
    row = [f"{p.problem_id}: {p.title}", p.source or "–", streams,
           t(_FLOW_TEXT_KEYS[p.status], lang), p.resolution_commitment or "–",
           p.follow_up_pi or "–", str(p.conferences), since]
    return ([source] + row) if include_source else row


def render_flow_problems_html(
    entries: list[tuple[str, FlowProblem]],
    title: str | None = None,
    lang: str = DEFAULT_LANG,
    reference: date | None = None,
) -> str:
    """
    Render the conference impediment backlog as an HTML fragment (B6).

    Problems that survived several conferences unresolved sort first and
    carry a red conference counter — the workshop pattern 'logged, never
    mitigated, back next PI' made measurable. Cross-VS problems are
    flagged in the value-streams cell.
    """
    if not entries:
        return ""
    include_source = _log_include_source(entries)  # type: ignore[arg-type]
    offset = 1 if include_source else 0
    survivor_seen = False
    head = "".join(f"<th>{_html.escape(h)}</th>"
                   for h in _flow_headers(include_source, lang))
    rows = ""
    for source, p in _flow_sorted(entries):
        cells = [_html.escape(c)
                 for c in _flow_cells(source, p, include_source, reference, lang)]
        tds = []
        for col, c in enumerate(cells):
            if col == offset + 3:  # status
                color = _FLOW_STATUS_COLORS.get(p.status, "#ffffff")
                tds.append(
                    f"<td style='background:{color};font-weight:600'>{c}</td>")
            elif col == offset + 6 and p.survived:  # conference counter
                survivor_seen = True
                tds.append(f"<td style='background:{_OVERDUE_COLOR};"
                           f"font-weight:700'>{c}</td>")
            elif col == offset + 2 and p.cross_vs:
                tds.append(f"<td style='font-weight:600'>{c}</td>")
            else:
                tds.append(f"<td>{c}</td>")
        rows += f"<tr>{''.join(tds)}</tr>"
    heading = _flow_title(entries, title or t("flow.heading", lang), lang)
    legend = _legend_line(
        _legend_group(t("col.status", lang), _FLOW_STATUS_COLORS,
                      _FLOW_TEXT_KEYS, lang),
        _legend_flag(t("flow.col.conferences", lang), _OVERDUE_COLOR,
                     t("legend.survivor", lang))
        if survivor_seen else "",
    )
    return (f"<h2 class='metric-heading'>{_html.escape(heading)}</h2>"
            f"<table class='sr-summary'><tr>{head}</tr>{rows}</table>"
            f"{legend}")


def flow_problems_figure(
    entries: list[tuple[str, FlowProblem]],
    title: str | None = None,
    lang: str = DEFAULT_LANG,
    reference: date | None = None,
):
    """Render the flow-problem backlog as a plotly Table figure (PDF)."""
    import plotly.graph_objects as go

    include_source = _log_include_source(entries)  # type: ignore[arg-type]
    offset = 1 if include_source else 0
    ordered = _flow_sorted(entries)
    headers = _flow_headers(include_source, lang)
    rows = [_flow_cells(source, p, include_source, reference, lang)
            for source, p in ordered]
    columns = [[row[c] for row in rows] for c in range(len(headers))]
    fills: list[list[str]] = [["white"] * len(rows) for _ in headers]
    fills[offset + 3] = [_FLOW_STATUS_COLORS.get(p.status, "#ffffff")
                         for _, p in ordered]
    fills[offset + 6] = [_OVERDUE_COLOR if p.survived else "white"
                         for _, p in ordered]
    fig = go.Figure(go.Table(
        header=dict(values=headers, fill_color="#f2f2f2", align="left"),
        cells=dict(values=columns, align="left", fill_color=fills),
    ))
    fig.update_layout(title=_flow_title(entries, title or t("flow.heading", lang), lang),
                      title_font_size=14, margin=dict(t=40, b=10))
    return fig


# ---------------------------------------------------------------------------
# Strategic themes & integrated roadmap (B7, VSC-2)
# ---------------------------------------------------------------------------

_EPIC_STATUS_MARK = {"planned": "", "in_progress": " ⟳", "done": " ✓"}


def _themes_title(
    theme_entries: list[tuple[str, StrategicTheme]],
    epic_entries: list[tuple[str, Epic]],
    title: str,
    lang: str = DEFAULT_LANG,
) -> str:
    used = {e.theme for _, e in epic_entries if e.theme}
    orphans = sum(1 for _, th in theme_entries if th.theme_id not in used)
    zombies = sum(1 for _, e in epic_entries if not e.theme)
    return t("themes.title", lang, title=title, themes=len(theme_entries),
             epics=len(epic_entries), orphans=orphans, zombies=zombies)


def render_themes_html(
    theme_entries: list[tuple[str, StrategicTheme]],
    epic_entries: list[tuple[str, Epic]],
    title: str | None = None,
    lang: str = DEFAULT_LANG,
) -> str:
    """
    Render strategic themes and the integrated roadmap (B7).

    Three parts: the theme table (a theme without epics is flagged red as
    'declared & forgotten'), the roadmap matrix (rows = trains, columns =
    P1·P2·Y1·Y2·Y3 — near-term granular, far-term coarse; zombie epics
    red), and, when present, the zombie list (epics without a strategic
    home). Orphanhood is judged across the whole portfolio: a theme
    served by another solution's epic is not orphaned.
    """
    if not theme_entries and not epic_entries:
        return ""
    used = {e.theme for _, e in epic_entries if e.theme}
    epic_count: dict[str, int] = {}
    for _, e in epic_entries:
        if e.theme:
            epic_count[e.theme] = epic_count.get(e.theme, 0) + 1

    heading = _themes_title(theme_entries, epic_entries,
                            title or t("themes.heading", lang), lang)
    html = f"<h2 class='metric-heading'>{_html.escape(heading)}</h2>"

    if theme_entries:
        include_source = _log_include_source(theme_entries)  # type: ignore[arg-type]
        head_cols = [t("themes.col.theme", lang),
                     t("themes.col.description", lang),
                     t("themes.col.epics", lang)]
        if include_source:
            head_cols = [t("col.solution", lang)] + head_cols
        head = "".join(f"<th>{_html.escape(h)}</th>" for h in head_cols)
        rows = ""
        forgotten_seen = False
        ordered = sorted(theme_entries,
                         key=lambda t: (t[1].theme_id in used, t[0],
                                        t[1].theme_id))
        for source, th in ordered:
            count = epic_count.get(th.theme_id, 0)
            tds = ([f"<td>{_html.escape(source)}</td>"]
                   if include_source else [])
            tds.append(f"<td>{_html.escape(th.theme_id)}: "
                       f"{_html.escape(th.title)}</td>")
            tds.append(f"<td>{_html.escape(th.description or '–')}</td>")
            if count:
                tds.append(f"<td>{count}</td>")
            else:
                forgotten_seen = True
                tds.append(f"<td style='background:{_OVERDUE_COLOR};"
                           f"font-weight:600'>"
                           f"{t('themes.forgotten', lang)}</td>")
            rows += f"<tr>{''.join(tds)}</tr>"
        html += (f"<table class='sr-summary'><tr>{head}</tr>{rows}</table>"
                 + (_legend_line(_legend_flag(
                     t("themes.col.epics", lang), _OVERDUE_COLOR,
                     t("legend.theme_forgotten", lang)))
                    if forgotten_seen else ""))

    if epic_entries:
        trains = sorted({e.train for _, e in epic_entries})
        head = f"<th>{_html.escape(t('roadmap.grid.header', lang))}</th>" + "".join(
            f"<th>{h}</th>" for h in HORIZONS)
        rows = ""
        for train in trains:
            row_tds = f"<td style='font-weight:600'>{_html.escape(train)}</td>"
            for horizon in HORIZONS:
                cell_epics = [e for _, e in epic_entries
                              if e.train == train and e.horizon == horizon]
                if not cell_epics:
                    row_tds += "<td>–</td>"
                    continue
                parts = []
                for e in sorted(cell_epics, key=lambda x: x.epic_id):
                    label = (f"{_html.escape(e.epic_id)}: "
                             f"{_html.escape(e.title)}"
                             f"{_EPIC_STATUS_MARK.get(e.status, '')}")
                    if e.theme:
                        label += f" [{_html.escape(e.theme)}]"
                        parts.append(label)
                    else:
                        parts.append(
                            f"<span style='background:{_OVERDUE_COLOR};"
                            f"font-weight:600'>{label} [ZOMBIE]</span>")
                row_tds += f"<td>{'<br/>'.join(parts)}</td>"
            rows += f"<tr>{row_tds}</tr>"
        marks = " · ".join(
            f"{mark.strip()} = {t('epic.' + status, lang)}"
            for status, mark in _EPIC_STATUS_MARK.items() if mark)
        html += (f"<h3 class='metric-heading'>"
                 f"{_html.escape(t('roadmap.heading', lang))}</h3>"
                 f"<table class='sr-summary'><tr>{head}</tr>{rows}</table>"
                 + _legend_line(
                     f"<span class='sr-legend-group'>"
                     f"<b>{_html.escape(t('legend.marks', lang))}:</b> "
                     f"{_html.escape(marks)} "
                     f"{_html.escape(t('legend.marks.none', lang))}</span>",
                     _legend_flag(t("themes.col.epics", lang), _OVERDUE_COLOR,
                                  t("legend.zombie", lang))))

    zombies = [(s, e) for s, e in epic_entries if not e.theme]
    if zombies:
        items = "".join(
            f"<li style='background:{_OVERDUE_COLOR};padding:2px 6px'>"
            f"{_html.escape(s)} · {_html.escape(e.epic_id)}: "
            f"{_html.escape(e.title)} ({_html.escape(e.train)}, "
            f"{e.horizon})</li>" for s, e in zombies)
        # Keine Legende: die Ueberschrift sagt bereits, was jeder Eintrag
        # dieser Liste ist — eine Farberklaerung waere hier Doppelung.
        html += (f"<h3 class='metric-heading'>"
                 f"{_html.escape(t('zombies.heading', lang))}</h3>"
                 f"<ul class='delta'>{items}</ul>")
    return html


def themes_figure(
    theme_entries: list[tuple[str, StrategicTheme]],
    epic_entries: list[tuple[str, Epic]],
    title: str | None = None,
    lang: str = DEFAULT_LANG,
):
    """Render themes + roadmap matrix as a plotly figure (PDF export)."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    used = {e.theme for _, e in epic_entries if e.theme}
    epic_count: dict[str, int] = {}
    for _, e in epic_entries:
        if e.theme:
            epic_count[e.theme] = epic_count.get(e.theme, 0) + 1

    blocks = []
    if theme_entries:
        include_source = _log_include_source(theme_entries)  # type: ignore[arg-type]
        headers = ((["Solution"] if include_source else [])
                   + ["Theme", "Description", "Epics"])
        ordered = sorted(theme_entries,
                         key=lambda t: (t[1].theme_id in used, t[0],
                                        t[1].theme_id))
        rows = []
        for source, th in ordered:
            count = epic_count.get(th.theme_id, 0)
            rows.append(([source] if include_source else [])
                        + [f"{th.theme_id}: {th.title}", th.description or "–",
                           str(count) if count
                           else "0 — declared & forgotten"])
        fills = [["white"] * len(rows) for _ in headers]
        fills[-1] = [_OVERDUE_COLOR if not epic_count.get(th.theme_id) else
                     "white" for _, t in ordered]
        blocks.append((headers, rows, fills))

    if epic_entries:
        trains = sorted({e.train for _, e in epic_entries})
        headers = ["Train \\ Horizon"] + list(HORIZONS)
        rows = []
        fills = [["white"] * len(trains) for _ in headers]
        for r, train in enumerate(trains):
            row = [train]
            for c, horizon in enumerate(HORIZONS, start=1):
                cell_epics = [e for _, e in epic_entries
                              if e.train == train and e.horizon == horizon]
                labels = []
                has_zombie = False
                for e in sorted(cell_epics, key=lambda x: x.epic_id):
                    tag = f" [{e.theme}]" if e.theme else " [ZOMBIE]"
                    has_zombie = has_zombie or not e.theme
                    labels.append(f"{e.epic_id}: {e.title}{tag}")
                row.append("<br>".join(labels) if labels else "–")
                if has_zombie:
                    fills[c][r] = _OVERDUE_COLOR
            rows.append(row)
        blocks.append((headers, rows, fills))

    fig = make_subplots(rows=len(blocks), cols=1,
                        specs=[[{"type": "table"}]] * len(blocks))
    for i, (headers, rows, fills) in enumerate(blocks, start=1):
        columns = [[row[c] for row in rows] for c in range(len(headers))]
        fig.add_trace(go.Table(
            header=dict(values=headers, fill_color="#f2f2f2", align="left"),
            cells=dict(values=columns, align="left", fill_color=fills),
        ), row=i, col=1)
    fig.update_layout(
        title=_themes_title(theme_entries, epic_entries,
                            title or t("themes.heading", lang), lang),
        title_font_size=14, margin=dict(t=40, b=10))
    return fig
