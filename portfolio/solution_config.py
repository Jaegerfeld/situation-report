# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       22.06.2026
# Geändert:       22.06.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Liest und validiert eine Solution-/Portfolio-Konfiguration. Eine Solution
#   fasst mehrere bereits konfigurierte ARTs zusammen, indem sie deren Project-
#   Templates referenziert. Ein Portfolio (kind="portfolio") fasst wiederum
#   mehrere Solutions zusammen, indem es deren Solution-Templates referenziert —
#   eine Solution-Konfig ist damit selbst ein wiederverwendbares Template
#   (Single Source of Truth bleibt jeweils die referenzierte Datei). So gilt
#   derselbe Template-/Referenz-Mechanismus auf ART- wie auf Solution-Ebene.
# =============================================================================

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
APP_NAME = "situation_report"

KIND_SOLUTION = "solution"
KIND_PORTFOLIO = "portfolio"

MODE_POOLED = "pooled"
MODE_COMPARISON = "comparison"

FRAMEWORK_SAFE = "SAFe"
FRAMEWORK_LESS = "LeSS"
FRAMEWORK_NEXUS = "Nexus"

#: Report terminology (matches build_reports.terminology SAFE/GLOBAL values).
TERMINOLOGY_SAFE = "SAFe"
TERMINOLOGY_GLOBAL = "Global"


@dataclass
class Member:
    """
    One member of a solution: a reference to a configured ART.

    Either ``template`` (path to a project template whose build_reports section
    holds the data paths) or a direct ``issue_times`` path must be set. The
    direct form bypasses template resolution and is handy for tests and ad-hoc
    setups.
    """
    name: str
    template: str = ""
    issue_times: str = ""
    cfd: str = ""
    workflow: str = ""
    transitions: str = ""


@dataclass
class SolutionConfig:
    """
    Parsed solution/portfolio configuration.

    Attributes:
        name:       Display name of the solution/portfolio.
        kind:       KIND_SOLUTION or KIND_PORTFOLIO.
        framework:  Terminology framework (SAFe / LeSS / Nexus).
        members:    List of Member references to aggregate.
        from_date:  Optional solution-level report start date.
        to_date:    Optional solution-level report end date.
        modes:      Requested report modes (Phase 1 supports only "pooled").
    """
    name: str
    kind: str = KIND_SOLUTION
    framework: str = FRAMEWORK_SAFE
    terminology: str = TERMINOLOGY_SAFE
    members: list[Member] = field(default_factory=list)
    from_date: date | None = None
    to_date: date | None = None
    modes: list[str] = field(default_factory=lambda: ["pooled"])


def _parse_date(value: Any) -> date | None:
    """Parse an optional YYYY-MM-DD string into a date, or None."""
    if not value:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def parse_solution_config(data: dict[str, Any]) -> SolutionConfig:
    """
    Build a SolutionConfig from an already-parsed JSON object.

    Separated from file reading so it can be unit-tested without touching disk.

    Args:
        data: Parsed JSON object.

    Returns:
        Validated SolutionConfig.

    Raises:
        ValueError: If required fields are missing or invalid.
    """
    if not isinstance(data, dict):
        raise ValueError("Solution config must be a JSON object.")

    name = str(data.get("name", "")).strip()
    if not name:
        raise ValueError("Solution config is missing a non-empty 'name'.")

    kind = str(data.get("kind", KIND_SOLUTION))
    if kind not in (KIND_SOLUTION, KIND_PORTFOLIO):
        raise ValueError(f"Unknown kind '{kind}' — expected 'solution' or 'portfolio'.")

    raw_members = data.get("members")
    if not isinstance(raw_members, list) or not raw_members:
        raise ValueError("Solution config needs a non-empty 'members' list.")

    members: list[Member] = []
    for i, m in enumerate(raw_members):
        if not isinstance(m, dict):
            raise ValueError(f"Member #{i + 1} is not an object.")
        default_name = ("Solution" if kind == KIND_PORTFOLIO else "ART") + f" {i + 1}"
        member = Member(
            name=str(m.get("name", "")).strip() or default_name,
            template=str(m.get("template", "")),
            issue_times=str(m.get("issue_times", "")),
            cfd=str(m.get("cfd", "")),
            workflow=str(m.get("workflow", "")),
            transitions=str(m.get("transitions", "")),
        )
        if kind == KIND_PORTFOLIO:
            # A portfolio member references a saved solution template (Single
            # Source of Truth: the solution config file), never raw ART data.
            if not member.template:
                raise ValueError(
                    f"Portfolio member '{member.name}' must reference a solution "
                    f"template via 'template'."
                )
        elif not member.template and not member.issue_times:
            raise ValueError(
                f"Member '{member.name}' must set either 'template' or 'issue_times'."
            )
        members.append(member)

    report = data.get("report", {}) or {}
    terminology = str(report.get("terminology", TERMINOLOGY_SAFE))
    if terminology not in (TERMINOLOGY_SAFE, TERMINOLOGY_GLOBAL):
        terminology = TERMINOLOGY_SAFE
    return SolutionConfig(
        name=name,
        kind=kind,
        framework=str(data.get("framework", FRAMEWORK_SAFE)),
        terminology=terminology,
        members=members,
        from_date=_parse_date(report.get("from_date")),
        to_date=_parse_date(report.get("to_date")),
        modes=list(report.get("modes", ["pooled"])) or ["pooled"],
    )


def load_solution_config(path: Path) -> SolutionConfig:
    """
    Read and validate a solution-config JSON file.

    Args:
        path: Path to the solution config JSON.

    Returns:
        Validated SolutionConfig.

    Raises:
        ValueError: On invalid content.
        OSError / json.JSONDecodeError: On read/parse failure.
    """
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return parse_solution_config(raw)


def to_dict(config: SolutionConfig) -> dict[str, Any]:
    """
    Serialise a SolutionConfig back into a plain JSON-ready dict.

    Empty optional member fields are omitted so the output stays clean and
    round-trips through parse_solution_config() to an equal config.

    Args:
        config: The configuration to serialise.

    Returns:
        JSON-serialisable dict in the schema-v1 shape.
    """
    members: list[dict[str, Any]] = []
    for m in config.members:
        entry: dict[str, Any] = {"name": m.name}
        for key in ("template", "issue_times", "cfd", "workflow", "transitions"):
            value = getattr(m, key)
            if value:
                entry[key] = value
        members.append(entry)

    report: dict[str, Any] = {"modes": list(config.modes), "terminology": config.terminology}
    if config.from_date is not None:
        report["from_date"] = config.from_date.isoformat()
    if config.to_date is not None:
        report["to_date"] = config.to_date.isoformat()

    return {
        "schema": SCHEMA_VERSION,
        "app": APP_NAME,
        "kind": config.kind,
        "name": config.name,
        "framework": config.framework,
        "members": members,
        "report": report,
    }


def save_solution_config(path: Path, config: SolutionConfig) -> None:
    """
    Write a SolutionConfig to a JSON file.

    Args:
        path:   Destination JSON file.
        config: The configuration to write.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(to_dict(config), indent=2, ensure_ascii=False), encoding="utf-8"
    )
