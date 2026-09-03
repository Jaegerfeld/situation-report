# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Report-Snapshot für das Delta-Briefing (Roadmap D2, deterministischer
#   Kern). Ein Snapshot friert den Zustand eines Solution-/Portfolio-Reports
#   als kleines JSON ein: Kennzahlen je Einheit (und gepoolt), Datenqualität
#   je Quelle, Zustände der fünf Governance-Register. Zwei Snapshots sind die
#   Voraussetzung des Delta-Briefings („Was hat sich geändert?" — Hohpes
#   first derivative als Produkt, Muster M2). Alles hier ist deterministisch;
#   Zahlen entstehen ausschließlich in der Pipeline, nie in einer KI-Schicht.
# =============================================================================

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .aggregator import (
    _collect_capabilities,
    _collect_decisions,
    _collect_dependencies,
    _collect_nfr,
    _collect_risks,
    _collect_themes,
    build_pooled_report_data,
    load_comparison_units,
)
from .solution_config import SolutionConfig, load_solution_config
from .summary import SourceQuality, Summary, compute_summary

SNAPSHOT_SCHEMA_VERSION = 1


@dataclass
class Snapshot:
    """
    Frozen state of one solution/portfolio report at a reference date.

    ``as_of`` is the observation date all age/overdue judgements refer to;
    ``units`` are the comparison units (ARTs of a solution, member solutions
    of a portfolio), ``total`` the pooled whole. Governance entries keep raw
    status fields plus the dates needed to re-derive overdue/aging on either
    side of a delta.
    """
    name: str
    kind: str
    as_of: date
    created: str
    target_ct: int
    total: dict[str, Any]
    units: list[dict[str, Any]] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)
    governance: dict[str, list[dict[str, Any]]] = field(default_factory=dict)


def _summary_dict(summary: Summary) -> dict[str, Any]:
    """Serialise a Summary into the snapshot's unit shape."""
    d = asdict(summary)
    d["open"] = d.pop("open_items")
    return d


def _quality_dict(q: SourceQuality, as_of: date) -> dict[str, Any]:
    """
    Serialise a SourceQuality with age/confidence re-anchored to ``as_of``.

    The aggregator assesses quality against today; a snapshot may represent an
    earlier observation date, so the age-derived confidence is recomputed.
    """
    anchored = SourceQuality(
        label=q.label, records=q.records,
        pct_missing_first=q.pct_missing_first, pct_open=q.pct_open,
        has_cfd=q.has_cfd, data_as_of=q.data_as_of,
        age_days=(as_of - q.data_as_of).days if q.data_as_of else None,
    )
    return {
        "label": anchored.label,
        "records": anchored.records,
        "pct_missing_first": round(anchored.pct_missing_first, 1),
        "has_cfd": anchored.has_cfd,
        "data_as_of": anchored.data_as_of.isoformat() if anchored.data_as_of else None,
        "confidence": anchored.confidence,
    }


def _iso(d: date | None) -> str | None:
    return d.isoformat() if d else None


def _governance_dict(
    config: SolutionConfig, log: Callable[[str], None]
) -> dict[str, list[dict[str, Any]]]:
    """Collect the five governance registers into snapshot entries."""
    risks = [{"id": r.risk_id, "title": r.title, "roam": r.roam,
              "impact": r.impact, "owner": r.owner,
              "since": _iso(r.status_since), "solution": src}
             for src, r in _collect_risks(config, log=log)]
    deps = [{"id": d.dep_id, "title": d.title, "from": d.from_art,
             "to": d.to_art, "status": d.status, "due": _iso(d.due),
             "solution": src}
            for src, d in _collect_dependencies(config, log=log)]
    nfr_entries, runway_entries = _collect_nfr(config, log=log)
    nfrs = [{"id": n.nfr_id, "title": n.title, "status": n.status,
             "solution": src}
            for src, n in nfr_entries]
    runway = [{"id": r.item_id, "title": r.title, "status": r.status,
               "needed_by": _iso(r.needed_by), "solution": src}
              for src, r in runway_entries]
    caps = [{"id": c.cap_id, "title": c.title, "health": c.health,
             "arts": len(c.arts), "solution": src}
            for src, c in _collect_capabilities(config, log=log)]
    decisions = [{"id": e.entry_id, "kind": e.kind, "title": e.title,
                  "status": e.status, "review_by": _iso(e.review_by),
                  "solution": src}
                 for src, e in _collect_decisions(config, log=log)]
    _themes, epic_entries = _collect_themes(config, log=log)
    epics = [{"id": e.epic_id, "title": e.title, "train": e.train,
              "horizon": e.horizon, "theme": e.theme, "status": e.status,
              "solution": src}
             for src, e in epic_entries]
    return {"risks": risks, "dependencies": deps, "nfr": nfrs,
            "runway": runway, "capabilities": caps, "decisions": decisions,
            "epics": epics}


