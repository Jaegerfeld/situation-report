# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       13.10.2026
# Geändert:       13.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Solution-Area-Register mit Rekurrenz-Signal (Roadmap P5, aus einem
#   Praxis-Workshop). Beleg: „Dynamic solution areas should be rare; if they
#   recur frequently, that signals an organizational or architectural
#   anti-pattern." Ein leichtgewichtiges Register dynamischer Solution Areas
#   (Anlass, beteiligte Teams/Value Streams, Dauer); der Report zeigt die
#   Rekurrenz je Naht — dieselbe Team-Paarung, derselbe Anlass. Wiederholung
#   an derselben Stelle ist ein Frühindikator für ein Value-Stream-Schnitt-
#   oder Architekturproblem (EA-Sicht). Damit wird ein Organisations-
#   Anti-Pattern erstmals gemessen statt behauptet. Owner sind Teams, keine
#   Personen. Schema v1, Standardbibliothek.
# =============================================================================

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

AREAS_SCHEMA_VERSION = 1

AREA_ACTIVE = "active"
AREA_CLOSED = "closed"
AREA_STATUS_ORDER = (AREA_ACTIVE, AREA_CLOSED)

#: Same topic at the same seam this many times: highlighted in the report.
RECURRENCE_HIGHLIGHT = 2
#: ... and from here on it is the EA signal ("check the value-stream cut").
RECURRENCE_SIGNAL = 3


@dataclass
class SolutionArea:
    """
    One dynamic solution area: a temporary collaboration across teams or
    value streams, opened for a reason (``topic`` = short key for grouping,
    ``title`` = the wording). ``participants`` names the seam (at least two
    teams/ARTs/value streams); ``closed_on`` empty = still active.
    """
    area_id: str
    title: str
    topic: str
    participants: list[str] = field(default_factory=list)
    opened_on: date | None = None
    closed_on: date | None = None
    notes: str = ""

    @property
    def status(self) -> str:
        return AREA_CLOSED if self.closed_on else AREA_ACTIVE

    @property
    def seam(self) -> tuple[str, ...]:
        """The seam key: the participants, order-free."""
        return tuple(sorted(self.participants))

    def duration_days(self, reference: date) -> int | None:
        """Days the area ran (to its close, else to the reference date)."""
        if self.opened_on is None:
            return None
        end = self.closed_on or reference
        return max(0, (end - self.opened_on).days)


@dataclass
class SolutionAreaRegister:
    """All solution areas of one solution. An empty register is valid."""
    areas: list[SolutionArea] = field(default_factory=list)


@dataclass
class Seam:
    """All areas between the same participants, with their recurrence."""
    participants: tuple[str, ...]
    areas: list[SolutionArea]
    topics: Counter = field(default_factory=Counter)

    @property
    def count(self) -> int:
        return len(self.areas)

    @property
    def active(self) -> int:
        return sum(1 for a in self.areas if a.status == AREA_ACTIVE)

    @property
    def recurrence(self) -> int:
        """How often the most frequent topic came back at this seam."""
        return max(self.topics.values(), default=0)

    @property
    def recurring_topic(self) -> str:
        return self.topics.most_common(1)[0][0] if self.topics else ""

    @property
    def highlighted(self) -> bool:
        return self.recurrence >= RECURRENCE_HIGHLIGHT

    @property
    def signal(self) -> bool:
        return self.recurrence >= RECURRENCE_SIGNAL

    def total_days(self, reference: date) -> int:
        return sum(d for d in (a.duration_days(reference) for a in self.areas) if d is not None)

    @property
    def last_opened(self) -> date | None:
        opened = [a.opened_on for a in self.areas if a.opened_on is not None]
        return max(opened) if opened else None


