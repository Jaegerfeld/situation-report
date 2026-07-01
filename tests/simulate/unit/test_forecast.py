# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       01.07.2026
# Geändert:       01.07.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für simulate.forecast: empirische Verteilung, Kapazitäts- und
#   Termin-Forecast (inkl. Scope-Wachstum), Exceedance-Perzentile und
#   Reproduzierbarkeit. Deterministisch über geseedete random.Random-Instanzen
#   bzw. entartete (konstante) Verteilungen.
# =============================================================================

from __future__ import annotations

import random
from datetime import date

import pytest

from simulate.forecast import (
    HowManyForecast,
    ThroughputSample,
    how_many,
    probability_at_least,
    probability_of_completing,
    when_done,
)


# Entartete Verteilung: an jedem Tag genau `n` Items -> deterministische Läufe.
def _constant(n: int) -> ThroughputSample:
    return ThroughputSample(values=(n,), weights=(1,), days_observed=10)


class TestThroughputSample:
    def test_from_daily_counts_builds_distribution_incl_zero_days(self) -> None:
        s = ThroughputSample.from_daily_counts([0, 0, 1, 2, 2, 3])
        assert s.values == (0, 1, 2, 3)
        assert s.weights == (2, 1, 2, 1)
        assert s.days_observed == 6
        assert s.mean_per_day == pytest.approx((0 + 1 + 4 + 3) / 6)

    def test_empty(self) -> None:
        s = ThroughputSample.from_daily_counts([])
        assert s.is_empty
        assert s.mean_per_day == 0.0


class TestHowMany:
    def test_constant_distribution_is_deterministic(self) -> None:
        fc = how_many(_constant(2), horizon_days=10, runs=100, rng=random.Random(1))
        assert set(fc.totals) == {20}
        assert all(v == 20 for v in fc.percentiles.values())

    def test_exceedance_is_monotone_in_confidence(self) -> None:
        s = ThroughputSample.from_daily_counts([0, 1, 2, 3, 4, 1, 2, 2, 0, 3])
        fc = how_many(s, horizon_days=30, runs=5000, rng=random.Random(7))
        # Höhere Konfidenz -> kleinere (oder gleiche) garantierte Menge.
        assert fc.percentiles[95] <= fc.percentiles[85] <= fc.percentiles[75] <= fc.percentiles[50]

    def test_reproducible_with_same_seed(self) -> None:
        s = ThroughputSample.from_daily_counts([0, 1, 2, 3, 1, 2])
        a = how_many(s, 20, 500, rng=random.Random(42))
        b = how_many(s, 20, 500, rng=random.Random(42))
        assert a.totals == b.totals

    def test_empty_sample_yields_zero(self) -> None:
        fc = how_many(ThroughputSample.from_daily_counts([]), 10, 50, rng=random.Random(1))
        assert set(fc.totals) == {0}

    def test_runs_must_be_positive(self) -> None:
        with pytest.raises(ValueError):
            how_many(_constant(2), 10, 0, rng=random.Random(1))


class TestWhenDone:
    def test_constant_no_growth(self) -> None:
        fc = when_done(_constant(5), backlog=50, runs=100, rng=random.Random(1))
        assert set(fc.completion_days) == {10}
        assert fc.not_completed == 0
        assert all(v == 10 for v in fc.percentiles.values())

    def test_dates_mapped_from_start_date(self) -> None:
        start = date(2026, 7, 1)
        fc = when_done(_constant(5), backlog=50, runs=10, rng=random.Random(1),
                       start_date=start)
        assert fc.dates[50] == date(2026, 7, 11)  # 10 Tage später

    def test_scope_growth_extends_completion(self) -> None:
        # 10/Tag, +10 % Splits -> netto 9/Tag -> 100 Items in 12 Tagen.
        fc = when_done(_constant(10), backlog=100, runs=50, rng=random.Random(1),
                       split_rate=0.1)
        assert set(fc.completion_days) == {12}
        assert fc.not_completed == 0

    def test_growth_outruns_throughput_never_completes(self) -> None:
        # 1/Tag, split_rate 2 -> remaining wächst -> kein Lauf wird fertig.
        fc = when_done(_constant(1), backlog=10, runs=20, rng=random.Random(1),
                       split_rate=2.0)
        assert fc.not_completed == 20
        assert fc.completion_days == []

    def test_empty_sample_never_completes(self) -> None:
        fc = when_done(ThroughputSample.from_daily_counts([]), backlog=10, runs=5,
                       rng=random.Random(1))
        assert fc.not_completed == 5

    def test_partial_completion_marks_unreachable_confidence_as_none(self) -> None:
        # Durchsatz 0 oder 2 (Mittel 1/Tag) + Scope-Wachstum, enger Cap -> ein Teil
        # der Läufe wird NICHT fertig. Perzentile über alle Läufe: Konfidenz über
        # der Fertigstellungsrate ist im Cap nicht erreichbar -> None.
        sample = ThroughputSample.from_daily_counts([0, 2])
        fc = when_done(sample, backlog=10, runs=3000, rng=random.Random(3),
                       split_rate=0.2, max_days=15, percentiles=(95, 50, 25))
        rate = len(fc.completion_days) / fc.runs * 100
        assert 0 < len(fc.completion_days) < fc.runs   # echt gemischt
        assert 25 < rate < 95                          # Rate zwischen den Stufen
        assert fc.percentiles[25] is not None          # erreichbar -> endlicher Tag
        assert fc.percentiles[95] is None              # nicht im Cap -> None

    def test_invalid_args(self) -> None:
        with pytest.raises(ValueError):
            when_done(_constant(5), backlog=0, runs=10, rng=random.Random(1))
        with pytest.raises(ValueError):
            when_done(_constant(5), backlog=10, runs=10, rng=random.Random(1),
                      split_rate=-0.1)


class TestProbability:
    def test_certain_and_impossible(self) -> None:
        s = _constant(2)  # immer 20 in 10 Tagen
        assert probability_of_completing(s, 20, 10, 100, rng=random.Random(1)) == 1.0
        assert probability_of_completing(s, 21, 10, 100, rng=random.Random(1)) == 0.0


class TestProbabilityAtLeast:
    def _fc(self) -> HowManyForecast:
        return HowManyForecast(horizon_days=10, runs=4, totals=[1, 1, 2, 3],
                               percentiles={})

    def test_point_on_exceedance_curve(self) -> None:
        fc = self._fc()
        assert probability_at_least(fc, 1) == 1.0
        assert probability_at_least(fc, 2) == 0.5
        assert probability_at_least(fc, 3) == 0.25
        assert probability_at_least(fc, 4) == 0.0

    def test_empty(self) -> None:
        fc = HowManyForecast(horizon_days=10, runs=0, totals=[], percentiles={})
        assert probability_at_least(fc, 5) == 0.0
