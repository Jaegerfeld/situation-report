# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       02.09.2026
# Geändert:       02.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Liest und validiert ein Decision-/Assumption-Log (Roadmap B4) — ADR-artig,
#   bewusst leichtgewichtig. Jede Solution kann über das optionale
#   "decisions"-Feld ihrer Konfiguration auf eine decisions.json verweisen;
#   der Report rendert daraus die Log-Tabelle. Entscheidungen machen die
#   Trade-off-Disziplin sichtbar (proposed/accepted/superseded); Annahmen
#   tragen ein Prüfdatum (review_by) und werden überfällig, wenn es
#   verstreicht, solange sie offen sind — der Anschlusspunkt für
#   Red-Team/Premortem. Owner sind Teams, keine Personen.
# =============================================================================

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

DECISION_SCHEMA_VERSION = 1

KIND_DECISION = "decision"
KIND_ASSUMPTION = "assumption"

DECISION_PROPOSED = "proposed"
DECISION_ACCEPTED = "accepted"
DECISION_SUPERSEDED = "superseded"
#: Valid statuses for kind="decision" (the classic lightweight ADR set).
DECISION_STATUSES = (DECISION_PROPOSED, DECISION_ACCEPTED, DECISION_SUPERSEDED)

ASSUMPTION_OPEN = "open"
ASSUMPTION_CONFIRMED = "confirmed"
ASSUMPTION_INVALIDATED = "invalidated"
#: Valid statuses for kind="assumption".
ASSUMPTION_STATUSES = (ASSUMPTION_OPEN, ASSUMPTION_CONFIRMED,
                       ASSUMPTION_INVALIDATED)


@dataclass
class LogEntry:
    """
    One entry of the decision/assumption log.

    ``kind`` is "decision" or "assumption"; the valid ``status`` values depend
    on it (proposed/accepted/superseded vs. open/confirmed/invalidated).
    ``review_by`` gives an assumption its expiry: an open assumption whose
    review date has passed renders as due for review. ``supersedes`` may name
    the id of an earlier entry in the same log (validated). ``owner`` names a
    team, not a person.
    """
    entry_id: str
    kind: str
    title: str
    status: str
    owner: str = ""
    logged_on: date | None = None
    review_by: date | None = None
    supersedes: str = ""
    notes: str = ""


@dataclass
class DecisionLog:
    """All decisions and assumptions of one solution. Empty is valid."""
    entries: list[LogEntry] = field(default_factory=list)


def _parse_date_field(value: Any, entry_id: str, name: str) -> date | None:
    """Parse an optional ISO date field of one entry."""
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError(
            f"Entry '{entry_id}': '{name}' must be YYYY-MM-DD "
            f"(got '{value}').") from exc


def parse_decisions(data: Any) -> DecisionLog:
    """
    Build a DecisionLog from an already-parsed JSON object.

    Separated from file reading so it can be unit-tested without touching disk.

    Args:
        data: Parsed JSON object ({"entries": [...]}).

    Returns:
        Validated DecisionLog (kind/status values normalised to lower case).

    Raises:
        ValueError: On structural errors — missing list, empty id/title,
                    duplicate id, unknown kind, status not valid for the
                    kind, unparsable dates, supersedes pointing to a
                    non-existent entry.
    """
    if not isinstance(data, dict):
        raise ValueError("Decisions file must be a JSON object.")
    raw = data.get("entries")
    if not isinstance(raw, list):
        raise ValueError("Decisions file needs an 'entries' list "
                         "(may be empty).")

    entries: list[LogEntry] = []
    seen: set[str] = set()
    for i, e in enumerate(raw):
        if not isinstance(e, dict):
            raise ValueError(f"Entry #{i + 1} is not an object.")
        entry_id = str(e.get("id", "")).strip()
        if not entry_id:
            raise ValueError(f"Entry #{i + 1} is missing a non-empty 'id'.")
        if entry_id in seen:
            raise ValueError(f"Duplicate entry id '{entry_id}'.")
        seen.add(entry_id)

        title = str(e.get("title", "")).strip()
        if not title:
            raise ValueError(f"Entry '{entry_id}' is missing a non-empty 'title'.")

        kind = str(e.get("kind", "")).strip().lower()
        if kind not in (KIND_DECISION, KIND_ASSUMPTION):
            raise ValueError(
                f"Entry '{entry_id}': unknown kind '{kind}' — expected "
                f"'{KIND_DECISION}' or '{KIND_ASSUMPTION}'.")

        status = str(e.get("status", "")).strip().lower()
        valid = DECISION_STATUSES if kind == KIND_DECISION else ASSUMPTION_STATUSES
        if status not in valid:
            raise ValueError(
                f"Entry '{entry_id}': status '{status}' is not valid for a "
                f"{kind} — expected one of {', '.join(valid)}.")

        entries.append(LogEntry(
            entry_id=entry_id,
            kind=kind,
            title=title,
            status=status,
            owner=str(e.get("owner", "")).strip(),
            logged_on=_parse_date_field(e.get("logged_on"), entry_id, "logged_on"),
            review_by=_parse_date_field(e.get("review_by"), entry_id, "review_by"),
            supersedes=str(e.get("supersedes", "")).strip(),
            notes=str(e.get("notes", "")).strip(),
        ))

    ids = {entry.entry_id for entry in entries}
    for entry in entries:
        if entry.supersedes and entry.supersedes not in ids:
            raise ValueError(
                f"Entry '{entry.entry_id}': 'supersedes' names unknown entry "
                f"'{entry.supersedes}'.")
        if entry.supersedes == entry.entry_id:
            raise ValueError(
                f"Entry '{entry.entry_id}' cannot supersede itself.")
    return DecisionLog(entries=entries)


def load_decisions(path: Path) -> DecisionLog:
    """
    Read and validate a decisions JSON file.

    Args:
        path: Path to the decisions JSON.

    Returns:
        Validated DecisionLog.

    Raises:
        ValueError: On invalid content.
        OSError / json.JSONDecodeError: On read/parse failure.
    """
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return parse_decisions(raw)


def decisions_to_dict(log: DecisionLog) -> dict[str, Any]:
    """
    Serialise a DecisionLog back into a plain JSON-ready dict.

    Empty optional fields are omitted so the output stays clean and round-trips
    through parse_decisions() to an equal log.

    Args:
        log: The log to serialise.

    Returns:
        JSON-serialisable dict in the schema-v1 shape.
    """
    out: list[dict[str, Any]] = []
    for e in log.entries:
        entry: dict[str, Any] = {"id": e.entry_id, "kind": e.kind,
                                 "title": e.title, "status": e.status}
        if e.owner:
            entry["owner"] = e.owner
        if e.logged_on is not None:
            entry["logged_on"] = e.logged_on.isoformat()
        if e.review_by is not None:
            entry["review_by"] = e.review_by.isoformat()
        if e.supersedes:
            entry["supersedes"] = e.supersedes
        if e.notes:
            entry["notes"] = e.notes
        out.append(entry)
    return {"schema": DECISION_SCHEMA_VERSION, "entries": out}


def save_decisions(path: Path, log: DecisionLog) -> None:
    """
    Write a DecisionLog to a JSON file.

    Args:
        path: Destination JSON file.
        log:  The log to write.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(decisions_to_dict(log), indent=2, ensure_ascii=False),
        encoding="utf-8")
