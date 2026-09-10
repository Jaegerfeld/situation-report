# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       10.09.2026
# Geändert:       10.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Implementiert die Flow-Debt-Anzeige nach Vacanti, "Actionable Agile Metrics
#   for Predictability" (2015), Kapitel 9. Aus den CFD-Tagesdaten wird der
#   Bestand (WIP) je Stage als Zeitreihe gebildet; aus mittlerem Bestand und
#   Durchsatz folgt die genäherte mittlere Durchlaufzeit (Little's Law). Der
#   Vergleich mit der tatsächlich gemessenen mittleren Durchlaufzeit zeigt an,
#   ob der Prozess Flow Debt aufnimmt (einzelne Vorgänge werden auf Kosten
#   anderer beschleunigt), Flow Debt tilgt oder stabil ist.
#
#   Vorgeschaltet ist die Prüfung zweier Annahmen hinter Little's Law
#   (Vacanti S. 43): Zugang und Abgang im Gleichgewicht (Annahme 1) und
#   Bestand am Anfang und Ende vergleichbar (Annahme 3). Sind sie verletzt,
#   ist die Flow-Debt-Aussage nicht belastbar und wird als solche gekennzeichnet.
#
#   Herleitung: Quellen/Buchanalysen/Actionable-Agile-Metrics-I_Vacanti_Analyse.md
#   (Kandidaten AA2, AA3, AA5); deckt zugleich H2 aus der Hohpe-Analyse ab
#   (rechnerische vs. gemessene Durchlaufzeit als Konfidenzsignal).
# =============================================================================

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import date

import plotly.graph_objects as go

from ..loader import ReportData
from ..terminology import FLOW_DEBT, term
from . import register
from .base import MetricPlugin, MetricResult
from .cfd import cumulative_stage_series, resolve_flow_boundaries

# Verdicts for the Flow Debt comparison
DEBT_ACCUMULATING = "accumulating"
DEBT_PAYING_OFF = "paying_off"
DEBT_STABLE = "stable"

# Verdicts for the Little's Law assumption check
ASSUMPTION_OK = "ok"
ASSUMPTION_VIOLATED = "violated"

# Default tolerance band for "roughly equal", in percent of the exact mean.
# Vacanti gives no number for his third state (S. 117 f.); without a band the
# comparison is exact and would report debt for practically every real data
# set. 15 % is deliberately generous: it keeps the verdict quiet for ordinary
# variation and speaks up only for differences that are visible in a chart.
DEFAULT_TOLERANCE_PCT = 15.0

# Default tolerance for Little's Law assumptions 1 and 3, also in percent.
# Assumption 1 compares arrivals against departures over the window, assumption 3
# compares WIP at the start against WIP at the end.
DEFAULT_ASSUMPTION_TOLERANCE_PCT = 25.0

_COLOR_ACCUMULATING = "#c0392b"
_COLOR_PAYING_OFF = "#27ae60"
_COLOR_STABLE = "#2c7fb8"


@dataclass
class _FlowDebtData:
    """
    Chart data for the Flow Debt metric.

    Attributes:
        days:            Ordered calendar days covered by the CFD records.
        wip_total:       Total work in progress per day (arrivals minus departures).
        wip_by_stage:    Per-stage work in progress per day, in workflow order.
        stages_between:  Stage names between the first and the closed boundary.
        first_stage:     Effective arrival boundary.
        closed_stage:    Effective departure boundary.
        approx_mean:     Approximate mean cycle time in days (mean WIP / throughput).
        exact_mean:      Exact mean cycle time in days from the closed issues.
        verdict:         One of DEBT_ACCUMULATING, DEBT_PAYING_OFF, DEBT_STABLE.
        assumptions_ok:  True when both checked Little's Law assumptions hold.
    """
    days: list[date] = field(default_factory=list)
    wip_total: list[int] = field(default_factory=list)
    wip_by_stage: dict[str, list[int]] = field(default_factory=dict)
    stages_between: list[str] = field(default_factory=list)
    first_stage: str = ""
    closed_stage: str = ""
    approx_mean: float = 0.0
    exact_mean: float = 0.0
    verdict: str = DEBT_STABLE
    assumptions_ok: bool = True


