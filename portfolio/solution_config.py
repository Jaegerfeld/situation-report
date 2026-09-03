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
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

# v2 (02.09.2026): optionaler "stage_map"-Block (A4). v1-Dateien ohne den
# Block laden unveraendert; der Parser prueft das Schemafeld bewusst nicht.
# Seit B3 zusaetzlich das optionale "risks"-Feld (Pfad zur ROAM-risks.json),
# seit B2 das optionale "nfr"-Feld (Pfad zur NFR-/Runway-nfr.json), seit B1
# das optionale "capabilities"-Feld (Pfad zur Capability-Map-JSON), seit B5
# das optionale "dependencies"-Feld (Pfad zum Dependency-Register), seit B4
# das optionale "decisions"-Feld (Pfad zum Decision-/Assumption-Log), seit
# C1/C2 die optionalen Felder "slo" (SLO-Register) und "dora"
# (Delivery-Register), seit B6 das optionale "flow_problems"-Feld
# (Flussproblem-Backlog der VSC), seit B7 das optionale "themes"-Feld
# (Strategic Themes + Roadmap) — alles additiv, daher kein Schema-Bump.
SCHEMA_VERSION = 2
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
class StageMap:
    """
    Optional custom canonical stage mapping for pooling heterogeneous workflows.

    ``stages`` maps each canonical stage name (insertion order = display order)
    to the ART stage names it absorbs. ``first_stage``/``closed_stage`` name the
    canonical stages that mark work start and completion for the pooled CFD
    boundaries. Without a StageMap the pooled report keeps the fixed three-group
    mapping (To Do / In Progress / Done via classify_stages).
    """
    stages: dict[str, list[str]]
    first_stage: str
    closed_stage: str

    def lookup(self) -> dict[str, str]:
        """Flatten to a source-stage -> canonical-stage dict (exact match)."""
        return {src: canon for canon, sources in self.stages.items() for src in sources}


