# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       30.06.2026
# Geändert:       30.06.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Throughput-basierte Monte-Carlo-Forecast-Engine (Stil Vacanti / ProKanban).
#   Aus einer empirischen Tagesdurchsatz-Verteilung werden zwei Fragen
#   probabilistisch beantwortet:
#     - how_many():  Wie viele Items schaffen wir in N Tagen? (Kapazitäts-Forecast)
#     - when_done(): Wann ist ein Backlog von N Items fertig? (Termin-Forecast,
#                    inkl. optionalem Scope-Wachstum über eine Split-Rate)
#   Reine Standardbibliothek (random), keine numpy/pandas. Reproduzierbar über
#   eine injizierte random.Random-Instanz. Ergebnisse als Exceedance-Perzentile
#   (z. B. 85 % Konfidenz -> mindestens X Items / spätestens Tag Y).
# =============================================================================

from __future__ import annotations

import bisect
import math
import random
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta

#: Default-Konfidenzstufen (in Prozent) für Forecasts. 85/75/50 entsprechen den
#: Referenzlinien des R-Vorbilds; 95 ergänzt eine konservative Stufe.
DEFAULT_PERCENTILES: tuple[int, ...] = (95, 85, 75, 50)


def _nearest_rank(sorted_asc: Sequence[int], pct: float) -> int:
    """
    Perzentilwert nach der Nearest-Rank-Methode (für ganzzahlige Zähldaten).

    Args:
        sorted_asc: Aufsteigend sortierte Werte (nicht leer).
        pct:        Perzentil in [0, 100].

    Returns:
        Der Wert an der Nearest-Rank-Position. Bei leerer Eingabe 0.
    """
    n = len(sorted_asc)
    if n == 0:
        return 0
    rank = max(1, math.ceil(pct / 100.0 * n))
    return sorted_asc[min(rank, n) - 1]


@dataclass(frozen=True)
class ThroughputSample:
    """
    Empirische Verteilung des Tagesdurchsatzes.

    `values` und `weights` sind parallele Tupel: `values[i]` Items pro Tag wurden
    an `weights[i]` Tagen des History-Fensters beobachtet. Null-Tage (Wert 0)
    MÜSSEN enthalten sein, damit der Durchsatz nicht überschätzt wird.
    """

    values: tuple[int, ...]
    weights: tuple[int, ...]
    days_observed: int

    @classmethod
    def from_daily_counts(cls, daily_counts: Sequence[int]) -> ThroughputSample:
        """
        Baue die Verteilung aus einer Tagesreihe (ein Wert je Kalendertag).

        Args:
            daily_counts: Abgeschlossene Items je Tag über das History-Fenster,
                          inklusive Null-Tagen.

        Returns:
            ThroughputSample. Leer (keine values), wenn die Eingabe leer ist.
        """
        counter = Counter(int(c) for c in daily_counts)
        values = tuple(sorted(counter))
        weights = tuple(counter[v] for v in values)
        return cls(values=values, weights=weights, days_observed=len(daily_counts))

    @property
    def is_empty(self) -> bool:
        """True, wenn keine Beobachtungen vorliegen."""
        return self.days_observed == 0 or not self.values

    @property
    def mean_per_day(self) -> float:
        """Mittlerer Tagesdurchsatz (0.0, wenn leer)."""
        if self.is_empty:
            return 0.0
        total = sum(v * w for v, w in zip(self.values, self.weights))
        return total / self.days_observed

    def _draw(self, rng: random.Random, k: int) -> list[int]:
        """Ziehe k Tageswerte mit Zurücklegen gemäß der empirischen Verteilung."""
        return rng.choices(self.values, weights=self.weights, k=k)


@dataclass(frozen=True)
class HowManyForecast:
    """
    Ergebnis von how_many(): Verteilung der in `horizon_days` erreichten Items.

    `percentiles` ist exceedance-orientiert: Schlüssel = Konfidenz in Prozent,
    Wert = Item-Anzahl, die mit dieser Konfidenz MINDESTENS erreicht wird
    (höhere Konfidenz -> kleinere Anzahl).
    """

    horizon_days: int
    runs: int
    totals: list[int]
    percentiles: dict[int, int]


