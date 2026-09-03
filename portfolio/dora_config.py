# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Delivery-Register (Roadmap C2): DORA-Kennzahlen und statische Qualität
#   aus dem Quellen-Framework, in einer Datei ({dora: [...], quality:
#   [...]}) — zwei Sichten auf dieselbe Frage („Wie gesund liefert das
#   System?"). Die DORA-Einstufung (elite/high/medium/low je Kennzahl)
#   folgt den veröffentlichten DORA-Schwellen und ist ZENTRAL — jede
#   Quelle (GitHub, GitLab, Datei-Export, künftige) wird gleich beurteilt.
# =============================================================================

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sources.base import (
    KIND_DORA,
    KIND_QUALITY,
    DoraRecord,
    QualityRecord,
    record_from_dict,
    record_to_dict,
)

DORA_SCHEMA_VERSION = 1

TIER_ELITE = "elite"
TIER_HIGH = "high"
TIER_MEDIUM = "medium"
TIER_LOW = "low"
TIER_UNKNOWN = "unknown"
#: Worst-first ordering for display and the overall unit tier.
TIER_ORDER = (TIER_LOW, TIER_MEDIUM, TIER_HIGH, TIER_ELITE)


@dataclass
class DeliveryRegister:
    """DORA + quality records of one solution. Empty is valid."""
    dora: list[DoraRecord] = field(default_factory=list)
    quality: list[QualityRecord] = field(default_factory=list)


def _tier(value: float | None, elite: float, high: float, medium: float,
          higher_is_better: bool) -> str:
    """Generic threshold classifier for one DORA metric."""
    if value is None:
        return TIER_UNKNOWN
    if higher_is_better:
        if value >= elite:
            return TIER_ELITE
        if value >= high:
            return TIER_HIGH
        if value >= medium:
            return TIER_MEDIUM
        return TIER_LOW
    if value <= elite:
        return TIER_ELITE
    if value <= high:
        return TIER_HIGH
    if value <= medium:
        return TIER_MEDIUM
    return TIER_LOW


def deployment_frequency_tier(record: DoraRecord) -> str:
    """Elite: on-demand (≥1/day); high: ≥1/week; medium: ≥1/month."""
    return _tier(record.deployments_per_day, 1.0, 1 / 7, 1 / 30, True)


def lead_time_tier(record: DoraRecord) -> str:
    """Elite: <1 day; high: <1 week; medium: <1 month (hours)."""
    return _tier(record.lead_time_hours, 24.0, 168.0, 720.0, False)


def change_failure_tier(record: DoraRecord) -> str:
    """Elite: ≤5 %; high: ≤10 %; medium: ≤15 % (published bands vary)."""
    return _tier(record.change_failure_rate_pct, 5.0, 10.0, 15.0, False)


def restore_tier(record: DoraRecord) -> str:
    """Elite: <1 h; high: <1 day; medium: <1 week (hours)."""
    return _tier(record.time_to_restore_hours, 1.0, 24.0, 168.0, False)


#: (label, per-metric tier function) — shared by HTML and PDF rendering.
DORA_TIER_FUNCS = (
    ("Deploy freq/day", deployment_frequency_tier),
    ("Lead time (h)", lead_time_tier),
    ("CFR (%)", change_failure_tier),
    ("MTTR (h)", restore_tier),
)


def unit_tier(record: DoraRecord) -> str:
    """Overall tier of a unit = its worst known per-metric tier."""
    tiers = [func(record) for _label, func in DORA_TIER_FUNCS]
    known = [t for t in tiers if t != TIER_UNKNOWN]
    if not known:
        return TIER_UNKNOWN
    return min(known, key=TIER_ORDER.index)


def parse_delivery(data: Any) -> DeliveryRegister:
    """
    Build a DeliveryRegister from an already-parsed JSON object.

    Accepts {"dora": [...], "quality": [...]} (either may be missing) and,
    for single-kind files from the sources CLI, {kind, records}.

    Raises:
        ValueError: On structural errors or records without a unit.
    """
    if not isinstance(data, dict):
        raise ValueError("Delivery file must be a JSON object.")
    if "records" in data and "dora" not in data and "quality" not in data:
        kind = data.get("kind")
        if kind == KIND_DORA:
            data = {"dora": data["records"]}
        elif kind == KIND_QUALITY:
            data = {"quality": data["records"]}
        else:
            raise ValueError(f"Delivery file carries kind '{kind}' — "
                             f"expected 'dora' or 'quality'.")

    def _records(key: str, kind: str) -> list:
        raw = data.get(key, [])
        if not isinstance(raw, list):
            raise ValueError(f"Delivery file: '{key}' must be a list.")
        out = []
        for i, entry in enumerate(raw):
            if not isinstance(entry, dict):
                raise ValueError(f"{key} record #{i + 1} is not an object.")
            record = record_from_dict(kind, entry)
            if not record.unit.strip():  # type: ignore[union-attr]
                raise ValueError(f"{key} record #{i + 1} has no 'unit'.")
            out.append(record)
        return out

    return DeliveryRegister(
        dora=_records("dora", KIND_DORA),
        quality=_records("quality", KIND_QUALITY),
    )


def load_delivery(path: Path) -> DeliveryRegister:
    """Read and validate a delivery register JSON file."""
    return parse_delivery(json.loads(Path(path).read_text(encoding="utf-8")))


def save_delivery(path: Path, register: DeliveryRegister) -> None:
    """Write a DeliveryRegister ({schema, dora, quality})."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(
        {"schema": DORA_SCHEMA_VERSION,
         "dora": [record_to_dict(r) for r in register.dora],
         "quality": [record_to_dict(r) for r in register.quality]},
        indent=2, ensure_ascii=False), encoding="utf-8")
