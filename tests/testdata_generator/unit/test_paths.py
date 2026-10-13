# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       13.10.2026
# Geändert:       13.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Tests der Stage-Pfade (0.38.0): Invarianten des Samplers (nie unter die
#   erste Stufe, offene Vorgänge berühren die Abschlussstufe nie, Abbrüche
#   enden in der Endstufe ohne Abschluss, realism 0 = alte Kette,
#   Determinismus), Parkstufen-Erkennung, und die Kalibrierung gegen den
#   echten ART_A: bei realism 0,7 müssen Paarvielfalt, Rückwärts- und
#   Schleifenanteil, Sprünge, Abbrüche und der Median der Übergänge je
#   Vorgang in den Korridoren des echten Datensatzes liegen.
# =============================================================================

from __future__ import annotations

import collections
import dataclasses
import random
import statistics
from datetime import date
from pathlib import Path

import pytest

from testdata_generator.generator import GeneratorConfig, generate
from testdata_generator.paths import (
    MAX_KNOBS,
    PathSpec,
    RealismKnobs,
    detect_parking,
    knobs_at,
    sample_path,
)
from testdata_generator.workflow_parser import parse_workflow

WORKFLOW = Path(__file__).resolve().parents[3] / "testdata_generator" / "workflow_ART_A.txt"
STAGES = ["Funnel", "Analysis", "Program Backlog", "Implementation", "Blocker",
          "Validating on Staging", "Deploying to Production", "Releasing", "Done"]
FIRST, CLOSED, PARK, FINAL = 1, 7, 4, 8


def _spec(target: int, realism: float, backflow: float = 0.1) -> PathSpec:
    return PathSpec(n_stages=len(STAGES), first_idx=FIRST, closed_idx=CLOSED,
                    target_idx=target, parking_idx=PARK, backflow_prob=backflow,
                    knobs=knobs_at(realism))


class TestKnobs:
    def test_zero_switches_everything_off(self) -> None:
        assert all(v == 0 for v in knobs_at(0).__dict__.values())

    def test_one_is_the_maximum_and_clamped(self) -> None:
        assert knobs_at(1) == MAX_KNOBS == knobs_at(7)
        assert knobs_at(-1) == knobs_at(0)

    def test_half_is_linear(self) -> None:
        assert knobs_at(0.5).skip == pytest.approx(MAX_KNOBS.skip / 2)


class TestParking:
    def test_detected_by_name_never_first_or_last(self) -> None:
        assert detect_parking(STAGES) == PARK
        assert detect_parking(["Blocker", "Work", "Done"]) is None
        assert detect_parking(["Todo", "Work", "On Hold"]) is None
        assert detect_parking(["Todo", "On Hold", "Done"]) == 1

    def test_configured_name_wins_or_none(self) -> None:
        assert detect_parking(STAGES, "Validating on Staging") == 5
        assert detect_parking(STAGES, "Nope") is None


class TestSamplerInvariants:
    @pytest.mark.parametrize("realism", [0.0, 0.5, 1.0])
    def test_open_issue_never_touches_closed_and_ends_at_target(self, realism) -> None:
        rng = random.Random(3)
        for target in (FIRST, 2, 3, 5, 6):
            for _ in range(200):
                path = sample_path(_spec(target, realism), rng)
                assert CLOSED not in path and FINAL not in path
                assert not path or path[-1] == target
                assert all(i >= FIRST for i in path)       # the To-Do zone is left once

    @pytest.mark.parametrize("realism", [0.0, 0.5, 1.0])
    def test_completing_issue_reaches_closed_or_is_cancelled(self, realism) -> None:
        rng = random.Random(4)
        cancelled = archived = 0
        for _ in range(400):
            path = sample_path(_spec(CLOSED, realism), rng)
            if CLOSED in path:
                assert path[-1] in (CLOSED, FINAL)
                archived += path[-1] == FINAL
            else:
                assert realism > 0 and path[-1] == FINAL      # cancelled, never closed
                cancelled += 1
        if realism == 0:
            assert cancelled == archived == 0
        else:
            assert cancelled > 0 and archived > 0

    def test_backflow_never_below_first_stage(self) -> None:
        rng = random.Random(5)
        for _ in range(300):
            path = sample_path(_spec(CLOSED, 1.0, backflow=0.6), rng)
            below = [i for i in path if i < FIRST]
            assert not below

    def test_realism_zero_is_the_classic_chain(self) -> None:
        rng = random.Random(6)
        for _ in range(100):
            path = sample_path(_spec(CLOSED, 0.0, backflow=0.3), rng)
            assert path[-1] == CLOSED
            for a, b in zip([0] + path, path):
                assert b in (a + 1, a - 1) and b != a      # one step, no loops, no skips

    def test_parking_is_entered_and_left_to_the_same_stage(self) -> None:
        rng = random.Random(8)
        seen = 0
        for _ in range(300):
            path = [0] + sample_path(_spec(CLOSED, 1.0), rng)
            for i, stage in enumerate(path):
                if stage == PARK and i + 1 < len(path):
                    assert path[i + 1] == path[i - 1]
                    seen += 1
        assert seen > 0

    def test_deterministic_per_seed(self) -> None:
        a = [sample_path(_spec(CLOSED, 0.7), random.Random(11)) for _ in range(5)]
        b = [sample_path(_spec(CLOSED, 0.7), random.Random(11)) for _ in range(5)]
        assert a == b


