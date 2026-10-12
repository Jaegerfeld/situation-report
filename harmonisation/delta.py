# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       12.10.2026
# Geändert:       12.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Veränderung zweier Bewertungsstände (P3 Schritt 2, nach dem Muster des
#   Delta-Briefings D2): „Was hat sich seit der letzten Bewertung geändert?"
#   Der frühere Stand ist entweder ein zweiter Arbeitsbereich oder derselbe
#   Arbeitsbereich zu einem Stichtag — Bewertungen sind datiert, darum lässt
#   sich der Stand von damals aus den heutigen Dateien zurückrechnen. Verglichen
#   werden je Prozess und Dimension Score, Konfidenz, Spanne und Zahl der
#   Bewertungen, dazu neue Bewertungen, Entscheidungen des Boards und
#   hinzugekommene oder entfallene Prozesse. Ein Score, der sinkt, ist keine
#   Verschlechterung — er ist ein anderer Befund; darum ordnet dieser Diff
#   nichts nach gut und schlecht, sondern nach Prozess. „Keine Änderungen" wird
#   ausdrücklich gesagt. Das Markdown ist zugleich der Eingabe-Contract der
#   optionalen KI-Lesart: alle Zahlen entstehen hier.
# =============================================================================

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .model import Decision, Workspace
from .score import CellSummary, matrix


@dataclass(frozen=True)
class CellChange:
    """One matrix cell whose summary differs between the two states."""
    process: str
    dimension: str
    score: tuple[float | None, float | None]
    confidence: tuple[str, str]
    spread: tuple[float | None, float | None]
    assessments: tuple[int, int]

    @property
    def score_changed(self) -> bool:
        return self.score[0] != self.score[1]

    @property
    def confidence_changed(self) -> bool:
        return self.confidence[0] != self.confidence[1]


@dataclass(frozen=True)
class DecisionChange:
    """A board decision that is new or differs between the two states."""
    process: str
    old: Decision | None
    new: Decision | None


@dataclass(frozen=True)
class NewAssessment:
    """An assessment present only in the later state — date, never a name."""
    process: str
    day: date


@dataclass
class HarmonisationDelta:
    """Everything that differs between an earlier and a later state."""
    label_prev: str
    label_now: str
    cells: list[CellChange] = field(default_factory=list)
    new_assessments: list[NewAssessment] = field(default_factory=list)
    decisions: list[DecisionChange] = field(default_factory=list)
    added_processes: list[str] = field(default_factory=list)
    removed_processes: list[str] = field(default_factory=list)
    catalogue_changed: bool = False
    undated_decisions: int = 0

    @property
    def quiet(self) -> bool:
        """True when nothing changed — a valid, reportable outcome."""
        return not (self.cells or self.new_assessments or self.decisions
                    or self.added_processes or self.removed_processes
                    or self.catalogue_changed)


def filter_as_of(ws: Workspace, day: date) -> Workspace:
    """
    The workspace as it stood on ``day``.

    Assessments are dated, so the earlier state is the set of assessments
    up to and including that day. Decisions with a date follow the same
    rule; an undated decision cannot be placed in time and is kept in both
    states (the delta counts them so the reader knows). Catalogue and
    processes carry no date and are taken as they are.
    """
    assessments = tuple(a for a in ws.assessments if a.day <= day)
    decisions = {pid: d for pid, d in ws.decisions.items()
                 if d.day is None or d.day <= day}
    return Workspace(ws.catalogue, ws.processes, assessments, decisions, ws.root)


def _cell_pair(prev: CellSummary | None, now: CellSummary | None) -> tuple:
    def val(c: CellSummary | None):
        if c is None:
            return (None, "", None, 0)
        return (c.score, c.confidence, c.spread, c.assessments)
    return val(prev), val(now)


def _same_decision(a: Decision | None, b: Decision | None) -> bool:
    if a is None or b is None:
        return a is b
    return (a.decision, a.depth, a.day, a.body) == (b.decision, b.depth, b.day, b.body)


