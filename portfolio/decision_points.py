# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       14.10.2026
# Geändert:       14.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Auswertung des Wecker-Registers (D4-Rest) gegen einen Stand: Je Wecker
#   wird der Wert über den Pfad aus dem Fakten-Index (D3) gelesen und mit
#   der vereinbarten Schwelle verglichen. Vier Zustände, alle sichtbar
#   (P4-Regel 3): ausgelöst, unterschwellig, nicht vereinbart (keine
#   Schwelle — weckt nie, P4-Regel 2), nicht berechenbar (Pfad fehlt im
#   Stand, z. B. D/… ohne Vorstand, oder Wert nicht numerisch). Relative
#   Veränderung (unit "%") wird aus S1 und S0 gerechnet. Der P4-Wecker
#   (Cross-VS-Druck) kommt als Zusatzwert S1/pressure.cross_vs herein.
#   Keine Priorisierung durch das Werkzeug: Reihenfolge ist der Zustand,
#   darin die Reihenfolge des Registers.
# =============================================================================

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .decision_points_config import (
    DP_BELOW,
    DP_NOT_AGREED,
    DP_NOT_COMPUTABLE,
    DP_STATUS_ORDER,
    DP_TRIGGERED,
    UNIT_PERCENT,
    DecisionPoint,
)

if TYPE_CHECKING:  # facts imports snapshot imports aggregator imports summary imports this module
    from .facts import FactIndex

# Path prefixes of the fact index (mirrored from portfolio.facts to avoid the import cycle).
PREFIX_NOW = "S1"
PREFIX_PREV = "S0"
PREFIX_DELTA = "D"
PRESSURE_PATH = f"{PREFIX_NOW}/pressure.cross_vs"
_NUMBER_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")

NOTE_NO_PATH = "path not in this stand"
NOTE_NOT_NUMERIC = "value is not numeric"
NOTE_NO_PREV = "needs a previous stand (S0)"
NOTE_ZERO_BASE = "previous value is 0 - no relative change"


@dataclass
class PointResult:
    """One decision point against one stand."""
    point: DecisionPoint
    status: str
    value: float | None = None
    note: str = ""

    @property
    def shown_value(self) -> str:
        if self.value is None:
            return "-"
        text = f"{self.value:.1f}".rstrip("0").rstrip(".")
        return text + (" %" if self.point.unit == UNIT_PERCENT else "")

    @property
    def shown_threshold(self) -> str:
        if self.point.threshold is None:
            return "-"
        thr = f"{self.point.threshold:.1f}".rstrip("0").rstrip(".")
        return f"{self.point.op} {thr}" + (" %" if self.point.unit == UNIT_PERCENT else "")


def _number(text: str) -> float | None:
    m = _NUMBER_RE.search(text)
    return float(m.group(0)) if m else None


def resolve_metric(metric: str, index: FactIndex, extra: Mapping[str, float] | None = None,
                   ) -> tuple[float | None, str]:
    """The numeric value behind a path: from ``extra`` first, then the index."""
    if extra and metric in extra:
        return float(extra[metric]), ""
    fact = index.by_path.get(metric)
    if fact is None:
        if metric.startswith(PREFIX_DELTA + "/") and not index.prev_as_of:
            return None, NOTE_NO_PREV
        return None, NOTE_NO_PATH
    value = _number(fact.value)
    return (value, "") if value is not None else (None, NOTE_NOT_NUMERIC)


def _relative_change(metric: str, index: FactIndex) -> tuple[float | None, str]:
    """D/… with unit %: (S1 - S0) / S0 * 100 from the two stands."""
    rest = metric.split("/", 1)[1]
    now, note = resolve_metric(f"{PREFIX_NOW}/{rest}", index)
    if now is None:
        return None, note
    if not index.prev_as_of:
        return None, NOTE_NO_PREV
    prev, note = resolve_metric(f"{PREFIX_PREV}/{rest}", index)
    if prev is None:
        return None, note
    if prev == 0:
        return None, NOTE_ZERO_BASE
    return round((now - prev) / abs(prev) * 100, 1), ""


def evaluate_point(point: DecisionPoint, index: FactIndex,
                   extra: Mapping[str, float] | None = None) -> PointResult:
    if point.unit == UNIT_PERCENT and point.metric.startswith(PREFIX_DELTA + "/"):
        value, note = _relative_change(point.metric, index)
    else:
        value, note = resolve_metric(point.metric, index, extra)
    if value is None:
        return PointResult(point, DP_NOT_COMPUTABLE, None, note)
    if not point.agreed:
        return PointResult(point, DP_NOT_AGREED, value)
    return PointResult(point, DP_TRIGGERED if point.compare(value) else DP_BELOW, value)


def evaluate_points(points: list[DecisionPoint], index: FactIndex,
                    extra: Mapping[str, float] | None = None) -> list[PointResult]:
    """All points, ordered triggered → below → not agreed → not computable (stable within)."""
    results = [evaluate_point(p, index, extra) for p in points]
    order = {s: i for i, s in enumerate(DP_STATUS_ORDER)}
    return sorted(results, key=lambda r: order[r.status])


def count_by_status(results: list[PointResult]) -> dict[str, int]:
    counts = dict.fromkeys(DP_STATUS_ORDER, 0)
    for r in results:
        counts[r.status] += 1
    return counts


def points_to_markdown(results: list[PointResult], index: FactIndex, lang: str = "de") -> str:
    """The deterministic .alarms.md: every point with its state, no judgement."""
    de = lang == "de"
    counts = count_by_status(results)
    names = ({"triggered": "ausgelöst", "below": "unterschwellig", "not_agreed": "nicht vereinbart",
              "not_computable": "nicht berechenbar"} if de else
             {"triggered": "triggered", "below": "below threshold", "not_agreed": "not agreed",
              "not_computable": "not computable"})
    lines = [f"# {'Entscheidungspunkte' if de else 'Decision points'} — {index.name} ({index.as_of})", "",
             (f"Stand: S1 = {index.as_of}" + (f", S0 = {index.prev_as_of}" if index.prev_as_of else "")
              + f" · {len(results)} {'Wecker' if de else 'points'} · "
              + " · ".join(f"{counts[s]} {names[s]}" for s in DP_STATUS_ORDER)), "",
             ("| Wecker | Kennzahl | Wert | Schwelle | Zustand | Frage | Vereinbarte Reaktion |" if de else
              "| Point | Metric | Value | Threshold | State | Question | Agreed reaction |"),
             "|---|---|---|---|---|---|---|"]
    for r in results:
        state = names[r.status] + (f" ({r.note})" if r.note else "")
        lines.append(f"| {r.point.point_id} {r.point.title} | `{r.point.metric}` | {r.shown_value} | "
                     f"{r.shown_threshold} | {state} | {r.point.question or '-'} | {r.point.reaction or '-'} |")
    lines += ["", ("Ohne vereinbarte Schwelle weckt kein Wecker; unterschwellig bleibt sichtbar. "
                   "Das Werkzeug erfindet keine Schwellen und spricht keine Empfehlung aus." if de else
                   "Without an agreed threshold no point alarms; below-threshold stays visible. "
                   "The tool invents no thresholds and makes no recommendation."), ""]
    return "\n".join(lines)
