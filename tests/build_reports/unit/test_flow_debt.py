# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       10.09.2026
# Geändert:       10.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für FlowDebtMetric. Prüft die WIP-Zeitreihe aus den CFD-Daten,
#   die drei Urteile (Flow Debt aufnehmen / tilgen / stabil), das Toleranzband,
#   die Prüfung der Little's-Law-Annahmen 1 und 3, die Fenstergrenzen für die
#   gemessene Durchlaufzeit sowie das Verhalten bei fehlenden Daten.
# =============================================================================

from datetime import date, datetime, timedelta

import pytest

from build_reports.loader import CfdRecord, IssueRecord, ReportData
from build_reports.metrics.flow_debt import (
    DEBT_ACCUMULATING,
    DEBT_PAYING_OFF,
    DEBT_STABLE,
    FlowDebtMetric,
    _within,
    wip_series,
)
from build_reports.terminology import SAFE

STAGES = ["To Do", "In Progress", "Done"]


def _cfd(day: date, todo: int, inprog: int, done: int) -> CfdRecord:
    """Create a CfdRecord holding DAILY ENTRY COUNTS for the three stages.

    Args:
        day:    Calendar date of this CFD row.
        todo:   Issues that entered 'To Do' on that day.
        inprog: Issues that entered 'In Progress' on that day.
        done:   Issues that entered 'Done' on that day.

    Returns:
        CfdRecord with the three stage counts.
    """
    return CfdRecord(
        day=day,
        stage_counts={"To Do": todo, "In Progress": inprog, "Done": done},
    )


def _issue(key: str, first: datetime | None, closed: datetime | None) -> IssueRecord:
    """Create a minimal IssueRecord with the two dates the metric needs.

    Args:
        key:    Issue key.
        first:  Timestamp of entry into the first stage (may be None).
        closed: Timestamp of entry into the closed stage (may be None).

    Returns:
        IssueRecord with empty stage minutes and no resolution.
    """
    return IssueRecord(
        project="ART_A", key=key, issuetype="Story", status="Done",
        created=first, component="", first_date=first,
        implementation_date=None, closed_date=closed,
        stage_minutes={}, resolution="",
    )


def _data(cfd_rows: list[CfdRecord], issues: list[IssueRecord]) -> ReportData:
    """Assemble ReportData with the standard three-stage workflow.

    Args:
        cfd_rows: CFD records (daily entry counts).
        issues:   Issue records.

    Returns:
        ReportData with first_stage 'To Do' and closed_stage 'Done'.
    """
    return ReportData(
        issues=issues, cfd=cfd_rows, transitions=[], stages=list(STAGES),
        source_prefix="ART_A", first_stage="To Do", closed_stage="Done",
    )


@pytest.fixture
def metric() -> FlowDebtMetric:
    """Return a FlowDebtMetric with the default tolerance bands."""
    return FlowDebtMetric()


# -----------------------------------------------------------------------------
# wip_series
# -----------------------------------------------------------------------------

def test_wip_series_is_arrivals_minus_departures() -> None:
    """WIP per day equals cumulative arrivals minus cumulative departures."""
    data = _data(
        [
            _cfd(date(2026, 1, 1), 3, 0, 0),   # 3 arrived, 0 done  -> WIP 3
            _cfd(date(2026, 1, 2), 2, 1, 1),   # 5 arrived, 1 done  -> WIP 4
            _cfd(date(2026, 1, 3), 0, 1, 2),   # 5 arrived, 3 done  -> WIP 2
        ],
        [],
    )
    days, total, by_stage, between, first, closed = wip_series(data)

    assert days == [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)]
    assert total == [3, 4, 2]
    assert first == "To Do"
    assert closed == "Done"
    assert between == ["To Do", "In Progress"]
    assert set(by_stage) == {"To Do", "In Progress"}


def test_wip_series_never_goes_negative() -> None:
    """More departures than arrivals must not produce a negative WIP value."""
    data = _data([_cfd(date(2026, 1, 1), 1, 0, 4)], [])
    _, total, _, _, _, _ = wip_series(data)
    assert total == [0]


