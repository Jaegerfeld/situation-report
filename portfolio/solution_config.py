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
#   Templates referenziert (Single Source of Truth bleibt das ART-Template).
#   Schema v1 (Phase 1): nur kind="solution" mit Pooled-Aggregation.
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

FRAMEWORK_SAFE = "SAFe"
FRAMEWORK_LESS = "LeSS"
FRAMEWORK_NEXUS = "Nexus"


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
    if kind == KIND_PORTFOLIO:
        raise ValueError("Portfolio nesting is not implemented yet (Phase 3).")

    raw_members = data.get("members")
    if not isinstance(raw_members, list) or not raw_members:
        raise ValueError("Solution config needs a non-empty 'members' list.")

    members: list[Member] = []
    for i, m in enumerate(raw_members):
        if not isinstance(m, dict):
            raise ValueError(f"Member #{i + 1} is not an object.")
        member = Member(
            name=str(m.get("name", "")).strip() or f"ART {i + 1}",
            template=str(m.get("template", "")),
            issue_times=str(m.get("issue_times", "")),
            cfd=str(m.get("cfd", "")),
            workflow=str(m.get("workflow", "")),
            transitions=str(m.get("transitions", "")),
        )
        if not member.template and not member.issue_times:
            raise ValueError(
                f"Member '{member.name}' must set either 'template' or 'issue_times'."
            )
        members.append(member)

    report = data.get("report", {}) or {}
    return SolutionConfig(
        name=name,
        kind=kind,
        framework=str(data.get("framework", FRAMEWORK_SAFE)),
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
