# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       05.09.2026
# Geändert:       05.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Entscheidungspunkt-Wecker (P4, Workshop Wolfsburg 08/2026; Muster M4 der
#   KI-Denkschrift): misst den Druck aus offenen Abhängigkeiten ZWISCHEN
#   Value Streams und meldet, wenn eine im Ritual vereinbarte Schwelle
#   überschritten ist — „Schwelle überschritten, Value-Stream-Conference
#   einberufen?“
#
#   Damit wird die Doktrin „do it when you need it“ operationalisierbar
#   statt kalendergetrieben (Workshop-Beleg: „Trigger it when there are
#   significant cross-value-stream dependencies; skip it when there aren't.“)
#
#   Drei Entscheidungen, die den Wecker leise halten (gegen Alarm-Müdigkeit):
#
#   1. NUR portfolio-interne Nähte wecken. Eine Abhängigkeit auf einen
#      Lieferanten oder ein Fremdsystem ist realer Druck — aber eine
#      Value-Stream-Conference kann darüber nicht entscheiden, weil der
#      Adressat nicht im Raum sitzt. Extern wird ausgewiesen, zählt aber
#      nicht in den Wecker.
#   2. OHNE vereinbarte Schwelle kein Alarm. Das Werkzeug erfindet keinen
#      Schwellenwert; es zeigt den Wert und sagt, dass noch keine Schwelle
#      vereinbart ist. Die Schwelle gehört ins Ritual, nicht in einen
#      Vorgabewert.
#   3. Unterschwellig wird SICHTBAR gemeldet, nicht weggelassen. Ein
#      Indikator, der nur bei schlechten Werten erscheint, lehrt seine Leser,
#      Abwesenheit als „nicht gerechnet“ zu deuten (gleiche Regel wie das
#      ausdrückliche „No changes“ des Delta-Briefings).
#
#   Bewusst NICHT im Modell: eine eigene Kritikalität und ein Erfassungsdatum.
#   Der Status IST das menschliche Kritikalitätsurteil (Hausregel „Status
#   pflegen Menschen, das Werkzeug rechnet nicht“) — ein zweites Severity-Feld
#   auf derselben Zeile könnte ihm widersprechen. Und Druck entsteht nicht
#   durch Alter an sich, sondern durch Überschreiten des vereinbarten Termins:
#   eine vor 90 Tagen erfasste Abhängigkeit, die erst nächstes Quartal fällig
#   ist, drückt niemanden. Gewichtet wird darum Status × Überfälligkeit.
# =============================================================================

from __future__ import annotations

import html as _html
from dataclasses import dataclass, field
from datetime import date

from .dependency_config import (
    DEP_AT_RISK,
    DEP_BLOCKED,
    DEP_DONE,
    DEP_ON_TRACK,
    Dependency,
)

#: Gewicht je Status — der Status ist das gepflegte Kritikalitätsurteil.
STATUS_WEIGHT: dict[str, int] = {
    DEP_BLOCKED: 3,
    DEP_AT_RISK: 2,
    DEP_ON_TRACK: 1,
}

#: Ab so vielen Tagen Überfälligkeit verdoppelt bzw. verdreifacht sich das
#: Gewicht. Ganzzahlige Stufen, damit ein Mensch den Wert nachrechnen kann.
OVERDUE_DOUBLE_AFTER_DAYS = 1
OVERDUE_TRIPLE_AFTER_DAYS = 30

#: Einordnung einer Abhängigkeit relativ zur eigenen Solution.
SCOPE_INTERNAL = "internal"      # innerhalb der eigenen Solution
SCOPE_CROSS_VS = "cross_vs"      # Ziel gehört einer anderen Solution des Portfolios
SCOPE_EXTERNAL = "external"      # Ziel gehört zu keiner Solution des Portfolios


@dataclass
class PressureItem:
    """One open cross-value-stream dependency and what it contributes."""
    source: str
    dependency: Dependency
    target_solution: str
    overdue_days: int
    weight: int


@dataclass
class DependencyPressure:
    """
    The decision-point indicator for one report run.

    ``threshold`` is None when no threshold has been agreed yet — the
    indicator is then reported without ever raising an alarm.
    """
    value: int = 0
    items: list[PressureItem] = field(default_factory=list)
    external_open: int = 0
    threshold: int | None = None
    applicable: bool = True

    @property
    def triggered(self) -> bool:
        """True only when a threshold was agreed AND is reached."""
        return self.threshold is not None and self.value >= self.threshold