def test_wip_series_falls_back_to_outer_stages_without_markers() -> None:
    """Without <First>/<Closed> markers the outermost stages are used."""
    data = _data([_cfd(date(2026, 1, 1), 2, 0, 0)], [])
    data.first_stage = None
    data.closed_stage = None
    _, _, _, _, first, closed = wip_series(data)
    assert (first, closed) == ("To Do", "Done")


# -----------------------------------------------------------------------------
# _within
# -----------------------------------------------------------------------------

@pytest.mark.parametrize(
    "a, b, tol, expected",
    [
        (10.0, 10.0, 0.0, True),      # identical values are always within
        (0.0, 0.0, 0.0, True),        # both zero counts as equal
        (10.0, 11.0, 15.0, True),     # ~9 % of 11 -> inside a 15 % band
        (10.0, 13.0, 15.0, False),    # ~23 % of 13 -> outside
        (13.0, 10.0, 15.0, False),    # symmetric
    ],
)
def test_within_tolerance_band(a: float, b: float, tol: float, expected: bool) -> None:
    """The tolerance band is relative to the larger value and symmetric."""
    assert _within(a, b, tol) is expected


# -----------------------------------------------------------------------------
# compute — the three verdicts
# -----------------------------------------------------------------------------

def _steady_cfd(days: int = 20, standing_wip: int = 10) -> list[CfdRecord]:
    """Build a CFD with a standing WIP that neither grows nor shrinks.

    Day 1 brings the standing stock in; every later day has exactly one arrival
    and one departure, so WIP stays flat and both checked assumptions hold.

    Args:
        days:         Number of calendar days to generate.
        standing_wip: WIP level held constant across the window.

    Returns:
        List of CfdRecord with daily entry counts.
    """
    rows = [_cfd(date(2026, 1, 1), standing_wip, 0, 0)]
    rows += [_cfd(date(2026, 1, d), 1, 1, 1) for d in range(2, days + 1)]
    return rows


def _daily_closers(offset_days: int) -> list[IssueRecord]:
    """One issue closing on each day 2..20, each having taken offset_days.

    Args:
        offset_days: Elapsed days between first_date and closed_date.

    Returns:
        List of IssueRecord matching the _steady_cfd window.
    """
    return [
        _issue(
            f"A-{d}",
            datetime(2026, 1, d) - timedelta(days=offset_days),
            datetime(2026, 1, d),
        )
        for d in range(2, 21)
    ]


def test_steady_fixture_satisfies_both_assumptions(metric: FlowDebtMetric) -> None:
    """Guard the fixture itself: the steady scenario must not violate 1 or 3.

    Without this the verdict tests below could pass on data that the metric has
    already declared undependable.
    """
    stats = metric.compute(_data(_steady_cfd(), _daily_closers(1)), SAFE).stats

    assert stats["assumption_1_ok"] is True
    assert stats["assumption_3_ok"] is True
    assert stats["mean_wip"] == pytest.approx(10.0)


def test_accumulating_when_approximation_exceeds_measurement(
    metric: FlowDebtMetric,
) -> None:
    """A larger Little's-Law approximation than measurement means Flow Debt.

    A standing WIP of 10 at roughly one departure per day implies a mean cycle
    time of about ten days. The items that actually closed took one day each —
    they were finished by borrowing cycle time from the ten still sitting there.
    """
    stats = metric.compute(_data(_steady_cfd(), _daily_closers(1)), SAFE).stats

    assert stats["assumptions_ok"] is True
    assert stats["approx_mean"] > 9.0
    assert stats["exact_mean"] == pytest.approx(1.0)
    assert stats["verdict"] == DEBT_ACCUMULATING


def test_paying_off_when_measurement_exceeds_approximation(
    metric: FlowDebtMetric,
) -> None:
    """A larger measured mean than the approximation means debt is being repaid."""
    stats = metric.compute(_data(_steady_cfd(), _daily_closers(30)), SAFE).stats

    assert stats["assumptions_ok"] is True
    assert stats["exact_mean"] == pytest.approx(30.0)
    assert stats["exact_mean"] > stats["approx_mean"]
    assert stats["verdict"] == DEBT_PAYING_OFF


