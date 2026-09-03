# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Delta-Briefing (Roadmap D2, deterministischer Kern): vergleicht zwei
#   Report-Snapshots und beantwortet „Was hat sich geändert?" — Kennzahl-
#   Deltas je Einheit, Durchsatz im Zeitraum, Konfidenz-Wechsel je Quelle,
#   Zustandsübergänge in den fünf Governance-Registern (neu/entfallen/
#   gewechselt, neu überfällig). Verschlechterungen zuerst. Ausgabe als
#   eigenständige HTML-Seite und als Markdown — Letzteres ist zugleich der
#   künftige Eingabe-Contract der optionalen LLM-Narration (die textet,
#   rechnet aber nicht; alle Zahlen entstehen hier).
# =============================================================================

from __future__ import annotations

import html as _html
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from .snapshot import Snapshot

#: Governance status values that count as a worsening when entered.
_BAD_STATES = {"blocked", "violated", "critical", "invalidated", "owned"}
#: Governance status values that count as an improvement when entered.
_GOOD_STATES = {"done", "met", "in_place", "resolved", "mitigated", "ok",
                "confirmed", "accepted", "on_track"}

_RED = "#f8d7da"
_GREEN = "#e6f4e6"


@dataclass
class FieldChange:
    """One changed field of a matched entry: old → new."""
    entry_id: str
    title: str
    solution: str
    fields: dict[str, tuple[Any, Any]]
    worsened: bool = False


@dataclass
class SectionDelta:
    """Changes of one governance register between two snapshots."""
    added: list[dict[str, Any]] = field(default_factory=list)
    removed: list[dict[str, Any]] = field(default_factory=list)
    changed: list[FieldChange] = field(default_factory=list)
    newly_overdue: list[dict[str, Any]] = field(default_factory=list)

    @property
    def empty(self) -> bool:
        return not (self.added or self.removed or self.changed
                    or self.newly_overdue)


@dataclass
class UnitDelta:
    """Metric changes of one comparison unit (or the pooled total)."""
    label: str
    fields: dict[str, tuple[Any, Any]]


@dataclass
class DeltaReport:
    """The full computed delta between two snapshots."""
    name: str
    as_of_prev: date
    as_of_now: date
    period_days: int
    total: UnitDelta | None
    completed_delta: int
    units: list[UnitDelta] = field(default_factory=list)
    new_units: list[str] = field(default_factory=list)
    removed_units: list[str] = field(default_factory=list)
    confidence_changes: list[FieldChange] = field(default_factory=list)
    governance: dict[str, SectionDelta] = field(default_factory=dict)

    @property
    def quiet(self) -> bool:
        """True when nothing changed at all (a valid, reportable outcome)."""
        return (self.total is None and not self.units and not self.new_units
                and not self.removed_units and not self.confidence_changes
                and all(s.empty for s in self.governance.values()))


#: Unit metric fields compared, with display labels and value formatting.
_METRIC_FIELDS = (
    ("items", "Items"),
    ("completed", "Completed"),
    ("open", "Open (WIP)"),
    ("median_ct", "Median CT (d)"),
    ("p85_ct", "85th % CT (d)"),
    ("target_ct_pct", "≤ target CT (%)"),
    ("median_lt", "Median LT (d)"),
)

#: Metrics where a rising value is a worsening (for direction colouring).
_HIGHER_IS_WORSE = {"open", "median_ct", "p85_ct", "median_lt"}


def _diff_unit(label: str, prev: dict, now: dict) -> UnitDelta | None:
    """
    Field-level diff of one unit's metrics; None when nothing changed.

    Floats are compared at display precision (one decimal) so the briefing
    never reports a change the reader cannot see (e.g. 16.44 → 16.36).
    """
    fields: dict[str, tuple[Any, Any]] = {}
    for key, _lbl in _METRIC_FIELDS:
        old, new = prev.get(key), now.get(key)
        if isinstance(old, float):
            old = round(old, 1)
        if isinstance(new, float):
            new = round(new, 1)
        if old != new:
            fields[key] = (old, new)
    return UnitDelta(label=label, fields=fields) if fields else None


def _status_field(section: str) -> str:
    """The status-carrying field per governance section."""
    return {"risks": "roam", "capabilities": "health"}.get(section, "status")


