# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       02.09.2026
# Geändert:       02.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Liest und validiert eine Capability-Map (Roadmap B1). Jede Solution kann
#   über das optionale "capabilities"-Feld ihrer Konfiguration auf eine
#   capabilities.json verweisen; der Report rendert daraus die Tabelle
#   „Capability Map & Health": Geschäftsfähigkeiten mit Gesundheitsampel
#   (healthy/at_risk/critical) und den beitragenden ARTs. Capabilities sind
#   die Sprache der EA — sie binden Solution-Fortschritt an Strategie und
#   Wert statt an bloße Ticket-Zahlen. Die Gesundheit bewerten Menschen im
#   PI-Planning/-Review; Owner sind Teams, keine Personen. Die Capability-Map
#   (Geschäftsfähigkeiten) ist bewusst NICHT die stage_map (Workflow-Status)
#   — andere Dimension, andere Quelle.
# =============================================================================

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

CAPABILITY_SCHEMA_VERSION = 1

HEALTH_HEALTHY = "healthy"
HEALTH_AT_RISK = "at_risk"
HEALTH_CRITICAL = "critical"
#: Display order — the most urgent health first.
HEALTH_ORDER = (HEALTH_CRITICAL, HEALTH_AT_RISK, HEALTH_HEALTHY)


@dataclass
class Capability:
    """
    One business capability of the solution.

    ``arts`` names the ARTs (member names) contributing to the capability —
    the map from delivery structure to business value. ``health`` is assessed
    by people; ``assessed_on`` records when, so a stale assessment is visible.
    ``owner`` names a team, not a person.
    """
    cap_id: str
    title: str
    health: str
    arts: list[str] = field(default_factory=list)
    owner: str = ""
    assessed_on: date | None = None
    notes: str = ""


@dataclass
class CapabilityMap:
    """All capabilities of one solution. An empty map is valid."""
    capabilities: list[Capability] = field(default_factory=list)


def parse_capabilities(data: Any) -> CapabilityMap:
    """
    Build a CapabilityMap from an already-parsed JSON object.

    Separated from file reading so it can be unit-tested without touching disk.

    Args:
        data: Parsed JSON object ({"capabilities": [...]}).

    Returns:
        Validated CapabilityMap (health values normalised to lower case,
        ART names stripped, empty entries dropped).

    Raises:
        ValueError: On structural errors — missing list, empty id/title,
                    duplicate id, unknown health, non-list arts,
                    unparsable assessed_on date.
    """
    if not isinstance(data, dict):
        raise ValueError("Capabilities file must be a JSON object.")
    raw = data.get("capabilities")
    if not isinstance(raw, list):
        raise ValueError("Capabilities file needs a 'capabilities' list "
                         "(may be empty).")

    capabilities: list[Capability] = []
    seen: set[str] = set()
    for i, c in enumerate(raw):
        if not isinstance(c, dict):
            raise ValueError(f"Capability #{i + 1} is not an object.")
        cap_id = str(c.get("id", "")).strip()
        if not cap_id:
            raise ValueError(f"Capability #{i + 1} is missing a non-empty 'id'.")
        if cap_id in seen:
            raise ValueError(f"Duplicate capability id '{cap_id}'.")
        seen.add(cap_id)

        title = str(c.get("title", "")).strip()
        if not title:
            raise ValueError(
                f"Capability '{cap_id}' is missing a non-empty 'title'.")

        health = str(c.get("health", "")).strip().lower()
        if health not in HEALTH_ORDER:
            raise ValueError(
                f"Capability '{cap_id}': unknown health '{health}' — expected "
                f"one of {', '.join(HEALTH_ORDER)}.")

        raw_arts = c.get("arts", [])
        if not isinstance(raw_arts, list):
            raise ValueError(f"Capability '{cap_id}': 'arts' must be a list.")
        arts = [str(a).strip() for a in raw_arts if str(a).strip()]

        assessed_raw = c.get("assessed_on")
        try:
            assessed = (date.fromisoformat(str(assessed_raw))
                        if assessed_raw else None)
        except ValueError as exc:
            raise ValueError(
                f"Capability '{cap_id}': 'assessed_on' must be YYYY-MM-DD "
                f"(got '{assessed_raw}').") from exc

        capabilities.append(Capability(
            cap_id=cap_id,
            title=title,
            health=health,
            arts=arts,
            owner=str(c.get("owner", "")).strip(),
            assessed_on=assessed,
            notes=str(c.get("notes", "")).strip(),
        ))
    return CapabilityMap(capabilities=capabilities)


def load_capabilities(path: Path) -> CapabilityMap:
    """
    Read and validate a capabilities JSON file.

    Args:
        path: Path to the capabilities JSON.

    Returns:
        Validated CapabilityMap.

    Raises:
        ValueError: On invalid content.
        OSError / json.JSONDecodeError: On read/parse failure.
    """
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return parse_capabilities(raw)


def capabilities_to_dict(cap_map: CapabilityMap) -> dict[str, Any]:
    """
    Serialise a CapabilityMap back into a plain JSON-ready dict.

    Empty optional fields are omitted so the output stays clean and round-trips
    through parse_capabilities() to an equal map.

    Args:
        cap_map: The map to serialise.

    Returns:
        JSON-serialisable dict in the schema-v1 shape.
    """
    out: list[dict[str, Any]] = []
    for c in cap_map.capabilities:
        entry: dict[str, Any] = {"id": c.cap_id, "title": c.title,
                                 "health": c.health}
        if c.arts:
            entry["arts"] = list(c.arts)
        if c.owner:
            entry["owner"] = c.owner
        if c.assessed_on is not None:
            entry["assessed_on"] = c.assessed_on.isoformat()
        if c.notes:
            entry["notes"] = c.notes
        out.append(entry)
    return {"schema": CAPABILITY_SCHEMA_VERSION, "capabilities": out}


def save_capabilities(path: Path, cap_map: CapabilityMap) -> None:
    """
    Write a CapabilityMap to a JSON file.

    Args:
        path:    Destination JSON file.
        cap_map: The map to write.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(capabilities_to_dict(cap_map), indent=2, ensure_ascii=False),
        encoding="utf-8")
