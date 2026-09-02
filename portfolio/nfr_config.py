# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       02.09.2026
# Geändert:       02.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Liest und validiert ein NFR-/Architecture-Runway-Register (Roadmap B2).
#   Jede Solution kann über das optionale "nfr"-Feld ihrer Konfiguration auf
#   eine nfr.json verweisen; der Report rendert daraus das NFR-Dashboard
#   (Ziel/Ist/Status je NFR) und die Runway-Ampel (in_place/building/gap).
#   Der Status wird bewusst von Menschen gepflegt (PI-Planning/Review) —
#   das Werkzeug bewertet nicht selbst ("das LLM textet, es rechnet nicht"
#   gilt sinngemäß auch für den Zielvergleich). Owner sind Teams, keine
#   Personen.
# =============================================================================

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

NFR_SCHEMA_VERSION = 1

STATUS_MET = "met"
STATUS_AT_RISK = "at_risk"
STATUS_VIOLATED = "violated"
#: Dashboard order — the most urgent status first.
NFR_STATUS_ORDER = (STATUS_VIOLATED, STATUS_AT_RISK, STATUS_MET)

RUNWAY_IN_PLACE = "in_place"
RUNWAY_BUILDING = "building"
RUNWAY_GAP = "gap"
#: Dashboard order — gaps first.
RUNWAY_STATUS_ORDER = (RUNWAY_GAP, RUNWAY_BUILDING, RUNWAY_IN_PLACE)


@dataclass
class Nfr:
    """
    One non-functional requirement of the solution.

    ``target`` and ``actual`` are free-text (e.g. "p95 < 200 ms" / "230 ms") —
    the status is assessed by people in PI planning/review, not computed here.
    ``owner`` names a team, not a person.
    """
    nfr_id: str
    title: str
    target: str
    status: str
    actual: str = ""
    owner: str = ""
    notes: str = ""


@dataclass
class RunwayItem:
    """
    One architecture-runway element (infrastructure future features rely on).

    ``needed_by`` states when the element must be in place; a past date on an
    element that is not ``in_place`` renders as overdue.
    """
    item_id: str
    title: str
    status: str
    needed_by: date | None = None
    owner: str = ""
    notes: str = ""


@dataclass
class NfrRegister:
    """NFRs and runway elements of one solution. Empty lists are valid."""
    nfrs: list[Nfr] = field(default_factory=list)
    runway: list[RunwayItem] = field(default_factory=list)


def _require_entry_fields(
    entry: Any, index: int, kind: str, seen: set[str]
) -> tuple[str, str]:
    """Validate the shared id/title shape of one nfrs/runway entry."""
    if not isinstance(entry, dict):
        raise ValueError(f"{kind} #{index + 1} is not an object.")
    entry_id = str(entry.get("id", "")).strip()
    if not entry_id:
        raise ValueError(f"{kind} #{index + 1} is missing a non-empty 'id'.")
    if entry_id in seen:
        # "NFR" stays upper-case (acronym), "Runway item" reads lower-case
        # mid-sentence — keep the pre-refactor message wording stable.
        dup_kind = kind if kind.isupper() else kind[0].lower() + kind[1:]
        raise ValueError(f"Duplicate {dup_kind} id '{entry_id}'.")
    seen.add(entry_id)
    title = str(entry.get("title", "")).strip()
    if not title:
        raise ValueError(f"{kind} '{entry_id}' is missing a non-empty 'title'.")
    return entry_id, title


def _parse_nfr_entry(entry: Any, index: int, seen: set[str]) -> Nfr:
    """Validate and build one NFR entry."""
    nfr_id, title = _require_entry_fields(entry, index, "NFR", seen)
    target = str(entry.get("target", "")).strip()
    if not target:
        raise ValueError(f"NFR '{nfr_id}' is missing a non-empty 'target'.")
    status = str(entry.get("status", "")).strip().lower()
    if status not in NFR_STATUS_ORDER:
        raise ValueError(
            f"NFR '{nfr_id}': unknown status '{status}' — expected one of "
            f"{', '.join(NFR_STATUS_ORDER)}.")
    return Nfr(
        nfr_id=nfr_id,
        title=title,
        target=target,
        status=status,
        actual=str(entry.get("actual", "")).strip(),
        owner=str(entry.get("owner", "")).strip(),
        notes=str(entry.get("notes", "")).strip(),
    )