def seams(areas: list[SolutionArea]) -> list[Seam]:
    """Group areas by seam; most recurrent first, then most areas, then name."""
    by_seam: dict[tuple[str, ...], Seam] = {}
    for area in areas:
        seam = by_seam.setdefault(area.seam, Seam(area.seam, []))
        seam.areas.append(area)
        seam.topics[area.topic] += 1
    return sorted(by_seam.values(),
                  key=lambda s: (-s.recurrence, -s.count, " × ".join(s.participants)))


def _parse_day(raw: Any, area_id: str, what: str) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw))
    except ValueError as exc:
        raise ValueError(
            f"Solution area '{area_id}': '{what}' must be YYYY-MM-DD (got {raw!r}).") from exc


def parse_solution_areas(data: Any) -> SolutionAreaRegister:
    """
    Build a SolutionAreaRegister from an already-parsed JSON object.

    Raises:
        ValueError: On structural errors — missing list, empty id/title/
                    topic, duplicate id, fewer than two participants, a close
                    before the opening, or a bad date.
    """
    if not isinstance(data, dict):
        raise ValueError("Solution-areas file must be a JSON object.")
    raw = data.get("areas")
    if not isinstance(raw, list):
        raise ValueError("Solution-areas file needs an 'areas' list (may be empty).")
    areas: list[SolutionArea] = []
    seen: set[str] = set()
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValueError(f"Solution area #{i + 1} is not an object.")
        area_id = str(entry.get("id", "")).strip()
        if not area_id:
            raise ValueError(f"Solution area #{i + 1} is missing a non-empty 'id'.")
        if area_id in seen:
            raise ValueError(f"Duplicate solution-area id '{area_id}'.")
        seen.add(area_id)
        title = str(entry.get("title", "")).strip()
        topic = str(entry.get("topic", "")).strip()
        if not title or not topic:
            raise ValueError(
                f"Solution area '{area_id}' needs non-empty 'title' and 'topic' "
                f"(the topic is the key that makes recurrence countable).")
        participants_raw = entry.get("participants", [])
        if not isinstance(participants_raw, list):
            raise ValueError(f"Solution area '{area_id}': 'participants' must be a list.")
        participants = [str(p).strip() for p in participants_raw if str(p).strip()]
        if len(set(participants)) < 2:
            raise ValueError(
                f"Solution area '{area_id}' needs at least two distinct participants — "
                f"a seam has two sides.")
        opened_on = _parse_day(entry.get("opened_on"), area_id, "opened_on")
        closed_on = _parse_day(entry.get("closed_on"), area_id, "closed_on")
        if opened_on and closed_on and closed_on < opened_on:
            raise ValueError(f"Solution area '{area_id}': closed before it was opened.")
        areas.append(SolutionArea(
            area_id=area_id, title=title, topic=topic, participants=participants,
            opened_on=opened_on, closed_on=closed_on,
            notes=str(entry.get("notes", "")).strip()))
    return SolutionAreaRegister(areas=areas)


def load_solution_areas(path: Path) -> SolutionAreaRegister:
    """Read and validate a solution-areas JSON file."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return parse_solution_areas(raw)


def solution_areas_to_dict(register: SolutionAreaRegister) -> dict[str, Any]:
    """Serialise a register back into the schema-v1 JSON shape."""
    out: list[dict[str, Any]] = []
    for a in register.areas:
        entry: dict[str, Any] = {"id": a.area_id, "title": a.title, "topic": a.topic,
                                 "participants": list(a.participants)}
        if a.opened_on is not None:
            entry["opened_on"] = a.opened_on.isoformat()
        if a.closed_on is not None:
            entry["closed_on"] = a.closed_on.isoformat()
        if a.notes:
            entry["notes"] = a.notes
        out.append(entry)
    return {"schema": AREAS_SCHEMA_VERSION, "areas": out}


def save_solution_areas(path: Path, register: SolutionAreaRegister) -> None:
    """Write a SolutionAreaRegister to a JSON file."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(solution_areas_to_dict(register), indent=2, ensure_ascii=False),
                      encoding="utf-8")