def _due_field(section: str) -> str | None:
    """The due-date field per governance section (None = no due concept)."""
    return {"dependencies": "due", "runway": "needed_by",
            "decisions": "review_by"}.get(section)


def _is_overdue(section: str, entry: dict, as_of: date) -> bool:
    """Overdue judgement per section, mirroring the report rules."""
    due_key = _due_field(section)
    if not due_key or not entry.get(due_key):
        return False
    due = date.fromisoformat(str(entry[due_key]))
    status = str(entry.get(_status_field(section), ""))
    if section == "dependencies":
        active = status != "done"
    elif section == "runway":
        active = status != "in_place"
    else:  # decisions: only open assumptions expire
        active = entry.get("kind") == "assumption" and status == "open"
    return active and due < as_of


def _key(entry: dict) -> tuple[str, str]:
    """Match key of a governance entry: (solution, id)."""
    return (str(entry.get("solution", "")), str(entry.get("id", "")))


def _diff_section(
    section: str,
    prev: list[dict],
    now: list[dict],
    as_of_prev: date,
    as_of_now: date,
) -> SectionDelta:
    """Diff one governance register between two snapshots."""
    prev_by = {_key(e): e for e in prev}
    now_by = {_key(e): e for e in now}
    delta = SectionDelta()
    status_key = _status_field(section)

    for key, entry in now_by.items():
        if key not in prev_by:
            delta.added.append(entry)
            continue
        old = prev_by[key]
        fields: dict[str, tuple[Any, Any]] = {}
        if old.get(status_key) != entry.get(status_key):
            fields[status_key] = (old.get(status_key), entry.get(status_key))
        if fields:
            new_status = str(entry.get(status_key, "")).lower()
            delta.changed.append(FieldChange(
                entry_id=str(entry.get("id", "")),
                title=str(entry.get("title", "")),
                solution=str(entry.get("solution", "")),
                fields=fields,
                worsened=new_status in _BAD_STATES,
            ))
        if (_is_overdue(section, entry, as_of_now)
                and not _is_overdue(section, old, as_of_prev)):
            delta.newly_overdue.append(entry)

    delta.removed = [e for k, e in prev_by.items() if k not in now_by]
    delta.changed.sort(key=lambda c: (not c.worsened, c.solution, c.entry_id))
    return delta


def compute_delta(prev: Snapshot, now: Snapshot) -> DeltaReport:
    """
    Compute the delta briefing between two snapshots of the same report.

    Args:
        prev: The earlier snapshot.
        now:  The later snapshot.

    Returns:
        A populated DeltaReport (possibly quiet — "nothing changed" is a
        valid, honest result).

    Raises:
        ValueError: When the snapshots belong to different reports or the
                    order is reversed.
    """
    if prev.name != now.name:
        raise ValueError(
            f"Snapshots belong to different reports "
            f"('{prev.name}' vs '{now.name}').")
    if prev.as_of > now.as_of:
        raise ValueError("Snapshot order reversed: prev.as_of is after "
                         "now.as_of — swap the arguments.")

    prev_units = {u["label"]: u for u in prev.units}
    now_units = {u["label"]: u for u in now.units}
    units = [d for label, u in now_units.items()
             if label in prev_units
             and (d := _diff_unit(label, prev_units[label], u))]

    prev_conf = {s["label"]: s for s in prev.sources}
    confidence_changes = []
    for s in now.sources:
        old = prev_conf.get(s["label"])
        if old and old.get("confidence") != s.get("confidence"):
            order = {"low": 0, "medium": 1, "high": 2}
            confidence_changes.append(FieldChange(
                entry_id=s["label"], title="", solution="",
                fields={"confidence": (old.get("confidence"),
                                       s.get("confidence"))},
                worsened=order.get(str(s.get("confidence")), 1)
                < order.get(str(old.get("confidence")), 1),
            ))
    confidence_changes.sort(key=lambda c: (not c.worsened, c.entry_id))

    governance = {
        section: _diff_section(
            section, prev.governance.get(section, []),
            now.governance.get(section, []), prev.as_of, now.as_of)
        for section in ("risks", "dependencies", "nfr", "runway",
                        "capabilities", "decisions")
    }

    completed_delta = (int(now.total.get("completed", 0))
                       - int(prev.total.get("completed", 0)))
    return DeltaReport(
        name=now.name,
        as_of_prev=prev.as_of,
        as_of_now=now.as_of,
        period_days=(now.as_of - prev.as_of).days,
        total=_diff_unit(now.name, prev.total, now.total),
        completed_delta=completed_delta,
        units=units,
        new_units=[lbl for lbl in now_units if lbl not in prev_units],
        removed_units=[lbl for lbl in prev_units if lbl not in now_units],
        confidence_changes=confidence_changes,
        governance=governance,
    )


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