def parse_stage_map(data: Any) -> StageMap | None:
    """
    Parse and validate the optional ``stage_map`` block.

    Args:
        data: The raw JSON value of the "stage_map" key (or None).

    Returns:
        A validated StageMap, or None when the block is absent.

    Raises:
        ValueError: On structural errors — empty mapping, non-list group,
                    duplicate source stage, unknown or identical boundary markers.
    """
    if data is None:
        return None
    if not isinstance(data, dict):
        raise ValueError("'stage_map' must be an object.")

    raw_stages = data.get("stages")
    if not isinstance(raw_stages, dict) or not raw_stages:
        raise ValueError("'stage_map.stages' must be a non-empty object.")

    stages: dict[str, list[str]] = {}
    seen: dict[str, str] = {}
    for canon, sources in raw_stages.items():
        canon = str(canon).strip()
        if not canon:
            raise ValueError("'stage_map.stages' contains an empty canonical name.")
        if not isinstance(sources, list) or not sources:
            raise ValueError(f"Canonical stage '{canon}' needs a non-empty list "
                             f"of source stages.")
        cleaned = [str(s).strip() for s in sources if str(s).strip()]
        for s in cleaned:
            if s in seen:
                raise ValueError(f"Source stage '{s}' is mapped to both "
                                 f"'{seen[s]}' and '{canon}'.")
            seen[s] = canon
        stages[canon] = cleaned

    first = str(data.get("first_stage", "")).strip()
    closed = str(data.get("closed_stage", "")).strip()
    for label, value in (("first_stage", first), ("closed_stage", closed)):
        if value not in stages:
            raise ValueError(f"'stage_map.{label}' must name one of the canonical "
                             f"stages (got '{value}').")
    if first == closed:
        raise ValueError("'stage_map.first_stage' and 'closed_stage' must differ "
                         "(the CFD needs distinct work-start and completion stages).")
    return StageMap(stages=stages, first_stage=first, closed_stage=closed)


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
        modes:      Requested report modes ("pooled" / "comparison").
        stage_map:  Optional custom canonical stage mapping (A4); None keeps
                    the fixed three-group pooling.
        risks:      Optional path to a ROAM risks JSON (B3); "" means no
                    risk register.
        nfr:        Optional path to an NFR/architecture-runway JSON (B2);
                    "" means no NFR register.
        capabilities: Optional path to a capability-map JSON (B1); "" means
                    no capability map.
        dependencies: Optional path to a dependency-register JSON (B5); ""
                    means no dependency register.
        decisions:  Optional path to a decision/assumption-log JSON (B4);
                    "" means no decision log.
        slo:        Optional path to an SLO register JSON (C1); "" means
                    no SLO register.
        dora:       Optional path to a delivery register JSON (C2, DORA +
                    quality); "" means no delivery register.
        flow_problems: Optional path to a flow-problem backlog JSON (B6);
                    "" means no backlog.
        themes:     Optional path to a strategic-themes/roadmap JSON (B7);
                    "" means no themes register.
    """
    name: str
    kind: str = KIND_SOLUTION
    framework: str = FRAMEWORK_SAFE
    terminology: str = TERMINOLOGY_SAFE
    members: list[Member] = field(default_factory=list)
    from_date: date | None = None
    to_date: date | None = None
    modes: list[str] = field(default_factory=lambda: ["pooled"])
    stage_map: StageMap | None = None
    risks: str = ""
    nfr: str = ""
    capabilities: str = ""
    dependencies: str = ""
    decisions: str = ""
    slo: str = ""
    dora: str = ""
    flow_problems: str = ""
    themes: str = ""
    #: Folder of the file this config was loaded from (set by
    #: load_solution_config, never serialised). Relative paths inside the
    #: config resolve against it — the Datenraum rule that makes a
    #: portfolio folder portable. None = built in memory (legacy CWD
    #: behaviour).
    base_dir: Path | None = field(default=None, compare=False, repr=False)


def resolve_config_path(
    base: Path | None,
    value: str,
    log: Callable[[str], None] | None = None,
) -> Path:
    """
    Resolve a path stated in a config file (the Datenraum rule).

    Absolute values pass through unchanged. Relative values resolve
    against ``base`` (the folder of the config file that states them) —
    that is what makes a portfolio folder movable and copyable as a
    whole. Legacy configs that meant "relative to the working directory"
    keep working: when nothing exists at the config-relative location but
    the CWD-relative one does, that path is used and a warning suggests
    storing the path relative to the config.

    Args:
        base:  Folder of the config file (``config.base_dir``), or None
               for in-memory configs (plain CWD behaviour).
        value: The path string exactly as stated in the config.
        log:   Optional warning callback for the legacy fallback.

    Returns:
        The resolved path (config-relative candidate when nothing exists
        yet, so error messages point at the intended location).
    """
    raw = Path(str(value).strip())
    if raw.is_absolute() or base is None:
        return raw
    candidate = Path(base) / raw
    if candidate.exists():
        return candidate
    if raw.exists():
        if log is not None:
            log(f"  WARNING: '{value}' was resolved relative to the "
                f"working directory (legacy behaviour); store it relative "
                f"to the config file to make the folder portable.")
        return raw
    return candidate


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
        stage_map=parse_stage_map(data.get("stage_map")),
        risks=str(data.get("risks", "")).strip(),
        nfr=str(data.get("nfr", "")).strip(),
        capabilities=str(data.get("capabilities", "")).strip(),
        dependencies=str(data.get("dependencies", "")).strip(),
        decisions=str(data.get("decisions", "")).strip(),
        slo=str(data.get("slo", "")).strip(),
        dora=str(data.get("dora", "")).strip(),
        flow_problems=str(data.get("flow_problems", "")).strip(),
        themes=str(data.get("themes", "")).strip(),
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
    config = parse_solution_config(raw)
    config.base_dir = Path(path).resolve().parent
    return config


def to_dict(config: SolutionConfig) -> dict[str, Any]:
    """
    Serialise a SolutionConfig back into a plain JSON-ready dict.

    Empty optional member fields are omitted so the output stays clean and
    round-trips through parse_solution_config() to an equal config.

    Args:
        config: The configuration to serialise.

    Returns:
        JSON-serialisable dict in the schema-v2 shape (stage_map only when set).
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

    out: dict[str, Any] = {
        "schema": SCHEMA_VERSION,
        "app": APP_NAME,
        "kind": config.kind,
        "name": config.name,
        "framework": config.framework,
        "members": members,
        "report": report,
    }
    if config.stage_map is not None:
        out["stage_map"] = {
            "stages": {k: list(v) for k, v in config.stage_map.stages.items()},
            "first_stage": config.stage_map.first_stage,
            "closed_stage": config.stage_map.closed_stage,
        }
    for register in ("risks", "nfr", "capabilities", "dependencies",
                     "decisions", "slo", "dora", "flow_problems", "themes"):
        value = getattr(config, register)
        if value:
            out[register] = value
    return out


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
