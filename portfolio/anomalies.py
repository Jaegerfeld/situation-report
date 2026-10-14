# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       14.10.2026
# Geändert:       14.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Auffälligkeits-Hinweise aus einer Snapshot-Reihe (Roadmap D4, Schritt 2).
#   Je numerischem Fakt des jüngsten Stands (Kennzahlen gepoolt und je
#   Einheit, Registerzählungen) werden Median und MAD der früheren Stände
#   gerechnet; liegt der aktuelle Wert mehr als k · MAD vom Median entfernt,
#   ist er auffällig. Robust (Median/MAD statt Mittelwert/σ), Standard-
#   bibliothek, deterministisch. Das Ergebnis sind HINWEISE — Kandidaten für
#   einen Wecker, den der Stab vereinbart —, nie Alarme (Entscheidung Robert
#   14.10.2026, P4-Regel 2: ohne vereinbarte Schwelle weckt nichts). Weniger
#   als vier Stände: keine Statistik. Höchstens zehn Hinweise, der Rest
#   wird gezählt — gegen Alarm-Müdigkeit.
# =============================================================================

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from statistics import median

from .facts import FactIndex, build_fact_index
from .snapshot import Snapshot, parse_snapshot

MIN_STANDS = 4
MAD_FACTOR = 3.0
HINT_LIMIT = 10

_NUMBER_RE = re.compile(r"^[-+]?\d+(?:\.\d+)?")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")


@dataclass(frozen=True)
class Hint:
    """One metric whose latest value stands out against its own history."""
    path: str
    label: str
    value: float
    median: float
    mad: float
    score: float          # |value - median| / MAD
    prior_min: float
    prior_max: float
    stands: int           # prior stands that carried the path


@dataclass
class AnomalyReport:
    stands: int                       # stands in the series (incl. the latest)
    considered: int = 0               # paths with enough history
    hints: list[Hint] = field(default_factory=list)
    more: int = 0                     # hints beyond the limit
    latest_as_of: str = ""

    @property
    def enough(self) -> bool:
        return self.stands >= MIN_STANDS


def load_series(folder: Path) -> list[Snapshot]:
    """Every readable snapshot in the folder, oldest first (one per as_of, last wins)."""
    stands: dict[str, Snapshot] = {}
    for path in sorted(Path(folder).glob("*.json")):
        try:
            snap = parse_snapshot(json.loads(path.read_text(encoding="utf-8")))
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            continue
        stands[snap.as_of.isoformat()] = snap
    return [stands[k] for k in sorted(stands)]


def numeric_facts(index: FactIndex) -> dict[str, tuple[float, str]]:
    """path -> (value, label) for the numeric S1 facts (dates and texts excluded)."""
    out: dict[str, tuple[float, str]] = {}
    for f in index.facts:
        if not f.path.startswith("S1/") or f.value.startswith("text:") or _DATE_RE.match(f.value):
            continue
        m = _NUMBER_RE.match(f.value)
        if m:
            out[f.path] = (float(m.group(0)), f.label)
    return out


def detect_anomalies(series: list[Snapshot], min_stands: int = MIN_STANDS,
                     factor: float = MAD_FACTOR, limit: int = HINT_LIMIT) -> AnomalyReport:
    """
    Compare the latest stand against the earlier ones, path by path.

    A path needs values in at least ``min_stands - 1`` earlier stands; with a
    MAD of 0 (a constant history) nothing is said — one deviation from a
    flat line is not a statistic. Hints are sorted by score, strongest first.
    """
    report = AnomalyReport(stands=len(series))
    if len(series) < min_stands:
        return report
    latest = series[-1]
    report.latest_as_of = latest.as_of.isoformat()
    history = [numeric_facts(build_fact_index(s)) for s in series[:-1]]
    hints: list[Hint] = []
    for path, (value, label) in numeric_facts(build_fact_index(latest)).items():
        values = [h[path][0] for h in history if path in h]
        if len(values) < min_stands - 1:
            continue
        report.considered += 1
        med = median(values)
        mad = median(abs(v - med) for v in values)
        if mad == 0:
            continue
        score = abs(value - med) / mad
        if score > factor:
            hints.append(Hint(path, label, value, med, mad, round(score, 1), min(values), max(values),
                              len(values)))
    hints.sort(key=lambda h: (-h.score, h.path))
    report.hints, report.more = hints[:limit], max(0, len(hints) - limit)
    return report


def _fmt(v: float) -> str:
    return f"{v:.1f}".rstrip("0").rstrip(".")


def hints_to_markdown(report: AnomalyReport, lang: str = "de") -> str:
    """The hints section of the alarms protocol."""
    de = lang == "de"
    lines = [f"## {'Auffälligkeits-Hinweise — Kandidaten für Wecker' if de else 'Anomaly hints — candidates for decision points'}", ""]
    if not report.enough:
        lines.append("_Weniger als vier Stände in der Reihe — keine Statistik "
                      f"({report.stands} Stand/Stände)._" if de else
                      f"_Fewer than four stands in the series — no statistics ({report.stands} stand(s))._")
        return "\n".join(lines + [""])
    lines.append(f"{report.stands} Stände bis {report.latest_as_of} · {report.considered} Kennzahlen mit Historie · "
                  f"{len(report.hints) + report.more} auffällig (|Wert − Median| > {_fmt(MAD_FACTOR)} · MAD)"
                  if de else
                  f"{report.stands} stands up to {report.latest_as_of} · {report.considered} metrics with history · "
                  f"{len(report.hints) + report.more} outstanding (|value − median| > {_fmt(MAD_FACTOR)} · MAD)")
    lines += ["", ("Hinweise sind keine Alarme: Ob daraus ein Wecker wird, vereinbart der Stab." if de else
                   "Hints are not alarms: whether one becomes a decision point is for the staff to agree."), ""]
    if not report.hints:
        lines.append("_" + ("keine" if de else "none") + "_")
    else:
        lines += [("| Kennzahl | Wert | Median bisher | Spanne bisher | Stärke |" if de else
                   "| Metric | Value | Median so far | Range so far | Strength |"), "|---|---|---|---|---|"]
        lines += [f"| `{h.path}` | {_fmt(h.value)} | {_fmt(h.median)} | {_fmt(h.prior_min)} – {_fmt(h.prior_max)} "
                  f"({h.stands}) | {_fmt(h.score)} × MAD |" for h in report.hints]
        if report.more:
            lines.append(f"\n_{'weitere' if de else 'further'}: {report.more}_")
    return "\n".join(lines + [""])