@dataclass(frozen=True)
class WhenDoneForecast:
    """
    Ergebnis von when_done(): Verteilung der Tage bis zur Fertigstellung.

    `percentiles` ist termin-orientiert: Schlüssel = Konfidenz in Prozent, Wert =
    Anzahl Tage, innerhalb derer mit dieser Konfidenz fertiggestellt wird (höhere
    Konfidenz -> mehr Tage). `dates` bildet dieselben Perzentile auf Kalenderdaten
    ab, sofern ein start_date übergeben wurde. `not_completed` zählt Läufe, die
    `max_days` erreicht haben (Scope-Wachstum lief dem Durchsatz davon).
    """

    backlog: int
    runs: int
    split_rate: float
    completion_days: list[int]
    percentiles: dict[int, int | None]
    dates: dict[int, date]
    not_completed: int
    start_date: date | None


def how_many(
    sample: ThroughputSample,
    horizon_days: int,
    runs: int,
    *,
    rng: random.Random,
    percentiles: Sequence[int] = DEFAULT_PERCENTILES,
) -> HowManyForecast:
    """
    Kapazitäts-Forecast: Wie viele Items werden in `horizon_days` Tagen fertig?

    Pro Lauf werden `horizon_days` Tageswerte aus der empirischen Verteilung
    gezogen und summiert. Über `runs` Läufe entsteht die Ergebnisverteilung;
    daraus werden die Exceedance-Perzentile bestimmt.

    Args:
        sample:      Empirische Tagesdurchsatz-Verteilung.
        horizon_days: Länge des Vorhersagehorizonts in Tagen (> 0).
        runs:        Anzahl Monte-Carlo-Läufe (> 0).
        rng:         random.Random-Instanz (für Reproduzierbarkeit seeden).
        percentiles: Konfidenzstufen in Prozent.

    Returns:
        HowManyForecast. Bei leerer Verteilung oder horizon_days<=0 sind alle
        Totals 0.

    Raises:
        ValueError: Wenn runs <= 0.
    """
    if runs <= 0:
        raise ValueError("runs must be > 0")

    if sample.is_empty or horizon_days <= 0:
        totals = [0] * runs
    else:
        totals = [sum(sample._draw(rng, horizon_days)) for _ in range(runs)]

    totals_sorted = sorted(totals)
    # Exceedance: Konfidenz c -> Wert am (100 - c)-Perzentil der Totalverteilung.
    pct_map = {c: _nearest_rank(totals_sorted, 100 - c) for c in percentiles}

    return HowManyForecast(
        horizon_days=horizon_days,
        runs=runs,
        totals=totals_sorted,
        percentiles=pct_map,
    )


#: Harte Obergrenze für den automatischen Cap (~5,5 Jahre). Jenseits davon ist ein
#: Termin-Forecast ohnehin bedeutungslos; bei sehr kleinem Durchsatz verhindert
#: die Grenze zugleich eine Explosion der Ziehungen (runs × max_days).
_MAX_DAYS_CAP = 2000


def _default_max_days(backlog: int, mean_per_day: float) -> int:
    """Großzügige, nach oben begrenzte Simulationsdauer eines when_done-Laufs."""
    if mean_per_day <= 0:
        return _MAX_DAYS_CAP
    estimate = backlog / mean_per_day
    return min(int(estimate * 5) + 60, _MAX_DAYS_CAP)


