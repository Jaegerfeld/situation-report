# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       12.10.2026
# Geändert:       12.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests der Rechnung: Score je Dimension, Konfidenz aus dem
#   Beleggrad, „unbekannt" senkt die Konfidenz und nicht den Score, Median
#   und Spannweite über mehrere Bewertungen, leere Zellen.
# =============================================================================

from __future__ import annotations

from datetime import date

from harmonisation.examples import EXAMPLE_CATALOGUE
from harmonisation.model import (
    EVIDENCE_DOCUMENTED,
    EVIDENCE_ESTIMATED,
    EVIDENCE_HEARSAY,
    Answer,
    Assessment,
    Process,
    Workspace,
    parse_catalogue,
)
from harmonisation.score import (
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    matrix,
    score_dimension,
    summarise,
)

CAT = parse_catalogue(EXAMPLE_CATALOGUE)
BV = CAT.dimensions[0]   # business_value, bv1..bv8
PROC = (Process("p", "P"),)


def _assessment(values: dict[str, int | None], evidence: str = EVIDENCE_ESTIMATED,
                who: str = "a", day: date = date(2026, 10, 1)) -> Assessment:
    return Assessment("p", who, day, {q: Answer(v, evidence) for q, v in values.items()})


class TestScoreDimension:
    def test_mean_of_answered_scaled_to_hundred(self) -> None:
        s = score_dimension(_assessment({"bv1": 4, "bv2": 2, "bv3": 0}), BV)
        assert s.score == 50.0 and s.answered == 3 and s.total == 8

    def test_unknown_lowers_confidence_not_score(self) -> None:
        full = _assessment({f"bv{i}": 4 for i in range(1, 9)}, EVIDENCE_DOCUMENTED)
        half = _assessment({**{f"bv{i}": 4 for i in range(1, 5)},
                            **{f"bv{i}": None for i in range(5, 9)}}, EVIDENCE_DOCUMENTED)
        assert score_dimension(full, BV).score == score_dimension(half, BV).score == 100.0
        assert score_dimension(full, BV).confidence == CONFIDENCE_HIGH
        assert score_dimension(half, BV).confidence == CONFIDENCE_MEDIUM

    def test_nothing_answered_gives_no_score(self) -> None:
        s = score_dimension(_assessment({}), BV)
        assert s.score is None and s.confidence == CONFIDENCE_LOW

    def test_confidence_bands_follow_the_documented_share(self) -> None:
        def with_documented(n: int) -> str:
            answers = {f"bv{i}": Answer(2, EVIDENCE_DOCUMENTED if i <= n else EVIDENCE_HEARSAY)
                       for i in range(1, 9)}
            return score_dimension(Assessment("p", "a", date(2026, 1, 1), answers), BV).confidence
        assert with_documented(8) == CONFIDENCE_HIGH
        assert with_documented(6) == CONFIDENCE_HIGH      # 6/8 ≥ 2/3
        assert with_documented(5) == CONFIDENCE_MEDIUM    # 5/8 ≥ 1/3
        assert with_documented(3) == CONFIDENCE_MEDIUM    # 3/8 ≥ 1/3
        assert with_documented(2) == CONFIDENCE_LOW


class TestSummarise:
    def test_median_and_spread_over_assessments(self) -> None:
        ws = Workspace(CAT, PROC, (
            _assessment({"bv1": 4}, who="x"),            # 100
            _assessment({"bv1": 2}, who="y"),            # 50
            _assessment({"bv1": 0}, who="z"),            # 0
        ))
        cell = summarise(ws, "p", BV)
        assert cell.score == 50.0 and cell.spread == 100.0 and cell.assessments == 3
        assert cell.answered == 3 and cell.total == 24

    def test_single_assessment_has_no_spread(self) -> None:
        ws = Workspace(CAT, PROC, (_assessment({"bv1": 3}),))
        cell = summarise(ws, "p", BV)
        assert cell.score == 75.0 and cell.spread is None

    def test_empty_assessment_does_not_count(self) -> None:
        ws = Workspace(CAT, PROC, (_assessment({"bv1": 3}), _assessment({}, who="b")))
        assert summarise(ws, "p", BV).assessments == 1

    def test_confidence_is_pooled_over_all_assessments(self) -> None:
        documented = _assessment({f"bv{i}": 3 for i in range(1, 9)}, EVIDENCE_DOCUMENTED, "x")
        hearsay = _assessment({f"bv{i}": 3 for i in range(1, 9)}, EVIDENCE_HEARSAY, "y")
        ws = Workspace(CAT, PROC, (documented, hearsay))
        assert summarise(ws, "p", BV).confidence == CONFIDENCE_MEDIUM   # 8/16

    def test_no_assessments_at_all(self) -> None:
        cell = summarise(Workspace(CAT, PROC, ()), "p", BV)
        assert cell.score is None and cell.assessments == 0 and cell.confidence == CONFIDENCE_LOW

    def test_matrix_covers_every_process_and_dimension(self) -> None:
        ws = Workspace(CAT, (Process("a", "A"), Process("b", "B")), ())
        m = matrix(ws)
        assert set(m) == {"a", "b"}
        assert set(m["a"]) == {"business_value", "transparency", "it_operations"}