def wip_series(
    data: ReportData,
) -> tuple[list[date], list[int], dict[str, list[int]], list[str], str, str]:
    """
    Derive the work-in-progress time series from the cumulative CFD data.

    WIP on a given day is the number of items that have arrived (entered the
    first stage) minus the number that have departed (entered the closed
    stage) up to that day — Vacanti's definition of items "between the two
    boundaries" (S. 22, S. 89 f.).

    The per-stage breakdown returns the cumulative arrivals of each stage
    between the boundaries minus the arrivals of the stage after it, i.e. how
    many items are currently sitting in that stage. It is not needed for the
    Flow Debt comparison itself but is the substrate for a later queue view.

    Args:
        data: ReportData with cfd records and stages populated.

    Returns:
        Tuple of (days, total WIP per day, per-stage WIP per day,
        stage names between the boundaries, first stage, closed stage).
    """
    days, cumulative = cumulative_stage_series(data)
    first, closed = resolve_flow_boundaries(data, cumulative)

    arrivals = cumulative[first]
    departures = cumulative[closed]
    total = [max(0, a - d) for a, d in zip(arrivals, departures)]

    # Stages from the arrival boundary up to (and including) the closed stage,
    # in workflow order; each stage holds what arrived in it minus what moved on.
    i_first = data.stages.index(first)
    i_closed = data.stages.index(closed)
    ordered = data.stages[i_first:i_closed + 1] if i_first <= i_closed else [first, closed]

    by_stage: dict[str, list[int]] = {}
    for idx, stage in enumerate(ordered[:-1]):
        nxt = ordered[idx + 1]
        by_stage[stage] = [
            max(0, a - b) for a, b in zip(cumulative[stage], cumulative[nxt])
        ]
    return days, total, by_stage, ordered[:-1], first, closed


def _within(a: float, b: float, tolerance_pct: float) -> bool:
    """
    Report whether two values lie within a relative tolerance of each other.

    The band is measured against the larger absolute value so the check is
    symmetric; when both values are zero they count as equal.

    Args:
        a:             First value.
        b:             Second value.
        tolerance_pct: Half-width of the band in percent.

    Returns:
        True when the two values are close enough to be treated as equal.
    """
    scale = max(abs(a), abs(b))
    if scale == 0:
        return True
    return abs(a - b) / scale * 100.0 <= tolerance_pct


