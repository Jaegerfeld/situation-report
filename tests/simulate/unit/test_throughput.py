# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       01.07.2026
# Geändert:       01.07.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für simulate.throughput: Tagesdurchsatz inkl. Null-Tagen,
#   exklusives Enddatum, Ignorieren von Issues ohne Closed Date sowie das
#   Standard-History-Fenster.
# =============================================================================

from __future__ import annotations

from datetime import date, datetime

from build_reports.loader import IssueRecord, ReportData
from simulate.throughput import (
    daily_throughput,
    default_history_window,
    to_sample,
)


def _issue(closed: datetime | None) -> IssueRecord:
    return IssueRecord(
        project="P", key="K", issuetype="Feature", status="Done",
        created=None, component="", first_date=None, implementation_date=None,
        closed_date=closed, stage_minutes={}, resolution="",
    )


def _data(*closed: datetime | None) -> ReportData:
    return ReportData(issues=[_issue(c) for c in closed])


class TestDailyThroughput:
    def test_fills_zero_days_within_window(self) -> None:
        data = _data(
            datetime(2026, 1, 1, 9, 0),
            datetime(2026, 1, 2, 14, 30),
            datetime(2026, 1, 2, 16, 0),
            datetime(2026, 1, 5, 8, 0),
        )
        series = daily_throughput(data, date(2026, 1, 1), date(2026, 1, 8))
        assert series == [1, 2, 0, 0, 1, 0, 0]

    def test_end_date_is_exclusive(self) -> None:
        data = _data(datetime(2026, 1, 7, 12, 0), datetime(2026, 1, 8, 12, 0))
        series = daily_throughput(data, date(2026, 1, 1), date(2026, 1, 8))
        assert len(series) == 7
        assert series[-1] == 1          # 7. Jan zählt
        assert sum(series) == 1         # 8. Jan (== end) ist ausgeschlossen

    def test_ignores_issues_without_closed_date(self) -> None:
        data = _data(None, datetime(2026, 1, 3, 10, 0), None)
        series = daily_throughput(data, date(2026, 1, 1), date(2026, 1, 5))
        assert series == [0, 0, 1, 0]

    def test_dates_outside_window_ignored(self) -> None:
        data = _data(datetime(2025, 12, 31, 10, 0), datetime(2026, 2, 1, 10, 0))
        series = daily_throughput(data, date(2026, 1, 1), date(2026, 1, 4))
        assert series == [0, 0, 0]

    def test_empty_window(self) -> None:
        data = _data(datetime(2026, 1, 1, 10, 0))
        assert daily_throughput(data, date(2026, 1, 8), date(2026, 1, 1)) == []


class TestHistoryWindow:
    def test_reference_defines_exclusive_end(self) -> None:
        start, end = default_history_window(_data(), days=30, reference=date(2026, 7, 1))
        assert end == date(2026, 7, 1)
        assert start == date(2026, 6, 1)
        assert (end - start).days == 30


class TestToSample:
    def test_builds_sample_from_window(self) -> None:
        data = _data(
            datetime(2026, 1, 1, 9, 0),
            datetime(2026, 1, 1, 10, 0),
            datetime(2026, 1, 3, 9, 0),
        )
        sample = to_sample(data, date(2026, 1, 1), date(2026, 1, 4))
        # Tage: [2, 0, 1] -> Verteilung {0:1, 1:1, 2:1}, 3 Tage beobachtet
        assert sample.days_observed == 3
        assert sample.values == (0, 1, 2)
        assert sample.weights == (1, 1, 1)