def _parse_runway_entry(entry: Any, index: int, seen: set[str]) -> RunwayItem:
    """Validate and build one runway entry."""
    item_id, title = _require_entry_fields(entry, index, "Runway item", seen)
    status = str(entry.get("status", "")).strip().lower()
    if status not in RUNWAY_STATUS_ORDER:
        raise ValueError(
            f"Runway item '{item_id}': unknown status '{status}' — expected "
            f"one of {', '.join(RUNWAY_STATUS_ORDER)}.")
    needed_raw = entry.get("needed_by")
    try:
        needed = date.fromisoformat(str(needed_raw)) if needed_raw else None
    except ValueError as exc:
        raise ValueError(
            f"Runway item '{item_id}': 'needed_by' must be YYYY-MM-DD "
            f"(got '{needed_raw}').") from exc
    return RunwayItem(
        item_id=item_id,
        title=title,
        status=status,
        needed_by=needed,
        owner=str(entry.get("owner", "")).strip(),
        notes=str(entry.get("notes", "")).strip(),
    )


def parse_nfr(data: Any) -> NfrRegister:
    """
    Build an NfrRegister from an already-parsed JSON object.

    Separated from file reading so it can be unit-tested without touching disk.

    Args:
        data: Parsed JSON object ({"nfrs": [...], "runway": [...]}; either
              list may be absent or empty).

    Returns:
        Validated NfrRegister (status values normalised to lower case).

    Raises:
        ValueError: On structural errors — non-list blocks, empty id/title,
                    duplicate id, unknown status, missing NFR target,
                    unparsable needed_by date.
    """
    if not isinstance(data, dict):
        raise ValueError("NFR file must be a JSON object.")

    raw_nfrs = data.get("nfrs", [])
    raw_runway = data.get("runway", [])
    if not isinstance(raw_nfrs, list):
        raise ValueError("'nfrs' must be a list.")
    if not isinstance(raw_runway, list):
        raise ValueError("'runway' must be a list.")

    seen_nfrs: set[str] = set()
    seen_items: set[str] = set()
    return NfrRegister(
        nfrs=[_parse_nfr_entry(n, i, seen_nfrs) for i, n in enumerate(raw_nfrs)],
        runway=[_parse_runway_entry(r, i, seen_items)
                for i, r in enumerate(raw_runway)],
    )


def load_nfr(path: Path) -> NfrRegister:
    """
    Read and validate an NFR/runway JSON file.

    Args:
        path: Path to the NFR JSON.

    Returns:
        Validated NfrRegister.

    Raises:
        ValueError: On invalid content.
        OSError / json.JSONDecodeError: On read/parse failure.
    """
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return parse_nfr(raw)


def nfr_to_dict(register: NfrRegister) -> dict[str, Any]:
    """
    Serialise an NfrRegister back into a plain JSON-ready dict.

    Empty optional fields are omitted so the output stays clean and round-trips
    through parse_nfr() to an equal register.

    Args:
        register: The register to serialise.

    Returns:
        JSON-serialisable dict in the schema-v1 shape.
    """
    out_nfrs: list[dict[str, Any]] = []
    for n in register.nfrs:
        entry: dict[str, Any] = {"id": n.nfr_id, "title": n.title,
                                 "target": n.target, "status": n.status}
        if n.actual:
            entry["actual"] = n.actual
        if n.owner:
            entry["owner"] = n.owner
        if n.notes:
            entry["notes"] = n.notes
        out_nfrs.append(entry)

    out_runway: list[dict[str, Any]] = []
    for r in register.runway:
        entry = {"id": r.item_id, "title": r.title, "status": r.status}
        if r.needed_by is not None:
            entry["needed_by"] = r.needed_by.isoformat()
        if r.owner:
            entry["owner"] = r.owner
        if r.notes:
            entry["notes"] = r.notes
        out_runway.append(entry)

    return {"schema": NFR_SCHEMA_VERSION, "nfrs": out_nfrs, "runway": out_runway}


def save_nfr(path: Path, register: NfrRegister) -> None:
    """
    Write an NfrRegister to a JSON file.

    Args:
        path:     Destination JSON file.
        register: The register to write.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(nfr_to_dict(register), indent=2, ensure_ascii=False),
        encoding="utf-8")
