# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Flussproblem-Backlog (Roadmap B6, VSC-1 aus dem Workshop Wolfsburg
#   08/2026): der wichtigste Input der Value-Stream-Konferenz. Jede Solution
#   kann über das optionale "flow_problems"-Feld auf eine
#   flow_problems.json verweisen. Das im Workshop benannte Muster „Risiken
#   werden geloggt, nie mitigiert, tauchen nächstes PI wieder auf" wird
#   messbar: Jedes Problem zählt, in wie vielen Konferenzen es bereits
#   behandelt wurde — offene Probleme ab der dritten Konferenz eskalieren
#   sichtbar. Cross-VS wird nicht behauptet, sondern abgeleitet (mehr als
#   ein betroffener Value Stream). Owner sind Teams, keine Personen.
# =============================================================================

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

FLOW_SCHEMA_VERSION = 1

FLOW_OPEN = "open"
FLOW_COMMITTED = "committed"   # resolution committed at a conference
FLOW_RESOLVED = "resolved"
FLOW_DROPPED = "dropped"       # consciously not pursued (documented)
FLOW_STATUS_ORDER = (FLOW_OPEN, FLOW_COMMITTED, FLOW_RESOLVED, FLOW_DROPPED)

#: An unresolved problem seen in this many conferences escalates visibly.
SURVIVED_CONFERENCES_THRESHOLD = 3


@dataclass
class FlowProblem:
    """
    One flow problem / impediment on the conference backlog.

    ``value_streams`` names the affected value streams or ARTs;
    ``conferences`` counts in how many Value-Stream Conferences the problem
    has been on the table (maintained by people — the tool has no history
    to derive it from). ``resolution_commitment`` records what was promised
    and ``follow_up_pi`` when it comes back to the table.
    """
    problem_id: str
    title: str
    status: str
    value_streams: list[str] = field(default_factory=list)
    source: str = ""                 # who raised it (team/ART/conference)
    owner: str = ""                  # team, never a person
    raised_on: date | None = None
    conferences: int = 1
    resolution_commitment: str = ""
    follow_up_pi: str = ""
    notes: str = ""

    @property
    def cross_vs(self) -> bool:
        """Derived, never asserted: more than one value stream affected."""
        return len(self.value_streams) > 1

    @property
    def survived(self) -> bool:
        """The workshop pattern: unresolved after several conferences."""
        return (self.status in (FLOW_OPEN, FLOW_COMMITTED)
                and self.conferences >= SURVIVED_CONFERENCES_THRESHOLD)


@dataclass
class FlowProblemRegister:
    """All flow problems of one solution. An empty register is valid."""
    problems: list[FlowProblem] = field(default_factory=list)


def parse_flow_problems(data: Any) -> FlowProblemRegister:
    """
    Build a FlowProblemRegister from an already-parsed JSON object.

    Raises:
        ValueError: On structural errors — missing list, empty id/title,
                    duplicate id, unknown status, empty value_streams,
                    bad date, non-positive conference count.
    """
    if not isinstance(data, dict):
        raise ValueError("Flow-problems file must be a JSON object.")
    raw = data.get("problems")
    if not isinstance(raw, list):
        raise ValueError("Flow-problems file needs a 'problems' list "
                         "(may be empty).")

    problems: list[FlowProblem] = []
    seen: set[str] = set()
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValueError(f"Flow problem #{i + 1} is not an object.")
        problem_id = str(entry.get("id", "")).strip()
        if not problem_id:
            raise ValueError(f"Flow problem #{i + 1} is missing a "
                             f"non-empty 'id'.")
        if problem_id in seen:
            raise ValueError(f"Duplicate flow-problem id '{problem_id}'.")
        seen.add(problem_id)

        title = str(entry.get("title", "")).strip()
        if not title:
            raise ValueError(
                f"Flow problem '{problem_id}' is missing a non-empty "
                f"'title'.")

        status = str(entry.get("status", "")).strip().lower()
        if status not in FLOW_STATUS_ORDER:
            raise ValueError(
                f"Flow problem '{problem_id}': unknown status '{status}' — "
                f"expected one of {', '.join(FLOW_STATUS_ORDER)}.")

        streams_raw = entry.get("value_streams", [])
        if not isinstance(streams_raw, list) or not streams_raw:
            raise ValueError(
                f"Flow problem '{problem_id}' needs a non-empty "
                f"'value_streams' list.")
        value_streams = [str(s).strip() for s in streams_raw if str(s).strip()]
        if not value_streams:
            raise ValueError(
                f"Flow problem '{problem_id}' needs a non-empty "
                f"'value_streams' list.")

        raised_raw = entry.get("raised_on")
        try:
            raised_on = (date.fromisoformat(str(raised_raw))
                         if raised_raw else None)
        except ValueError as exc:
            raise ValueError(
                f"Flow problem '{problem_id}': 'raised_on' must be "
                f"YYYY-MM-DD (got '{raised_raw}').") from exc

        try:
            conferences = int(entry.get("conferences", 1))
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Flow problem '{problem_id}': 'conferences' must be an "
                f"integer.") from exc
        if conferences < 1:
            raise ValueError(
                f"Flow problem '{problem_id}': 'conferences' must be >= 1.")

        problems.append(FlowProblem(
            problem_id=problem_id,
            title=title,
            status=status,
            value_streams=value_streams,
            source=str(entry.get("source", "")).strip(),
            owner=str(entry.get("owner", "")).strip(),
            raised_on=raised_on,
            conferences=conferences,
            resolution_commitment=str(
                entry.get("resolution_commitment", "")).strip(),
            follow_up_pi=str(entry.get("follow_up_pi", "")).strip(),
            notes=str(entry.get("notes", "")).strip(),
        ))
    return FlowProblemRegister(problems=problems)


def load_flow_problems(path: Path) -> FlowProblemRegister:
    """Read and validate a flow-problems JSON file."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return parse_flow_problems(raw)


def flow_problems_to_dict(register: FlowProblemRegister) -> dict[str, Any]:
    """Serialise a register back into the schema-v1 JSON shape."""
    out: list[dict[str, Any]] = []
    for p in register.problems:
        entry: dict[str, Any] = {"id": p.problem_id, "title": p.title,
                                 "status": p.status,
                                 "value_streams": list(p.value_streams)}
        if p.source:
            entry["source"] = p.source
        if p.owner:
            entry["owner"] = p.owner
        if p.raised_on is not None:
            entry["raised_on"] = p.raised_on.isoformat()
        if p.conferences != 1:
            entry["conferences"] = p.conferences
        if p.resolution_commitment:
            entry["resolution_commitment"] = p.resolution_commitment
        if p.follow_up_pi:
            entry["follow_up_pi"] = p.follow_up_pi
        if p.notes:
            entry["notes"] = p.notes
        out.append(entry)
    return {"schema": FLOW_SCHEMA_VERSION, "problems": out}


def save_flow_problems(path: Path, register: FlowProblemRegister) -> None:
    """Write a FlowProblemRegister to a JSON file."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(flow_problems_to_dict(register), indent=2,
                   ensure_ascii=False),
        encoding="utf-8")