def when_done(
    sample: ThroughputSample,
    backlog: int,
    runs: int,
    *,
    rng: random.Random,
    split_rate: float = 0.0,
    max_days: int | None = None,
    percentiles: Sequence[int] = DEFAULT_PERCENTILES,
    start_date: date | None = None,
) -> WhenDoneForecast:
    """
    Termin-Forecast: Wann ist ein Backlog von `backlog` Items fertig?

    Pro Lauf wird der verbleibende Scope Tag für Tag um den gezogenen
    Tagesdurchsatz reduziert. Optionales Scope-Wachstum: jedes abgeschlossene
    Item erzeugt im Mittel `split_rate` neue Items (z. B. 0.1 = +10 % Nacharbeit/
    Splits). Erreicht der verbleibende Scope <= 0, ist der Lauf an diesem Tag
    fertig. Läufe, die `max_days` erreichen (Wachstum >= Durchsatz), zählen als
    `not_completed` und gehen nicht in die Perzentile ein.

    Args:
        sample:      Empirische Tagesdurchsatz-Verteilung.
        backlog:     Anzahl zu erledigender Items (> 0).
        runs:        Anzahl Monte-Carlo-Läufe (> 0).
        rng:         random.Random-Instanz.
        split_rate:  Erwartete neue Items je abgeschlossenem Item (>= 0).
        max_days:    Obergrenze je Lauf; None = automatisch aus Backlog/Durchsatz.
        percentiles: Konfidenzstufen in Prozent.
        start_date:  Optionales Startdatum, um Perzentile auf Kalenderdaten
                     abzubilden.

    Returns:
        WhenDoneForecast.

    Raises:
        ValueError: Wenn runs <= 0, backlog <= 0 oder split_rate < 0.
    """
    if runs <= 0:
        raise ValueError("runs must be > 0")
    if backlog <= 0:
        raise ValueError("backlog must be > 0")
    if split_rate < 0:
        raise ValueError("split_rate must be >= 0")

    cap = max_days if max_days is not None else _default_max_days(backlog, sample.mean_per_day)

    completion_days: list[int] = []
    not_completed = 0

    if sample.is_empty:
        # Ohne Durchsatz wird nie fertiggestellt.
        not_completed = runs
    else:
        for _ in range(runs):
            day = _simulate_completion(sample, backlog, split_rate, cap, rng)
            if day is None:
                not_completed += 1
            else:
                completion_days.append(day)

    days_sorted = sorted(completion_days)
    # Perzentile über ALLE Läufe: nicht fertiggestellte Läufe zählen als "jenseits
    # des Caps" (unendlich, ans Ende sortiert). Eine Konfidenz oberhalb der
    # Fertigstellungsrate ist innerhalb des Caps nicht erreichbar -> None, statt
    # einen zu optimistischen Tag zu nennen (sonst wären alle Perzentile bei
    # Scope-Wachstum systematisch zu früh).
    total = len(days_sorted) + not_completed
    pct_map: dict[int, int | None] = {}
    for c in percentiles:
        rank = max(1, math.ceil(c / 100.0 * total)) if total else 1
        pct_map[c] = days_sorted[rank - 1] if total and rank <= len(days_sorted) else None

    dates_map: dict[int, date] = {}
    if start_date is not None:
        dates_map = {
            c: start_date + timedelta(days=d)
            for c, d in pct_map.items() if d is not None
        }

    return WhenDoneForecast(
        backlog=backlog,
        runs=runs,
        split_rate=split_rate,
        completion_days=days_sorted,
        percentiles=pct_map,
        dates=dates_map,
        not_completed=not_completed,
        start_date=start_date,
    )


def _simulate_completion(
    sample: ThroughputSample,
    backlog: int,
    split_rate: float,
    cap: int,
    rng: random.Random,
) -> int | None:
    """
    Ein einzelner when_done-Lauf.

    Returns:
        Anzahl Tage bis zur Fertigstellung, oder None, wenn `cap` erreicht wurde.
    """
    daily = sample._draw(rng, cap)
    remaining = float(backlog)
    for idx, done in enumerate(daily):
        remaining -= done
        remaining += done * split_rate
        if remaining <= 0:
            return idx + 1
    return None


def probability_at_least(fc: HowManyForecast, target: int) -> float:
    """
    Wahrscheinlichkeit, mindestens `target` Items zu erreichen.

    Dies ist der Punkt der Exceedance-Kurve an der Stelle `target` und damit die
    Antwort auf "Schaffen wir den Scope bis zum Horizont?". Nutzt die bereits
    gezogenen Läufe von how_many() — keine zweite Simulation.

    Args:
        fc:     Ergebnis von how_many() (fc.totals ist aufsteigend sortiert).
        target: Zielanzahl Items.

    Returns:
        Anteil der Läufe in [0.0, 1.0] mit Gesamtmenge >= target.
    """
    n = len(fc.totals)
    if n == 0:
        return 0.0
    idx = bisect.bisect_left(fc.totals, target)
    return (n - idx) / n


def probability_of_completing(
    sample: ThroughputSample,
    target: int,
    horizon_days: int,
    runs: int,
    *,
    rng: random.Random,
) -> float:
    """
    Wahrscheinlichkeit, in `horizon_days` mindestens `target` Items zu schaffen.

    Eigenständige Variante (simuliert selbst). Für den Report wird stattdessen
    probability_at_least() auf eine vorhandene how_many()-Auswertung angewandt.

    Args:
        sample:      Empirische Tagesdurchsatz-Verteilung.
        target:      Zielanzahl Items.
        horizon_days: Vorhersagehorizont in Tagen.
        runs:        Anzahl Läufe (> 0).
        rng:         random.Random-Instanz.

    Returns:
        Anteil der Läufe in [0.0, 1.0], die >= target erreichen.
    """
    fc = how_many(sample, horizon_days, runs, rng=rng, percentiles=())
    return probability_at_least(fc, target)