def _measure(realism: float, seed: int, **extra) -> dict:
    wf = parse_workflow(WORKFLOW)
    cfg = GeneratorConfig(project_key="G", issue_count=533, from_date=date(2025, 1, 1),
                          to_date=date(2025, 12, 31), seed=seed, realism=realism, **extra)
    seqs = [[h["items"][0]["toString"] for h in iss["changelog"]["histories"]]
            for iss in generate(wf, cfg)["issues"]]
    idx = {s: i for i, s in enumerate(wf.stages)}
    pairs: collections.Counter = collections.Counter()
    back = loops = skips = cancels = 0
    per = []
    for st in seqs:
        per.append(len(st))
        for a, b in zip(st, st[1:]):
            pairs[(a, b)] += 1
            if a == b:
                loops += 1
            elif idx[b] < idx[a]:
                back += 1
            else:
                skips += idx[b] - idx[a] > 1
                cancels += b == "Done" and a != "Releasing"
    tot = sum(pairs.values()) or 1
    return {"pairs": len(pairs), "back": back / tot, "loops": loops / tot, "skips": skips,
            "cancels": cancels, "median": statistics.median(per), "transitions": tot}


class TestCalibrationAgainstArtA:
    """Real ART_A (458 issues, 1404 transitions): 40 pairs, 12.0 % backward,
    7.5 % self-loops, 358 skips, 149 entries into Done not from Releasing,
    median 4 transitions per issue."""

    @pytest.mark.parametrize("seed", [1, 2])
    def test_realism_0_7_lands_in_the_corridors(self, seed) -> None:
        m = _measure(0.7, seed, backflow_prob=0.1)
        assert 30 <= m["pairs"] <= 60
        assert 0.08 <= m["back"] <= 0.18
        assert 0.04 <= m["loops"] <= 0.11
        assert m["skips"] >= 150 and m["cancels"] >= 40
        assert m["median"] <= 6

    def test_pattern_mode_gets_the_same_untidiness(self) -> None:
        m = _measure(0.7, 1, mean_cycle_days=30, pattern="triangle")
        assert m["pairs"] >= 30 and m["loops"] >= 0.04 and m["back"] >= 0.05

    def test_realism_zero_is_as_tidy_as_before(self) -> None:
        m = _measure(0.0, 1, backflow_prob=0.1)
        assert m["pairs"] <= 12 and m["loops"] == 0 and m["skips"] == 0 and m["cancels"] == 0
        assert m["median"] >= 6

    def test_more_realism_more_variety(self) -> None:
        low, high = _measure(0.3, 1), _measure(1.0, 1)
        assert high["pairs"] >= low["pairs"] and high["loops"] > low["loops"]


class TestConfigSurface:
    def test_knobs_dataclass_is_frozen(self) -> None:
        with pytest.raises(dataclasses.FrozenInstanceError):
            MAX_KNOBS.skip = 0.5  # type: ignore[misc]

    def test_realism_knobs_default_values_are_probabilities(self) -> None:
        assert all(0 < v <= 1 for v in RealismKnobs().__dict__.values())