def test_stable_when_approximation_matches_measurement(
    metric: FlowDebtMetric,
) -> None:
    """When the two means agree the verdict is stable, not debt."""
    stats = metric.compute(_data(_steady_cfd(), _daily_closers(10)), SAFE).stats

    assert stats["assumptions_ok"] is True
    assert stats["exact_mean"] == pytest.approx(10.0)
    assert stats["verdict"] == DEBT_STABLE


def test_tolerance_band_decides_between_stable_and_debt(
    metric: FlowDebtMetric,
) -> None:
    """The same data yields stable or debt depending only on the band width."""
    data = _data(_steady_cfd(), _daily_closers(10))

    metric.tolerance_pct = 15.0
    assert metric.compute(data, SAFE).stats["verdict"] == DEBT_STABLE

    metric.tolerance_pct = 0.0
    assert metric.compute(data, SAFE).stats["verdict"] == DEBT_ACCUMULATING


# -----------------------------------------------------------------------------
# compute — window, assumptions, guards
# -----------------------------------------------------------------------------

def test_exact_mean_ignores_issues_closed_outside_the_window(
    metric: FlowDebtMetric,
) -> None:
    """Only issues closed inside the CFD window may enter the measured mean."""
    cfd_rows = [_cfd(date(2026, 1, d), 1, 1, 1) for d in range(1, 6)]
    inside = [
        _issue("IN-1", datetime(2026, 1, 1), datetime(2026, 1, 3)),
        _issue("IN-2", datetime(2026, 1, 2), datetime(2026, 1, 4)),
    ]
    outside = [_issue("OUT-1", datetime(2025, 1, 1), datetime(2025, 6, 1))]
    result = metric.compute(_data(cfd_rows, inside + outside), SAFE)

    assert result.stats["closed_in_window"] == 2
    assert result.stats["exact_mean"] == pytest.approx(2.0)


def test_assumption_one_compares_rates_not_cumulative_totals(
    metric: FlowDebtMetric,
) -> None:
    """A standing WIP must not by itself violate assumption 1.

    Cumulative arrivals always exceed cumulative departures by exactly the
    standing stock. Comparing those totals would flag every process that
    carries any WIP at all, so the check compares what moved DURING the window.
    """
    stats = metric.compute(
        _data(_steady_cfd(standing_wip=50), _daily_closers(1)), SAFE
    ).stats

    assert stats["arrivals"] > stats["departures"]
    assert stats["arrivals_in_window"] == stats["departures_in_window"]
    assert stats["assumption_1_ok"] is True


def test_assumption_one_violation_is_reported(metric: FlowDebtMetric) -> None:
    """Arrivals far above departures during the window violate assumption 1."""
    cfd_rows = [_cfd(date(2026, 1, d), 10, 0, 1) for d in range(1, 6)]
    issues = [
        _issue(f"A-{d}", datetime(2026, 1, d), datetime(2026, 1, d + 1))
        for d in range(1, 5)
    ]
    result = metric.compute(_data(cfd_rows, issues), SAFE)

    assert result.stats["assumption_1_ok"] is False
    assert result.stats["assumptions_ok"] is False
    assert any("assumption 1" in w for w in result.warnings)


def test_assumption_three_violation_is_reported(metric: FlowDebtMetric) -> None:
    """A WIP level that grows across the window violates assumption 3."""
    # WIP climbs from 1 to 9: far more arrives than departs, so the level at the
    # end no longer resembles the level at the start.
    cfd_rows = [
        _cfd(date(2026, 1, 1), 2, 0, 1),
        _cfd(date(2026, 1, 2), 5, 0, 1),
        _cfd(date(2026, 1, 3), 5, 0, 1),
    ]
    issues = [
        _issue(f"A-{d}", datetime(2026, 1, d), datetime(2026, 1, d))
        for d in range(1, 4)
    ]
    result = metric.compute(_data(cfd_rows, issues), SAFE)

    assert result.stats["assumption_3_ok"] is False
    assert any("assumption 3" in w for w in result.warnings)