def overdue_days(dep: Dependency, reference: date) -> int:
    """Days past the agreed date; 0 when not due, not dated, or done."""
    if dep.status == DEP_DONE or dep.due is None or dep.due >= reference:
        return 0
    return (reference - dep.due).days


def overdue_factor(days: int) -> int:
    """1 while on time, 2 once overdue, 3 beyond a month overdue."""
    if days >= OVERDUE_TRIPLE_AFTER_DAYS:
        return 3
    if days >= OVERDUE_DOUBLE_AFTER_DAYS:
        return 2
    return 1


def classify(
    source: str,
    dep: Dependency,
    arts_by_solution: dict[str, set[str]],
) -> tuple[str, str]:
    """
    Locate a dependency's target: own solution, a sibling solution, or outside.

    Derived from the configuration, never asserted in the register — the same
    rule B6 uses for its cross-value-stream flag. The register deliberately
    does not validate its 'to' side, so an unknown target simply means the
    dependency leaves the portfolio.

    Args:
        source:           Name of the solution owning the dependency.
        dep:              The dependency.
        arts_by_solution: ART names per solution name.

    Returns:
        (scope, target solution name) — the name is "" for external targets.
    """
    if dep.to_art in arts_by_solution.get(source, set()):
        return SCOPE_INTERNAL, source
    for solution, arts in arts_by_solution.items():
        if solution != source and dep.to_art in arts:
            return SCOPE_CROSS_VS, solution
    return SCOPE_EXTERNAL, ""


def compute_pressure(
    entries: list[tuple[str, Dependency]],
    arts_by_solution: dict[str, set[str]],
    threshold: int | None = None,
    reference: date | None = None,
) -> DependencyPressure:
    """
    Compute the cross-value-stream dependency pressure.

    pressure = Σ (status weight × overdue factor) over all OPEN dependencies
    whose target belongs to another solution of the same portfolio. Done
    dependencies exert no pressure; external targets are counted separately
    (a Value Stream Conference cannot decide about a vendor).

    The indicator needs sibling solutions to mean anything: with fewer than
    two known solutions there is no seam between value streams, and the
    result is marked as not applicable rather than reported as a
    reassuring zero.

    Args:
        entries:          (source label, Dependency) pairs, as collected for the report.
        arts_by_solution: ART names per solution name.
        threshold:        Agreed alarm threshold; None = report only, never alarm.
        reference:        Overdue reference date (default: today) — injectable for tests.

    Returns:
        The indicator, its contributing items (heaviest first) and the verdict.
    """
    reference = reference or date.today()
    if len(arts_by_solution) < 2:
        return DependencyPressure(threshold=threshold, applicable=False)

    items: list[PressureItem] = []
    external_open = 0
    for source, dep in entries:
        if dep.status == DEP_DONE:
            continue
        scope, target = classify(source, dep, arts_by_solution)
        if scope == SCOPE_EXTERNAL:
            external_open += 1
            continue
        if scope == SCOPE_INTERNAL:
            continue
        days = overdue_days(dep, reference)
        weight = STATUS_WEIGHT.get(dep.status, 1) * overdue_factor(days)
        items.append(PressureItem(source, dep, target, days, weight))

    items.sort(key=lambda i: (-i.weight, -i.overdue_days, i.dependency.dep_id))
    return DependencyPressure(
        value=sum(i.weight for i in items),
        items=items,
        external_open=external_open,
        threshold=threshold,
    )


def _verdict_line(pressure: DependencyPressure) -> tuple[str, str]:
    """The headline sentence and its colour — the whole point of the feature."""
    if not pressure.applicable:
        return ("Only meaningful across value streams — this configuration "
                "knows a single solution.", "#666666")
    if pressure.threshold is None:
        return (f"Pressure {pressure.value}. No threshold agreed yet — "
                f"reporting only, no alarm.", "#666666")
    if pressure.triggered:
        return (f"Pressure {pressure.value} of {pressure.threshold} — "
                f"threshold reached. Convene a Value Stream Conference?",
                "#c0392b")
    return (f"Pressure {pressure.value} of {pressure.threshold} — "
            f"below threshold.", "#2e7d32")