class FlowDebtMetric(MetricPlugin):
    """
    Flow Debt metric after Vacanti (2015), chapter 9.

    Compares the approximate mean cycle time predicted by Little's Law
    (mean WIP divided by throughput, both read at the CFD boundaries) against
    the exact mean cycle time measured on the issues that actually closed. A larger approximate mean means the process
    is accumulating Flow Debt: some items were completed faster by borrowing
    cycle time from others still in progress.

    The verdict is only meaningful when Little's Law's assumptions hold, so
    assumptions 1 (arrivals match departures) and 3 (WIP comparable at the
    start and the end of the window) are checked first and reported above it.

    Class attributes:
        metric_id:                Registry key, 'flow_debt'.
        tolerance_pct:            Band around the exact mean that still counts
                                  as "stable", in percent.
        assumption_tolerance_pct: Band for the two assumption checks, in percent.
    """

    metric_id = FLOW_DEBT
    tolerance_pct: float = DEFAULT_TOLERANCE_PCT
    assumption_tolerance_pct: float = DEFAULT_ASSUMPTION_TOLERANCE_PCT

    def compute(self, data: ReportData, terminology: str) -> MetricResult:
        """
        Compute the Flow Debt verdict and the assumption check.

        Both legs of the comparison are derived from the same window: the days
        covered by the CFD records. The exact mean uses only issues that closed
        inside that window, so the two populations match as closely as the data
        allows.

        Args:
            data:        Filtered ReportData (cfd records must be populated).
            terminology: Active terminology mode (not used for labels here).

        Returns:
            MetricResult with stats and chart_data as _FlowDebtData.
        """
        warnings: list[str] = []

        if not data.cfd:
            warnings.append(
                "No CFD data available — Flow Debt needs CFD.xlsx (--cfd)."
            )
            return MetricResult(metric_id=self.metric_id, warnings=warnings)
        if not data.stages:
            warnings.append("No stages defined in data.")
            return MetricResult(metric_id=self.metric_id, warnings=warnings)

        days, wip_total, wip_by_stage, stages_between, first, closed = wip_series(data)
        if not days:
            warnings.append("CFD data contains no days.")
            return MetricResult(metric_id=self.metric_id, warnings=warnings)

        window_start, window_end = days[0], days[-1]
        window_days = (window_end - window_start).days + 1

        # Arrivals and departures DURING the window, both read at the same two
        # boundaries the WIP series uses. Little's Law only holds when WIP,
        # throughput and cycle time describe one and the same system, so the
        # throughput leg must come from the departure boundary — not from a
        # separate count of closed issues (Vacanti, assumption 5).
        _, cumulative = cumulative_stage_series(data)
        arrivals_total = cumulative[first][-1]
        departures_total = cumulative[closed][-1]
        arrivals_in_window = arrivals_total - cumulative[first][0]
        departures_in_window = departures_total - cumulative[closed][0]

        if departures_in_window <= 0:
            warnings.append(
                f"Nothing departed via '{closed}' during the window — "
                f"Flow Debt cannot be computed."
            )
            return MetricResult(metric_id=self.metric_id, warnings=warnings)

        # The measured mean can only come from the issue records; restrict it to
        # the same window so both legs describe the same period.
        cycle_days: list[float] = []
        for issue in data.issues:
            closed_at, started_at = issue.closed_date, issue.first_date
            if closed_at is None or started_at is None:
                continue
            if not (window_start <= closed_at.date() <= window_end):
                continue
            cycle_days.append((closed_at - started_at).total_seconds() / 86400.0)

        closed_in_window = len(cycle_days)
        if closed_in_window == 0:
            warnings.append(
                "No issues closed inside the CFD window — Flow Debt cannot be computed."
            )
            return MetricResult(metric_id=self.metric_id, warnings=warnings)

        # The two sources should agree about how many items finished. When they
        # do not, the CFD boundary and the issues' Closed Date mean different
        # things, and the comparison mixes two populations.
        if not _within(
            departures_in_window, closed_in_window, self.assumption_tolerance_pct
        ):
            warnings.append(
                f"Departure counts disagree: {departures_in_window} entered "
                f"'{closed}' but {closed_in_window} issues carry a Closed Date in "
                f"the window. Throughput and mean cycle time describe different "
                f"populations."
            )

        throughput_per_day = departures_in_window / window_days
        exact_mean = statistics.mean(cycle_days)
        mean_wip = statistics.mean(wip_total)
        approx_mean = mean_wip / throughput_per_day if throughput_per_day else 0.0

        # --- Little's Law assumptions 1 and 3 (Vacanti S. 43) ----------------
        # Assumption 1 is about RATES, so it compares what arrived and what
        # departed DURING the window. Comparing the cumulative totals instead
        # would fail for every process that carries a standing WIP, because
        # those totals differ by exactly that standing stock.
        #
        # The two checks are two readings of the same imbalance (arrivals minus
        # departures during the window equals the change in WIP), but they are
        # scaled differently: assumption 1 against the flow, assumption 3
        # against the WIP level. Both are reported because a given imbalance
        # can be harmless for one and severe for the other.
        assumption_1 = _within(
            arrivals_in_window, departures_in_window, self.assumption_tolerance_pct
        )
        assumption_3 = _within(wip_total[0], wip_total[-1], self.assumption_tolerance_pct)
        assumptions_ok = assumption_1 and assumption_3

        if not assumption_1:
            warnings.append(
                f"Little's Law assumption 1 violated: {arrivals_in_window} arrivals vs. "
                f"{departures_in_window} departures during the window — the Flow Debt "
                f"verdict is not dependable."
            )
        if not assumption_3:
            warnings.append(
                f"Little's Law assumption 3 violated: WIP {wip_total[0]} at the start "
                f"vs. {wip_total[-1]} at the end — the Flow Debt verdict is not dependable."
            )

        # The CFD counts stage ENTRIES, so items that skipped the first stage
        # never register as arrivals and bias WIP downward. Surface that rather
        # than letting it distort the comparison silently.
        if arrivals_total and departures_total and arrivals_total < departures_total:
            warnings.append(
                f"More departures ({departures_total}) than arrivals ({arrivals_total}) "
                f"in the CFD: some issues never entered '{first}'. WIP is understated."
            )

        # --- The verdict -----------------------------------------------------
        if _within(approx_mean, exact_mean, self.tolerance_pct):
            verdict = DEBT_STABLE
        elif approx_mean > exact_mean:
            verdict = DEBT_ACCUMULATING
        else:
            verdict = DEBT_PAYING_OFF

        chart_data = _FlowDebtData(
            days=days,
            wip_total=wip_total,
            wip_by_stage=wip_by_stage,
            stages_between=stages_between,
            first_stage=first,
            closed_stage=closed,
            approx_mean=round(approx_mean, 2),
            exact_mean=round(exact_mean, 2),
            verdict=verdict,
            assumptions_ok=assumptions_ok,
        )
        stats = dict(
            approx_mean=round(approx_mean, 2),
            exact_mean=round(exact_mean, 2),
            mean_wip=round(mean_wip, 2),
            throughput_per_day=round(throughput_per_day, 3),
            verdict=verdict,
            assumptions_ok=assumptions_ok,
            assumption_1_ok=assumption_1,
            assumption_3_ok=assumption_3,
            arrivals=arrivals_total,
            departures=departures_total,
            arrivals_in_window=arrivals_in_window,
            departures_in_window=departures_in_window,
            window_days=window_days,
            closed_in_window=closed_in_window,
            tolerance_pct=self.tolerance_pct,
        )
        return MetricResult(
            metric_id=self.metric_id, stats=stats,
            chart_data=chart_data, warnings=warnings,
        )

    def render(self, result: MetricResult, terminology: str) -> list[go.Figure]:
        """
        Build the WIP-over-time figure carrying the assumption and debt verdict.

        The header follows the house convention (see flow_load and cfd): scalar
        facts belong in the title line. The assumption status is stated FIRST,
        because the assumptions decide whether the debt number means anything.

        Args:
            result:      MetricResult produced by compute().
            terminology: Active terminology mode.

        Returns:
            List with a single plotly Figure, or an empty list when compute()
            produced no chart data.
        """
        cd: _FlowDebtData | None = result.chart_data
        if cd is None:
            return []

        label = term(self.metric_id, terminology)
        color = {
            DEBT_ACCUMULATING: _COLOR_ACCUMULATING,
            DEBT_PAYING_OFF: _COLOR_PAYING_OFF,
            DEBT_STABLE: _COLOR_STABLE,
        }[cd.verdict]
        verdict_text = {
            DEBT_ACCUMULATING: "accumulating Flow Debt",
            DEBT_PAYING_OFF: "paying off Flow Debt",
            DEBT_STABLE: "stable",
        }[cd.verdict]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=[d.isoformat() for d in cd.days],
            y=cd.wip_total,
            mode="lines",
            name=f"WIP ({cd.first_stage} → {cd.closed_stage})",
            line=dict(color=color, width=2),
            fill="tozeroy",
            fillcolor="rgba(44,127,184,0.12)",
        ))

        assumption_line = (
            "Little's Law assumptions 1 + 3: OK"
            if cd.assumptions_ok
            else "Little's Law assumptions 1 + 3: VIOLATED — verdict not dependable"
        )
        header = (
            f"{assumption_line}<br>"
            f"Approx. mean CT: {cd.approx_mean}d | "
            f"Exact mean CT: {cd.exact_mean}d | "
            f"<b>{verdict_text}</b>"
        )
        fig.update_layout(
            title=f"{label}<br><span style='font-size:11px'>{header}</span>",
            xaxis_title="Date",
            yaxis_title="Work in Progress",
            template="plotly_white",
            showlegend=True,
        )
        return [fig]


register(FlowDebtMetric())