_SECTION_TITLES = {
    "risks": "ROAM risks",
    "dependencies": "Dependencies",
    "nfr": "NFRs",
    "runway": "Architecture runway",
    "capabilities": "Capabilities",
    "decisions": "Decisions & assumptions",
}


def _fmt(value: Any) -> str:
    """Human formatting for metric values (None → –, floats → 1 decimal)."""
    if value is None:
        return "–"
    if isinstance(value, float):
        return f"{value:.1f}"
    return str(value)


def _arrow(key: str, old: Any, new: Any) -> tuple[str, str]:
    """Direction arrow and colour for one metric change."""
    if not (isinstance(old, (int, float)) and isinstance(new, (int, float))):
        return "→", ""
    up = new > old
    arrow = "▲" if up else "▼"
    worse = up if key in _HIGHER_IS_WORSE else not up
    if key in ("items", "completed"):
        return arrow, ""  # volume changes are neutral
    return arrow, (_RED if worse else _GREEN)


def _unit_rows_html(deltas: list[UnitDelta]) -> str:
    rows = ""
    for d in deltas:
        for key, label in _METRIC_FIELDS:
            if key not in d.fields:
                continue
            old, new = d.fields[key]
            arrow, color = _arrow(key, old, new)
            style = f" style='background:{color};font-weight:600'" if color else ""
            rows += (f"<tr><td>{_html.escape(d.label)}</td>"
                     f"<td>{_html.escape(label)}</td>"
                     f"<td>{_fmt(old)}</td><td{style}>{arrow} {_fmt(new)}</td></tr>")
    return rows


def _entry_line(entry: dict) -> str:
    src = entry.get("solution", "")
    prefix = f"[{src}] " if src else ""
    return f"{prefix}{entry.get('id', '')}: {entry.get('title', '')}"


def render_delta_html(delta: DeltaReport) -> str:
    """
    Render the delta briefing as a self-contained HTML page.

    Sections appear only when they carry changes; worsenings are highlighted
    red, improvements green. A quiet delta renders an explicit "no changes"
    page — silence is information.
    """
    head = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>Delta Briefing — {_html.escape(delta.name)}</title>"
        "<style>"
        "body{font-family:'Segoe UI',Arial,sans-serif;margin:24px;color:#222;}"
        "h1{font-size:1.4rem;} h2{font-size:1.1rem;margin-top:24px;}"
        "p.meta{color:#555;}"
        "table.sr-summary{border-collapse:collapse;margin:8px 0 24px 0;font-size:0.95rem;}"
        "table.sr-summary th,table.sr-summary td{"
        "border:1px solid #d0d0d0;padding:4px 12px;text-align:left;}"
        "table.sr-summary th{background:#f2f2f2;}"
        "li.worse{background:" + _RED + ";} li.better{background:" + _GREEN + ";}"
        "ul.delta li{margin:2px 0;padding:2px 6px;}"
        "</style></head><body>"
    )
    title = (f"<h1>Delta Briefing — {_html.escape(delta.name)}</h1>"
             f"<p class='meta'>{delta.as_of_prev.isoformat()} → "
             f"{delta.as_of_now.isoformat()} ({delta.period_days} days); "
             f"{delta.completed_delta:+d} items completed in the period.</p>")

    if delta.quiet:
        return (head + title
                + "<p><b>No changes</b> between the two snapshots.</p>"
                + "</body></html>")

    body = ""
    metric_deltas = ([delta.total] if delta.total else []) + delta.units
    if metric_deltas:
        body += ("<h2>Metrics</h2><table class='sr-summary'>"
                 "<tr><th>Unit</th><th>Metric</th><th>Before</th><th>Now</th></tr>"
                 + _unit_rows_html(metric_deltas) + "</table>")
    if delta.new_units or delta.removed_units:
        body += "<h2>Units</h2><ul class='delta'>"
        body += "".join(f"<li>new: {_html.escape(u)}</li>"
                        for u in delta.new_units)
        body += "".join(f"<li>removed: {_html.escape(u)}</li>"
                        for u in delta.removed_units)
        body += "</ul>"

    if delta.confidence_changes:
        body += "<h2>Data confidence</h2><ul class='delta'>"
        for c in delta.confidence_changes:
            old, new = c.fields["confidence"]
            cls = "worse" if c.worsened else "better"
            body += (f"<li class='{cls}'>{_html.escape(c.entry_id)}: "
                     f"{_html.escape(str(old))} → <b>{_html.escape(str(new))}</b></li>")
        body += "</ul>"

    for section, sd in delta.governance.items():
        if sd.empty:
            continue
        body += f"<h2>{_SECTION_TITLES[section]}</h2><ul class='delta'>"
        status_key = _status_field(section)
        for c in sd.changed:
            old, new = c.fields[status_key]
            cls = "worse" if c.worsened else "better"
            label = _entry_line({"solution": c.solution, "id": c.entry_id,
                                 "title": c.title})
            body += (f"<li class='{cls}'>{_html.escape(label)} — "
                     f"{_html.escape(str(old))} → <b>{_html.escape(str(new))}</b></li>")
        for e in sd.newly_overdue:
            body += (f"<li class='worse'>newly overdue: "
                     f"{_html.escape(_entry_line(e))}</li>")
        for e in sd.added:
            body += f"<li>new: {_html.escape(_entry_line(e))}</li>"
        for e in sd.removed:
            body += f"<li>removed: {_html.escape(_entry_line(e))}</li>"
        body += "</ul>"

    return head + title + body + "</body></html>"