def render_decision_point_html(
    pressure: DependencyPressure,
    title: str = "Decision Point — Cross-Value-Stream Dependency Pressure",
) -> str:
    """
    Render the decision-point block as a self-contained HTML fragment.

    Always renders when dependencies were collected — below threshold and
    "no threshold agreed" are stated out loud, so a missing block never gets
    read as "nothing to worry about".

    Args:
        pressure: The computed indicator.
        title:    Heading shown above the block.

    Returns:
        An HTML fragment (heading, verdict, contributing table).
    """
    verdict, colour = _verdict_line(pressure)
    head = (
        f"<h2 class='metric-heading'>{_html.escape(title)}</h2>"
        f"<p style='font-size:1.05rem;font-weight:600;color:{colour};"
        f"margin:4px 0 10px 0'>{_html.escape(verdict)}</p>"
    )
    if not pressure.applicable:
        return head

    note = ""
    if pressure.external_open:
        note = (f"<p style='color:#555;margin:0 0 10px 0'>"
                f"{pressure.external_open} further open dependencies point "
                f"outside the portfolio (vendors, external systems). They are "
                f"real pressure, but no conference of these value streams can "
                f"decide about them — they are excluded from the indicator."
                f"</p>")
    if not pressure.items:
        return head + note + (
            "<p style='color:#555'>No open dependencies between the value "
            "streams of this portfolio.</p>")

    rows = ""
    for item in pressure.items:
        dep = item.dependency
        overdue = f"{item.overdue_days} d" if item.overdue_days else "—"
        due = dep.due.isoformat() if dep.due else "—"
        rows += (
            f"<tr><td>{_html.escape(dep.dep_id)}</td>"
            f"<td>{_html.escape(dep.title)}</td>"
            f"<td>{_html.escape(item.source)} · {_html.escape(dep.from_art)}</td>"
            f"<td>{_html.escape(item.target_solution)} · "
            f"{_html.escape(dep.to_art)}</td>"
            f"<td>{_html.escape(dep.status)}</td>"
            f"<td>{due}</td><td>{overdue}</td>"
            f"<td style='font-weight:600'>{item.weight}</td></tr>")

    style = (
        "<style>"
        "table.sr-decision{border-collapse:collapse;margin:8px 0 24px 0;"
        "font-size:0.95rem;}"
        "table.sr-decision th,table.sr-decision td{border:1px solid #d0d0d0;"
        "padding:4px 12px;text-align:left;}"
        "table.sr-decision th{background:#f2f2f2;}"
        "table.sr-decision td:last-child,table.sr-decision th:last-child{"
        "text-align:right;}"
        "</style>")
    header = ("<tr><th>ID</th><th>Dependency</th><th>Needs (from)</th>"
              "<th>Delivers (to)</th><th>Status</th><th>Due</th>"
              "<th>Overdue</th><th>Weight</th></tr>")
    return (head + note + style
            + f"<table class='sr-decision'>{header}{rows}</table>")


def decision_point_figure(
    pressure: DependencyPressure,
    title: str = "Decision Point — Cross-Value-Stream Dependency Pressure",
):
    """
    Render the decision-point block as a plotly table figure (PDF path).

    Mirrors render_decision_point_html(): the verdict is the figure title, so
    a reader sees it without reading the table; the contributing dependencies
    follow, heaviest first.

    Args:
        pressure: The computed indicator.
        title:    Base title; the verdict is appended.

    Returns:
        A plotly Figure.
    """
    import plotly.graph_objects as go

    verdict, colour = _verdict_line(pressure)
    headers = ["ID", "Dependency", "Needs (from)", "Delivers (to)",
               "Status", "Due", "Overdue", "Weight"]
    rows = [[
        item.dependency.dep_id,
        item.dependency.title,
        f"{item.source} · {item.dependency.from_art}",
        f"{item.target_solution} · {item.dependency.to_art}",
        item.dependency.status,
        item.dependency.due.isoformat() if item.dependency.due else "–",
        f"{item.overdue_days} d" if item.overdue_days else "–",
        str(item.weight),
    ] for item in pressure.items]

    columns = [[row[c] for row in rows] for c in range(len(headers))]
    fig = go.Figure(data=[go.Table(
        header=dict(values=headers, fill_color="#f2f2f2", align="left"),
        cells=dict(values=columns, align="left"),
    )])
    fig.update_layout(title=f"{title} — {verdict}", title_font_size=14,
                      title_font_color=colour, margin=dict(t=60, b=10))
    return fig
