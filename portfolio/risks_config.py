# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       02.09.2026
# Geändert:       02.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Liest und validiert ein ROAM-Risiko-Register (Roadmap B3). Jede Solution
#   kann über das optionale "risks"-Feld ihrer Konfiguration auf eine
#   risks.json verweisen; der Report rendert daraus das ROAM-Board
#   (Resolved / Owned / Accepted / Mitigated). Owner sind Teams, keine
#   Personen — das Lagebild zeigt Verantwortung, keine Schuldigen.
# =============================================================================

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

RISKS_SCHEMA_VERSION = 1

ROAM_RESOLVED = "resolved"
ROAM_OWNED = "owned"
ROAM_ACCEPTED = "accepted"
ROAM_MITIGATED = "mitigated"
#: Display order of the board sections (the literal R-O-A-M reading).
ROAM_ORDER = (ROAM_RESOLVED, ROAM_OWNED, ROAM_ACCEPTED, ROAM_MITIGATED)

IMPACT_HIGH = "high"
IMPACT_MEDIUM = "medium"
IMPACT_LOW = "low"
IMPACT_ORDER = (IMPACT_HIGH, IMPACT_MEDIUM, IMPACT_LOW)


@dataclass
class Risk:
    """
    One risk on the ROAM board.

    ``status_since`` records when the risk entered its current ROAM category;
    the report derives the age from it (aging makes stuck ownership visible).
    ``owner`` names a team, not a person.
    """
    risk_id: str
    title: str
    roam: str
    owner: str = ""
    impact: str = IMPACT_MEDIUM
    status_since: date | None = None
    notes: str = ""


@dataclass
class RiskRegister:
    """All risks of one solution. An empty register is valid (no known risks)."""
    risks: list[Risk] = field(default_factory=list)


def parse_risks(data: Any) -> RiskRegister:
    """
    Build a RiskRegister from an already-parsed JSON object.

    Separated from file reading so it can be unit-tested without touching disk.

    Args:
        data: Parsed JSON object ({"risks": [...]}).

    Returns:
        Validated RiskRegister (ROAM/impact values normalised to lower case).

    Raises:
        ValueError: On structural errors — missing list, empty id/title,
                    duplicate id, unknown ROAM category or impact level,
                    unparsable status_since date.
    """
    if not isinstance(data, dict):
        raise ValueError("Risks file must be a JSON object.")
    raw = data.get("risks")
    if not isinstance(raw, list):
        raise ValueError("Risks file needs a 'risks' list (may be empty).")

    risks: list[Risk] = []
    seen: set[str] = set()
    for i, r in enumerate(raw):
        if not isinstance(r, dict):
            raise ValueError(f"Risk #{i + 1} is not an object.")
        risk_id = str(r.get("id", "")).strip()
        if not risk_id:
            raise ValueError(f"Risk #{i + 1} is missing a non-empty 'id'.")
        if risk_id in seen:
            raise ValueError(f"Duplicate risk id '{risk_id}'.")
        seen.add(risk_id)

        title = str(r.get("title", "")).strip()
        if not title:
            raise ValueError(f"Risk '{risk_id}' is missing a non-empty 'title'.")

        roam = str(r.get("roam", "")).strip().lower()
        if roam not in ROAM_ORDER:
            raise ValueError(
                f"Risk '{risk_id}': unknown ROAM category '{roam}' — expected "
                f"one of {', '.join(ROAM_ORDER)}.")

        impact = str(r.get("impact", IMPACT_MEDIUM)).strip().lower() or IMPACT_MEDIUM
        if impact not in IMPACT_ORDER:
            raise ValueError(
                f"Risk '{risk_id}': unknown impact '{impact}' — expected "
                f"one of {', '.join(IMPACT_ORDER)}.")

        since_raw = r.get("status_since")
        try:
            since = date.fromisoformat(str(since_raw)) if since_raw else None
        except ValueError as exc:
            raise ValueError(
                f"Risk '{risk_id}': 'status_since' must be YYYY-MM-DD "
                f"(got '{since_raw}').") from exc

        risks.append(Risk(
            risk_id=risk_id,
            title=title,
            roam=roam,
            owner=str(r.get("owner", "")).strip(),
            impact=impact,
            status_since=since,
            notes=str(r.get("notes", "")).strip(),
        ))
    return RiskRegister(risks=risks)


def load_risks(path: Path) -> RiskRegister:
    """
    Read and validate a risks JSON file.

    Args:
        path: Path to the risks JSON.

    Returns:
        Validated RiskRegister.

    Raises:
        ValueError: On invalid content.
        OSError / json.JSONDecodeError: On read/parse failure.
    """
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return parse_risks(raw)


def risks_to_dict(register: RiskRegister) -> dict[str, Any]:
    """
    Serialise a RiskRegister back into a plain JSON-ready dict.

    Empty optional fields are omitted so the output stays clean and round-trips
    through parse_risks() to an equal register.

    Args:
        register: The register to serialise.

    Returns:
        JSON-serialisable dict in the schema-v1 shape.
    """
    out_risks: list[dict[str, Any]] = []
    for r in register.risks:
        entry: dict[str, Any] = {"id": r.risk_id, "title": r.title, "roam": r.roam}
        if r.owner:
            entry["owner"] = r.owner
        entry["impact"] = r.impact
        if r.status_since is not None:
            entry["status_since"] = r.status_since.isoformat()
        if r.notes:
            entry["notes"] = r.notes
        out_risks.append(entry)
    return {"schema": RISKS_SCHEMA_VERSION, "risks": out_risks}


def save_risks(path: Path, register: RiskRegister) -> None:
    """
    Write a RiskRegister to a JSON file.

    Args:
        path:     Destination JSON file.
        register: The register to write.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(risks_to_dict(register), indent=2, ensure_ascii=False),
        encoding="utf-8")