def delta_to_markdown(delta: DeltaReport) -> str:
    """
    Render the delta briefing as compact Markdown.

    This is the human-readable text form and, deliberately, the input
    contract for the optional LLM narration layer (D2 part 2): the LLM may
    rephrase this content, never add numbers to it.
    """
    lines = [
        f"# Delta Briefing — {delta.name}",
        f"{delta.as_of_prev.isoformat()} → {delta.as_of_now.isoformat()} "
        f"({delta.period_days} days); {delta.completed_delta:+d} items "
        f"completed in the period.",
        "",
    ]
    if delta.quiet:
        lines.append("No changes between the two snapshots.")
        return "\n".join(lines)

    metric_deltas = ([delta.total] if delta.total else []) + delta.units
    if metric_deltas:
        lines.append("## Metrics")
        for d in metric_deltas:
            for key, label in _METRIC_FIELDS:
                if key in d.fields:
                    old, new = d.fields[key]
                    lines.append(f"- {d.label} — {label}: "
                                 f"{_fmt(old)} → {_fmt(new)}")
        lines.append("")
    for u in delta.new_units:
        lines.append(f"- new unit: {u}")
    for u in delta.removed_units:
        lines.append(f"- removed unit: {u}")

    if delta.confidence_changes:
        lines.append("## Data confidence")
        for c in delta.confidence_changes:
            old, new = c.fields["confidence"]
            lines.append(f"- {c.entry_id}: {old} → {new}")
        lines.append("")

    for section, sd in delta.governance.items():
        lines.extend(_section_markdown(section, sd))
    return "\n".join(lines).rstrip() + "\n"


def _section_markdown(section: str, sd: SectionDelta) -> list[str]:
    """Markdown lines for one governance section (empty section → none)."""
    if sd.empty:
        return []
    lines = [f"## {_SECTION_TITLES[section]}"]
    status_key = _status_field(section)
    for c in sd.changed:
        old, new = c.fields[status_key]
        src = f"[{c.solution}] " if c.solution else ""
        lines.append(f"- {src}{c.entry_id}: {c.title} — {old} → {new}")
    lines.extend(f"- newly overdue: {_entry_line(e)}" for e in sd.newly_overdue)
    lines.extend(f"- new: {_entry_line(e)}" for e in sd.added)
    lines.extend(f"- removed: {_entry_line(e)}" for e in sd.removed)
    lines.append("")
    return lines
