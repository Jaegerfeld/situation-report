# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       12.10.2026
# Geändert:       12.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Die Rechnung hinter der Entscheider-Matrix — deterministisch, ohne
#   Urteil. Je Prozess und Dimension: Score 0–100 aus den beantworteten
#   Fragen, Konfidenz aus dem Beleggrad, bei mehreren Bewertungen Median
#   und Spannweite. Drei Zahlen nebeneinander, kein Gesamtscore: Business
#   Value, Transparenz und IT/Betrieb sind drei verschiedene Dinge, und eine
#   Zahl, die sie verrechnet, verstünde niemand mehr. Was aus den Zahlen
#   folgt, trägt das Board ein — hier wird nichts empfohlen.
# =============================================================================

from __future__ import annotations

from dataclasses import dataclass
from statistics import median

from .model import (
    EVIDENCE_DOCUMENTED,
    EVIDENCE_HEARSAY,
    SCALE_MAX,
    Assessment,
    Dimension,
    Workspace,
)

CONFIDENCE_HIGH = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW = "low"

#: Anteil belegter Antworten, ab dem die Konfidenz hoch bzw. mittel ist.
_CONF_HIGH_FROM = 2 / 3
_CONF_MEDIUM_FROM = 1 / 3


@dataclass(frozen=True)
class DimensionScore:
    """One assessment, one dimension."""
    score: float | None           # 0–100; None when nothing was answered
    answered: int                 # Fragen mit Wert
    total: int                    # Fragen der Dimension
    documented: int               # Antworten mit Beleg
    hearsay: int                  # Antworten vom Hörensagen

    @property
    def confidence(self) -> str:
        """Share of documented answers over ALL questions — unknown lowers it."""
        if self.total == 0:
            return CONFIDENCE_LOW
        share = self.documented / self.total
        if share >= _CONF_HIGH_FROM:
            return CONFIDENCE_HIGH
        if share >= _CONF_MEDIUM_FROM:
            return CONFIDENCE_MEDIUM
        return CONFIDENCE_LOW


@dataclass(frozen=True)
class CellSummary:
    """All assessments of one process folded into one matrix cell."""
    score: float | None           # Median der Einzel-Scores
    spread: float | None          # max − min, None bei < 2 Scores
    assessments: int              # Bewertungen mit mindestens einer Antwort
    answered: int                 # Summe beantworteter Fragen
    total: int                    # Summe aller Fragen über die Bewertungen
    confidence: str


def score_dimension(assessment: Assessment, dimension: Dimension) -> DimensionScore:
    """Mean of the answered questions, scaled to 0–100."""
    values: list[int] = []
    documented = hearsay = 0
    for q in dimension.questions:
        ans = assessment.answers.get(q.id)
        if ans is None:
            continue
        if ans.value is not None:
            values.append(ans.value)
            if ans.evidence == EVIDENCE_DOCUMENTED:
                documented += 1
            elif ans.evidence == EVIDENCE_HEARSAY:
                hearsay += 1
    score = round(sum(values) / len(values) / SCALE_MAX * 100, 1) if values else None
    return DimensionScore(score, len(values), len(dimension.questions), documented, hearsay)


def summarise(ws: Workspace, process_id: str, dimension: Dimension) -> CellSummary:
    """
    Fold every assessment of a process into one cell.

    Median rather than mean: two people who see the same process very
    differently are a finding, not noise to average away — the spread says
    so next to the score. Confidence is pooled over all answers of all
    assessments, so three well-documented assessments beat one.
    """
    singles = [score_dimension(a, dimension)
               for a in ws.assessments if a.process == process_id]
    scored = [s for s in singles if s.score is not None]
    scores = [s.score for s in scored if s.score is not None]
    total = sum(s.total for s in singles)
    documented = sum(s.documented for s in singles)
    pooled = DimensionScore(None, sum(s.answered for s in singles), total, documented,
                            sum(s.hearsay for s in singles))
    return CellSummary(
        score=round(median(scores), 1) if scores else None,
        spread=round(max(scores) - min(scores), 1) if len(scores) >= 2 else None,
        assessments=len(scored),
        answered=pooled.answered,
        total=total,
        confidence=pooled.confidence if singles else CONFIDENCE_LOW,
    )


def matrix(ws: Workspace) -> dict[str, dict[str, CellSummary]]:
    """{process_id: {dimension_id: CellSummary}} for every process and dimension."""
    return {p.id: {d.id: summarise(ws, p.id, d) for d in ws.catalogue.dimensions}
            for p in ws.processes}