def test_more_departures_than_arrivals_warns_about_understated_wip(
    metric: FlowDebtMetric,
) -> None:
    """Issues that skipped the first stage bias WIP downward — say so."""
    cfd_rows = [
        _cfd(date(2026, 1, 1), 1, 0, 3),
        _cfd(date(2026, 1, 2), 1, 0, 3),
    ]
    issues = [
        _issue("A-1", datetime(2026, 1, 1), datetime(2026, 1, 2)),
        _issue("A-2", datetime(2026, 1, 1), datetime(2026, 1, 2)),
    ]
    result = metric.compute(_data(cfd_rows, issues), SAFE)
    assert any("never entered" in w for w in result.warnings)


def test_no_cfd_data_degrades_with_a_warning(metric: FlowDebtMetric) -> None:
    """Without CFD.xlsx the metric warns instead of raising."""
    result = metric.compute(_data([], []), SAFE)
    assert result.chart_data is None
    assert any("CFD" in w for w in result.warnings)


def test_no_departures_in_window_degrades_with_a_warning(
    metric: FlowDebtMetric,
) -> None:
    """Throughput of zero cannot produce an approximation — warn, do not divide."""
    cfd_rows = [_cfd(date(2026, 1, d), 1, 0, 0) for d in range(1, 4)]
    result = metric.compute(_data(cfd_rows, []), SAFE)
    assert result.chart_data is None
    assert any("Nothing departed" in w for w in result.warnings)


def test_departures_without_closed_issues_degrades_with_a_warning(
    metric: FlowDebtMetric,
) -> None:
    """The CFD may show departures while no issue record carries a Closed Date."""
    cfd_rows = [_cfd(date(2026, 1, d), 2, 0, 1) for d in range(1, 4)]
    issues = [_issue("A-1", datetime(2026, 1, 1), None)]
    result = metric.compute(_data(cfd_rows, issues), SAFE)

    assert result.chart_data is None
    assert any("closed inside" in w for w in result.warnings)


def test_diverging_departure_counts_are_reported(metric: FlowDebtMetric) -> None:
    """CFD departures and issue Closed Dates must describe the same population.

    When the <Closed> boundary and the issues' Closed Date disagree, throughput
    and the measured mean are taken from different sets of items — say so
    instead of comparing them silently.
    """
    # 3 departures via the closed stage, but 12 issues carry a Closed Date.
    cfd_rows = [_cfd(date(2026, 1, d), 5, 0, 1) for d in range(1, 4)]
    issues = [
        _issue(f"A-{i}", datetime(2026, 1, 1), datetime(2026, 1, 2))
        for i in range(12)
    ]
    result = metric.compute(_data(cfd_rows, issues), SAFE)

    assert any("Departure counts disagree" in w for w in result.warnings)


# -----------------------------------------------------------------------------
# render
# -----------------------------------------------------------------------------

def test_render_returns_one_figure_with_the_verdict_in_the_title(
    metric: FlowDebtMetric,
) -> None:
    """The figure header states the assumption status before the verdict."""
    cfd_rows = [_cfd(date(2026, 1, d), 1, 1, 1) for d in range(1, 11)]
    issues = [
        _issue(f"A-{d}", datetime(2026, 1, d), datetime(2026, 1, d))
        for d in range(1, 11)
    ]
    result = metric.compute(_data(cfd_rows, issues), SAFE)
    figures = metric.render(result, SAFE)

    assert len(figures) == 1
    title = figures[0].layout.title.text
    assert "Flow Debt" in title
    assert "assumptions 1 + 3" in title
    assert title.index("assumptions 1 + 3") < title.index("Exact mean CT")


def test_render_without_chart_data_returns_no_figures(metric: FlowDebtMetric) -> None:
    """A degraded result renders nothing rather than failing."""
    result = metric.compute(_data([], []), SAFE)
    assert metric.render(result, SAFE) == []
