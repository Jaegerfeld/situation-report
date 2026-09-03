# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   SLO-Register (Roadmap C1): liest die vom Quellen-Framework (sources)
#   erzeugten SLO-Records und leitet ZENTRAL Error-Budget und Status ab —
#   dieselbe Regel für jede Quelle, egal ob Prometheus, Datei-Export oder
#   künftige Provider: Budget verbraucht = (100−SLI)/(100−Ziel); Status
#   met | at_risk (Restbudget < 25 %) | breached (SLI unter Ziel) |
#   unknown (kein SLI). Zuverlässigkeit gemessen & budgetiert („SRE with
#   Azure") — die technische Ergänzung zur ökonomischen Flow-Sicht.
# =============================================================================

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sources.base import KIND_SLO, SloRecord, record_from_dict, record_to_dict

SLO_SCHEMA_VERSION = 1

SLO_MET = "met"
SLO_AT_RISK = "at_risk"
SLO_BREACHED = "breached"
SLO_UNKNOWN = "unknown"
#: Display order — most urgent first.
SLO_STATUS_ORDER = (SLO_BREACHED, SLO_AT_RISK, SLO_MET, SLO_UNKNOWN)

#: Below this remaining error budget, a met SLO counts as at risk.
_AT_RISK_BUDGET_PCT = 25.0


@dataclass
class SloRegister:
    """All SLO records of one solution. An empty register is valid."""
    records: list[SloRecord] = field(default_factory=list)


def error_budget_remaining_pct(record: SloRecord) -> float | None:
    """
    Remaining error budget in percent (may be negative when breached).

    Budget = 100 − target; consumed = (100 − SLI) / budget. A target of
    100 % has no budget — any miss is a breach (returns 0/None handling
    via status). None when no SLI was measured.
    """
    if record.sli_pct is None:
        return None
    budget = 100.0 - record.target_pct
    if budget <= 0:
        return 100.0 if record.sli_pct >= record.target_pct else 0.0
    consumed = (100.0 - record.sli_pct) / budget
    return round((1.0 - consumed) * 100.0, 1)


def slo_status(record: SloRecord) -> str:
    """Central status rule — identical for every source."""
    if record.sli_pct is None:
        return SLO_UNKNOWN
    if record.sli_pct < record.target_pct:
        return SLO_BREACHED
    remaining = error_budget_remaining_pct(record)
    if remaining is not None and remaining < _AT_RISK_BUDGET_PCT:
        return SLO_AT_RISK
    return SLO_MET


def parse_slo(data: Any) -> SloRegister:
    """
    Build an SloRegister from an already-parsed JSON object.

    Accepts the sources-CLI output ({schema, kind, records}) and the plain
    {"records": [...]} shape.

    Raises:
        ValueError: On structural errors (no records list, bad record,
                    wrong kind, missing service/target).
    """
    if not isinstance(data, dict):
        raise ValueError("SLO file must be a JSON object.")
    kind = data.get("kind")
    if kind not in (None, KIND_SLO):
        raise ValueError(f"SLO file carries kind '{kind}' — expected 'slo'.")
    raw = data.get("records")
    if not isinstance(raw, list):
        raise ValueError("SLO file needs a 'records' list (may be empty).")
    records: list[SloRecord] = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValueError(f"SLO record #{i + 1} is not an object.")
        record = record_from_dict(KIND_SLO, entry)
        assert isinstance(record, SloRecord)
        if not record.service.strip():
            raise ValueError(f"SLO record #{i + 1} has no 'service'.")
        records.append(record)
    return SloRegister(records=records)


def load_slo(path: Path) -> SloRegister:
    """Read and validate an SLO register JSON file."""
    return parse_slo(json.loads(Path(path).read_text(encoding="utf-8")))


def save_slo(path: Path, register: SloRegister) -> None:
    """Write an SloRegister in the sources schema (roundtrip-safe)."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(
        {"schema": SLO_SCHEMA_VERSION, "kind": KIND_SLO,
         "records": [record_to_dict(r) for r in register.records]},
        indent=2, ensure_ascii=False), encoding="utf-8")
