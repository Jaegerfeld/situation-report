# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       14.10.2026
# Geändert:       14.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Wecker-Register (Roadmap D4-Rest, Muster M4 der KI-Denkschrift:
#   Frühindikator + Schwelle + vereinbarte Reaktion). Der Stab vereinbart im
#   Ritual, welche Kennzahl ab welchem Wert welche Entscheidung auslöst; das
#   Werkzeug prüft, es erfindet keine Schwellen (Regeln von P4). Die Kennzahl
#   wird mit der Pfad-Syntax des Fakten-Index (D3) adressiert — alles, was
#   sich fragen lässt, lässt sich wecken: S1/units(ART Alpha-3).p85_ct,
#   D/total.open (mit unit "%" relativ), S1/governance.dependencies.count(blocked).
#   Owner ist ein Team (Leitplanke b). Schema v1, Standardbibliothek.
# =============================================================================

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

POINTS_SCHEMA_VERSION = 1

OPS = (">=", "<=", ">", "<")
UNIT_ABSOLUTE = ""
UNIT_PERCENT = "%"

DP_TRIGGERED = "triggered"
DP_BELOW = "below"
DP_NOT_AGREED = "not_agreed"
DP_NOT_COMPUTABLE = "not_computable"
DP_STATUS_ORDER = (DP_TRIGGERED, DP_BELOW, DP_NOT_AGREED, DP_NOT_COMPUTABLE)

_METRIC_RE = re.compile(r"^(S1|S0|D|H)/[A-Za-z0-9_.()\- x×/]+$")


@dataclass
class DecisionPoint:
    """
    One agreed alarm: a metric path, a comparison, a threshold, the question
    the alarm puts on the agenda and the reaction the staff agreed on.
    ``threshold`` None = not agreed yet (shown, never alarms).
    """
    point_id: str
    title: str
    metric: str
    op: str = ">="
    threshold: float | None = None
    unit: str = UNIT_ABSOLUTE
    question: str = ""
    reaction: str = ""
    team: str = ""
    agreed_on: date | None = None

    @property
    def agreed(self) -> bool:
        return self.threshold is not None

    def compare(self, value: float) -> bool:
        if self.threshold is None:
            return False
        return {">=": value >= self.threshold, "<=": value <= self.threshold,
                ">": value > self.threshold, "<": value < self.threshold}[self.op]


@dataclass
class DecisionPointRegister:
    """All agreed decision points of one solution. Empty is valid."""
    points: list[DecisionPoint] = field(default_factory=list)


def _day(raw: Any, pid: str) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw))
    except ValueError as exc:
        raise ValueError(f"Decision point '{pid}': 'agreed_on' must be YYYY-MM-DD.") from exc


def parse_decision_points(data: Any) -> DecisionPointRegister:
    """
    Build the register from a parsed JSON object.

    Raises:
        ValueError: Missing list, empty id/title/metric, duplicate id, metric
                    not in path syntax, unknown op, non-numeric threshold,
                    unknown unit, bad date.
    """
    if not isinstance(data, dict):
        raise ValueError("Decision-points file must be a JSON object.")
    raw = data.get("points")
    if not isinstance(raw, list):
        raise ValueError("Decision-points file needs a 'points' list (may be empty).")
    points: list[DecisionPoint] = []
    seen: set[str] = set()
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValueError(f"Decision point #{i + 1} is not an object.")
        pid = str(entry.get("id", "")).strip()
        if not pid:
            raise ValueError(f"Decision point #{i + 1} is missing a non-empty 'id'.")
        if pid in seen:
            raise ValueError(f"Duplicate decision-point id '{pid}'.")
        seen.add(pid)
        title = str(entry.get("title", "")).strip()
        metric = str(entry.get("metric", "")).strip()
        if not title or not metric:
            raise ValueError(f"Decision point '{pid}' needs non-empty 'title' and 'metric'.")
        if not _METRIC_RE.match(metric):
            raise ValueError(
                f"Decision point '{pid}': 'metric' must be a fact path such as "
                f"S1/units(ART A).p85_ct or D/total.open (got {metric!r}).")
        op = str(entry.get("op", ">=")).strip() or ">="
        if op not in OPS:
            raise ValueError(f"Decision point '{pid}': 'op' must be one of {', '.join(OPS)}.")
        threshold_raw: Any = entry.get("threshold")
        threshold: float | None = None
        if threshold_raw is not None and threshold_raw != "":
            try:
                threshold = float(threshold_raw)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Decision point '{pid}': 'threshold' must be a number.") from exc
        unit = str(entry.get("unit", UNIT_ABSOLUTE)).strip()
        if unit not in (UNIT_ABSOLUTE, UNIT_PERCENT):
            raise ValueError(f"Decision point '{pid}': 'unit' must be '' or '%'.")
        points.append(DecisionPoint(
            point_id=pid, title=title, metric=metric, op=op, threshold=threshold, unit=unit,
            question=str(entry.get("question", "")).strip(),
            reaction=str(entry.get("reaction", "")).strip(),
            team=str(entry.get("team", entry.get("owner", ""))).strip(),
            agreed_on=_day(entry.get("agreed_on"), pid)))
    return DecisionPointRegister(points=points)


def load_decision_points(path: Path) -> DecisionPointRegister:
    return parse_decision_points(json.loads(Path(path).read_text(encoding="utf-8")))


def decision_points_to_dict(register: DecisionPointRegister) -> dict[str, Any]:
    out = []
    for p in register.points:
        entry: dict[str, Any] = {"id": p.point_id, "title": p.title, "metric": p.metric, "op": p.op}
        if p.threshold is not None:
            entry["threshold"] = p.threshold
        if p.unit:
            entry["unit"] = p.unit
        for key in ("question", "reaction", "team"):
            if getattr(p, key):
                entry[key] = getattr(p, key)
        if p.agreed_on:
            entry["agreed_on"] = p.agreed_on.isoformat()
        out.append(entry)
    return {"schema": POINTS_SCHEMA_VERSION, "points": out}


def save_decision_points(path: Path, register: DecisionPointRegister) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(decision_points_to_dict(register), indent=2, ensure_ascii=False),
                      encoding="utf-8")
