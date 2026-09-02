# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       02.09.2026
# Geändert:       02.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Liest und validiert ein Dependency-/Integrations-Register (Roadmap B5).
#   Jede Solution kann über das optionale "dependencies"-Feld ihrer
#   Konfiguration auf eine dependencies.json verweisen; der Report rendert
#   daraus die Dependency-Heatmap (wer braucht was von wem) und die
#   Detail-Tabelle. Cross-ART-Abhängigkeiten sind Systemverhalten — sie
#   sichtbar zu machen schützt vor lokaler Optimierung. Das Ziel (to) darf
#   auch außerhalb der Solution liegen (anderer ART, Lieferant, Fremdsystem);
#   deshalb wird es bewusst nicht gegen die Member-Liste validiert.
# =============================================================================

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

DEPENDENCY_SCHEMA_VERSION = 1

DEP_BLOCKED = "blocked"
DEP_AT_RISK = "at_risk"
DEP_ON_TRACK = "on_track"
DEP_DONE = "done"
#: Display order — the most urgent status first; done last.
DEP_STATUS_ORDER = (DEP_BLOCKED, DEP_AT_RISK, DEP_ON_TRACK, DEP_DONE)


@dataclass
class Dependency:
    """
    One dependency/integration point between delivery units.

    ``from_art`` needs something that ``to_art`` delivers. ``due`` states when
    it must be resolved; a past date on a dependency that is not done renders
    as overdue. ``to_art`` may name a unit outside the solution (another
    solution's ART, a vendor, an external system).
    """
    dep_id: str
    title: str
    from_art: str
    to_art: str
    status: str
    due: date | None = None
    notes: str = ""


@dataclass
class DependencyRegister:
    """All dependencies of one solution. An empty register is valid."""
    dependencies: list[Dependency] = field(default_factory=list)


def parse_dependencies(data: Any) -> DependencyRegister:
    """
    Build a DependencyRegister from an already-parsed JSON object.

    Separated from file reading so it can be unit-tested without touching disk.

    Args:
        data: Parsed JSON object ({"dependencies": [...]}).

    Returns:
        Validated DependencyRegister (status values normalised to lower case).

    Raises:
        ValueError: On structural errors — missing list, empty id/title/
                    from/to, duplicate id, unknown status, unparsable due
                    date, identical from and to.
    """
    if not isinstance(data, dict):
        raise ValueError("Dependencies file must be a JSON object.")
    raw = data.get("dependencies")
    if not isinstance(raw, list):
        raise ValueError("Dependencies file needs a 'dependencies' list "
                         "(may be empty).")

    dependencies: list[Dependency] = []
    seen: set[str] = set()
    for i, d in enumerate(raw):
        if not isinstance(d, dict):
            raise ValueError(f"Dependency #{i + 1} is not an object.")
        dep_id = str(d.get("id", "")).strip()
        if not dep_id:
            raise ValueError(f"Dependency #{i + 1} is missing a non-empty 'id'.")
        if dep_id in seen:
            raise ValueError(f"Duplicate dependency id '{dep_id}'.")
        seen.add(dep_id)

        title = str(d.get("title", "")).strip()
        if not title:
            raise ValueError(
                f"Dependency '{dep_id}' is missing a non-empty 'title'.")

        from_art = str(d.get("from", "")).strip()
        to_art = str(d.get("to", "")).strip()
        if not from_art or not to_art:
            raise ValueError(
                f"Dependency '{dep_id}' needs non-empty 'from' and 'to'.")
        if from_art == to_art:
            raise ValueError(
                f"Dependency '{dep_id}': 'from' and 'to' must differ "
                f"(a unit cannot depend on itself).")

        status = str(d.get("status", "")).strip().lower()
        if status not in DEP_STATUS_ORDER:
            raise ValueError(
                f"Dependency '{dep_id}': unknown status '{status}' — expected "
                f"one of {', '.join(DEP_STATUS_ORDER)}.")

        due_raw = d.get("due")
        try:
            due = date.fromisoformat(str(due_raw)) if due_raw else None
        except ValueError as exc:
            raise ValueError(
                f"Dependency '{dep_id}': 'due' must be YYYY-MM-DD "
                f"(got '{due_raw}').") from exc

        dependencies.append(Dependency(
            dep_id=dep_id,
            title=title,
            from_art=from_art,
            to_art=to_art,
            status=status,
            due=due,
            notes=str(d.get("notes", "")).strip(),
        ))
    return DependencyRegister(dependencies=dependencies)


def load_dependencies(path: Path) -> DependencyRegister:
    """
    Read and validate a dependencies JSON file.

    Args:
        path: Path to the dependencies JSON.

    Returns:
        Validated DependencyRegister.

    Raises:
        ValueError: On invalid content.
        OSError / json.JSONDecodeError: On read/parse failure.
    """
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return parse_dependencies(raw)


def dependencies_to_dict(register: DependencyRegister) -> dict[str, Any]:
    """
    Serialise a DependencyRegister back into a plain JSON-ready dict.

    Empty optional fields are omitted so the output stays clean and round-trips
    through parse_dependencies() to an equal register.

    Args:
        register: The register to serialise.

    Returns:
        JSON-serialisable dict in the schema-v1 shape.
    """
    out: list[dict[str, Any]] = []
    for d in register.dependencies:
        entry: dict[str, Any] = {"id": d.dep_id, "title": d.title,
                                 "from": d.from_art, "to": d.to_art,
                                 "status": d.status}
        if d.due is not None:
            entry["due"] = d.due.isoformat()
        if d.notes:
            entry["notes"] = d.notes
        out.append(entry)
    return {"schema": DEPENDENCY_SCHEMA_VERSION, "dependencies": out}


def save_dependencies(path: Path, register: DependencyRegister) -> None:
    """
    Write a DependencyRegister to a JSON file.

    Args:
        path:     Destination JSON file.
        register: The register to write.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(dependencies_to_dict(register), indent=2, ensure_ascii=False),
        encoding="utf-8")
