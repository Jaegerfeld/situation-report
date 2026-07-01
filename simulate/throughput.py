# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       01.07.2026
# Geändert:       01.07.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Adapter von geladenen Jira-Daten (build_reports.loader.ReportData) auf die
#   Tagesdurchsatz-Reihe, die die Monte-Carlo-Engine erwartet. Zählt
#   abgeschlossene Issues je Tag und füllt das History-Fenster lückenlos auf —
#   inklusive Null-Tage. Das Auffüllen ist bewusst und korrigiert eine Verzerrung
#   der Flow-Velocity-Metrik, die nur Tage MIT Abschlüssen kennt: ohne Null-Tage
#   würde der Durchsatz und damit der Forecast systematisch überschätzt.
#   Das History-Fenster ist [start, end) — das (meist unvollständige) Enddatum
#   wird ausgeschlossen.
# =============================================================================

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta

from build_reports.loader import ReportData

from .forecast import ThroughputSample


def closed_dates(data: ReportData) -> list[date]:
    """
    Sortierte Liste der Abschlussdaten aller Issues mit Closed Date.

    Args:
        data: Geladene ReportData.

    Returns:
        Aufsteigend sortierte Liste von Kalenderdaten (Uhrzeit verworfen).
    """
    return sorted(
        i.closed_date.date() for i in data.issues if i.closed_date is not None
    )


def daily_throughput(data: ReportData, start: date, end: date) -> list[int]:
    """
    Tagesdurchsatz über das Fenster [start, end), inklusive Null-Tage.

    Args:
        data:  Geladene ReportData.
        start: Erster Tag des Fensters (inklusive).
        end:   Enddatum (exklusive) — der typischerweise unvollständige aktuelle
               Tag wird so ausgeschlossen.

    Returns:
        Eine Liste mit genau (end - start).days Werten: abgeschlossene Items je
        Tag. Leer, wenn end <= start.
    """
    n_days = (end - start).days
    if n_days <= 0:
        return []

    per_day: Counter[date] = Counter(
        d for d in closed_dates(data) if start <= d < end
    )
    return [per_day.get(start + timedelta(days=i), 0) for i in range(n_days)]


def default_history_window(
    data: ReportData,
    days: int = 180,
    *,
    reference: date | None = None,
) -> tuple[date, date]:
    """
    Standard-History-Fenster [end - days, end).

    Das Enddatum ist exklusiv. Standardmäßig endet das Fenster am Referenztag
    (None = heute), damit ein jüngst zurückliegender Leerlauf (Null-Tage) den
    Forecast korrekt dämpft. Für eine datenbezogene Auswertung kann `reference`
    auf den letzten Liefertag + 1 gesetzt werden.

    Args:
        data:      Geladene ReportData (für den Fallback bei fehlendem reference).
        days:      Länge des Fensters in Tagen (> 0).
        reference: Exklusives Enddatum; None = heute.

    Returns:
        Tupel (start, end) mit end exklusiv.
    """
    end = reference if reference is not None else date.today()
    start = end - timedelta(days=days)
    return start, end


def to_sample(data: ReportData, start: date, end: date) -> ThroughputSample:
    """
    Baue direkt eine ThroughputSample aus ReportData und Fenster.

    Args:
        data:  Geladene ReportData.
        start: Fensterbeginn (inklusive).
        end:   Fensterende (exklusive).

    Returns:
        Empirische Tagesdurchsatz-Verteilung für die Engine.
    """
    return ThroughputSample.from_daily_counts(daily_throughput(data, start, end))