def build_snapshot(
    config: SolutionConfig,
    as_of: date | None = None,
    target_ct: int = 90,
    log: Callable[[str], None] = print,
) -> Snapshot:
    """
    Compute a report snapshot for a solution/portfolio configuration.

    Loads the same data the report loads (pooled total, comparison units,
    source qualities, governance registers) and freezes the computed state.

    Args:
        config:    The solution or portfolio configuration.
        as_of:     Observation date for age/overdue judgements (default: today).
        target_ct: Cycle-time target in days (mirrors the report default).
        log:       Progress callback.

    Returns:
        A populated Snapshot.
    """
    as_of = as_of or date.today()
    qualities: list[SourceQuality] = []
    pooled = build_pooled_report_data(config, log=log, quality_sink=qualities)
    units = load_comparison_units(config, log=log)
    return Snapshot(
        name=config.name,
        kind=config.kind,
        as_of=as_of,
        created=datetime.now().isoformat(timespec="seconds"),
        target_ct=target_ct,
        total=_summary_dict(compute_summary(pooled, config.name, target_ct)),
        units=[_summary_dict(compute_summary(u, u.source_prefix, target_ct))
               for u in units],
        sources=[_quality_dict(q, as_of) for q in qualities],
        governance=_governance_dict(config, log),
    )


def snapshot_to_dict(snapshot: Snapshot) -> dict[str, Any]:
    """Serialise a Snapshot into the schema-v1 JSON shape."""
    return {
        "schema": SNAPSHOT_SCHEMA_VERSION,
        "name": snapshot.name,
        "kind": snapshot.kind,
        "as_of": snapshot.as_of.isoformat(),
        "created": snapshot.created,
        "target_ct": snapshot.target_ct,
        "total": snapshot.total,
        "units": snapshot.units,
        "sources": snapshot.sources,
        "governance": snapshot.governance,
    }


def parse_snapshot(data: Any) -> Snapshot:
    """
    Build a Snapshot from an already-parsed JSON object.

    Raises:
        ValueError: On a non-object, unsupported schema, or missing fields.
    """
    if not isinstance(data, dict):
        raise ValueError("Snapshot file must be a JSON object.")
    schema = data.get("schema")
    if schema != SNAPSHOT_SCHEMA_VERSION:
        raise ValueError(f"Unsupported snapshot schema '{schema}' — "
                         f"expected {SNAPSHOT_SCHEMA_VERSION}.")
    try:
        as_of = date.fromisoformat(str(data["as_of"]))
        return Snapshot(
            name=str(data["name"]),
            kind=str(data.get("kind", "")),
            as_of=as_of,
            created=str(data.get("created", "")),
            target_ct=int(data.get("target_ct", 90)),
            total=dict(data["total"]),
            units=[dict(u) for u in data.get("units", [])],
            sources=[dict(s) for s in data.get("sources", [])],
            governance={k: [dict(e) for e in v]
                        for k, v in dict(data.get("governance", {})).items()},
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid snapshot content: {exc}") from exc


def load_snapshot(path: Path) -> Snapshot:
    """Read and validate a snapshot JSON file."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return parse_snapshot(raw)


def save_snapshot(path: Path, snapshot: Snapshot) -> None:
    """Write a Snapshot to a JSON file (parents created as needed)."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(snapshot_to_dict(snapshot), indent=2, ensure_ascii=False),
        encoding="utf-8")


def write_snapshot_for_config(
    config_path: Path,
    output: Path,
    as_of: date | None = None,
    target_ct: int = 90,
    log: Callable[[str], None] = print,
) -> Snapshot:
    """
    Convenience wrapper: load config, build the snapshot, write it.

    Args:
        config_path: Path to the solution-config JSON.
        output:      Destination snapshot file.
        as_of:       Observation date (default: today).
        target_ct:   Cycle-time target in days.
        log:         Progress callback.

    Returns:
        The written Snapshot.
    """
    config = load_solution_config(config_path)
    snapshot = build_snapshot(config, as_of=as_of, target_ct=target_ct, log=log)
    save_snapshot(output, snapshot)
    log(f"Snapshot written: {output}")
    return snapshot