def compute_delta(prev: Workspace, now: Workspace,
                  label_prev: str, label_now: str) -> HarmonisationDelta:
    """
    Diff two workspace states. Processes are matched by id, cells by
    process and dimension; only processes present in both states yield
    cell changes — a new process is reported as such, not as 'changed from
    nothing'.
    """
    delta = HarmonisationDelta(label_prev=label_prev, label_now=label_now)
    prev_ids = [p.id for p in prev.processes]
    now_ids = [p.id for p in now.processes]
    delta.added_processes = [now.process(pid).name for pid in now_ids if pid not in prev_ids]
    delta.removed_processes = [prev.process(pid).name for pid in prev_ids if pid not in now_ids]
    delta.catalogue_changed = prev.catalogue.question_ids != now.catalogue.question_ids

    prev_cells = matrix(prev)
    now_cells = matrix(now)
    for pid in now_ids:
        if pid not in prev_ids:
            continue
        for dim in now.catalogue.dimensions:
            p, n = _cell_pair(prev_cells.get(pid, {}).get(dim.id), now_cells[pid].get(dim.id))
            if p == n:
                continue
            delta.cells.append(CellChange(
                process=pid, dimension=dim.id,
                score=(p[0], n[0]), confidence=(p[1], n[1]),
                spread=(p[2], n[2]), assessments=(p[3], n[3])))

    prev_keys = {(a.process, a.day, a.assessor) for a in prev.assessments}
    delta.new_assessments = sorted(
        (NewAssessment(a.process, a.day) for a in now.assessments
         if (a.process, a.day, a.assessor) not in prev_keys and a.process in prev_ids),
        key=lambda n: (now_ids.index(n.process), n.day))

    for pid in now_ids:
        if pid not in prev_ids:
            continue
        old, new = prev.decisions.get(pid), now.decisions.get(pid)
        if not _same_decision(old, new):
            delta.decisions.append(DecisionChange(pid, old, new))
    delta.undated_decisions = sum(1 for d in now.decisions.values() if d.day is None)
    return delta


# ---------------------------------------------------------------------------
# Markdown — der Eingabe-Contract der KI-Lesart (englisch beschriftet,
# Prozesse und Dimensionen, nie Personen)
# ---------------------------------------------------------------------------

def _num(value: float | None) -> str:
    return "none" if value is None else f"{value:g}"


def delta_to_markdown(delta: HarmonisationDelta, now: Workspace) -> str:
    """The deterministic change contract. Every number the reading may use is here."""
    lines = [
        f"# Harmonisation delta - {now.catalogue.name}",
        f"Earlier state: {delta.label_prev}; later state: {delta.label_now}.",
        "Scores are 0-100 per dimension; a lower score is a different finding, not a worsening.",
        "",
    ]
    if delta.quiet:
        lines.append("No changes between the two states.")
        return "\n".join(lines)
    if delta.catalogue_changed:
        lines += ["WARNING: the question catalogue differs between the states; "
                  "scores are not comparable.", ""]
    if delta.cells:
        lines.append("## Changed cells")
        for c in delta.cells:
            dim = _dimension_label(now, c.dimension, "en")
            lines.append(
                f"- {now.process(c.process).name} / {dim}: score {_num(c.score[0])} -> "
                f"{_num(c.score[1])}, confidence {c.confidence[0] or 'none'} -> "
                f"{c.confidence[1] or 'none'}, spread {_num(c.spread[0])} -> "
                f"{_num(c.spread[1])}, assessments {c.assessments[0]} -> {c.assessments[1]}")
        lines.append("")
    if delta.new_assessments:
        lines.append("## New assessments")
        for n in delta.new_assessments:
            lines.append(f"- {now.process(n.process).name}: assessment dated {n.day.isoformat()}")
        lines.append("")
    if delta.decisions:
        lines.append("## Board decisions")
        for d in delta.decisions:
            lines.append(f"- {now.process(d.process).name}: {_decision_text(d.old)} -> "
                         f"{_decision_text(d.new)}")
        lines.append("")
    if delta.added_processes:
        lines.append("## Processes added")
        lines += [f"- {name}" for name in delta.added_processes]
        lines.append("")
    if delta.removed_processes:
        lines.append("## Processes removed")
        lines += [f"- {name}" for name in delta.removed_processes]
        lines.append("")
    if delta.undated_decisions:
        lines.append(f"Note: {delta.undated_decisions} board decision(s) carry no date and "
                     f"count as present in both states.")
    return "\n".join(lines).rstrip() + "\n"


def _dimension_label(ws: Workspace, dimension_id: str, lang: str) -> str:
    for d in ws.catalogue.dimensions:
        if d.id == dimension_id:
            return d.label(lang)
    return dimension_id


def _decision_text(d: Decision | None) -> str:
    if d is None:
        return "open"
    text = d.decision
    if d.depth:
        text += f' (depth: "{d.depth}")'
    if d.day:
        text += f" on {d.day.isoformat()}"
    return text
