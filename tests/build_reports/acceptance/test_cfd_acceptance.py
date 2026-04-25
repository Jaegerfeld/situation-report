# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       25.04.2026
# Geändert:       25.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Acceptance-Tests für CfdMetric gegen den realen ART_E-Datensatz.
#   Prüft insbesondere, dass die <First>- und <Closed>-Marker aus der
#   Workflow-Datei korrekt in die gestapelten Trendlinien-Positionen
#   übersetzt werden (Bug: Linien lagen bei Rohwerten statt Oberkanten).
# =============================================================================

from pathlib import Path

import pytest

from build_reports.loader import load_report_data
from build_reports.metrics.cfd import CfdMetric
from build_reports.terminology import SAFE

TESTDATA_DIR = Path(__file__).parent.parent.parent / "testdata" / "ART_E"
ISSUE_TIMES = TESTDATA_DIR / "ART_E_IssueTimes.xlsx"
CFD        = TESTDATA_DIR / "ART_E_CFD.xlsx"
WORKFLOW   = TESTDATA_DIR / "workflow_ART_E.txt"


@pytest.fixture(scope="module")
def art_e_data():
    """Load the real ART_E dataset with workflow markers once for all CFD tests."""
    return load_report_data(ISSUE_TIMES, CFD, WORKFLOW)


@pytest.fixture(scope="module")
def cfd_result(art_e_data):
    """Compute CfdMetric result for the ART_E dataset."""
    return CfdMetric().compute(art_e_data, SAFE)


class TestCfdWorkflowMarkers:
    """Verify that <First> and <Closed> workflow markers are resolved correctly."""

    def test_first_stage_resolved(self, art_e_data):
        """<First>In Analysis is read from the workflow file into data.first_stage."""
        assert art_e_data.first_stage == "In Analysis"

    def test_closed_stage_resolved(self, art_e_data):
        """<Closed>Completed is read from the workflow file into data.closed_stage."""
        assert art_e_data.closed_stage == "Completed"

    def test_chart_first_stage(self, cfd_result):
        """chart_data.first_stage reflects the workflow <First> marker."""
        assert cfd_result.chart_data.first_stage == "In Analysis"

    def test_chart_closed_stage(self, cfd_result):
        """chart_data.closed_stage reflects the workflow <Closed> marker."""
        assert cfd_result.chart_data.closed_stage == "Completed"


class TestCfdTrendLinePositions:
    """Verify that trend lines sit at the correct visual (stacked) boundary positions.

    In a stacked area chart the visual top-edge of stage S =
    stage_series[S] + all stages that appear after S in workflow order.
    The trend lines must track these stacked positions, not the raw series values.
    """

    def _stacked_last(self, cd, stage_name: str) -> int:
        """Return the stacked top-edge value on the last day for the given stage."""
        idx = cd.stages.index(stage_name)
        return sum(cd.stage_series[cd.stages[j]][-1] for j in range(idx, len(cd.stages)))

    def test_inflow_trend_at_in_analysis_top_edge(self, cfd_result):
        """Inflow trend line ends at the stacked top-edge of 'In Analysis', not its raw count.

        The raw count of In Analysis is much lower than the stacked position
        (raw: ~172, stacked: ~723 for this dataset).
        """
        cd = cfd_result.chart_data
        metric = CfdMetric()
        figs = metric.render(cfd_result, SAFE)
        trend = [t for t in figs[0].data if not t.stackgroup]

        expected_y_last = self._stacked_last(cd, "In Analysis")
        actual_y_last = list(trend[0].y)[-1]

        assert actual_y_last == expected_y_last, (
            f"Inflow line at {actual_y_last}, expected stacked top-edge {expected_y_last}. "
            f"Raw In Analysis value is {cd.stage_series['In Analysis'][-1]}."
        )

    def test_outflow_trend_at_completed_top_edge(self, cfd_result):
        """Outflow trend line ends at the stacked top-edge of 'Completed', not its raw count."""
        cd = cfd_result.chart_data
        metric = CfdMetric()
        figs = metric.render(cfd_result, SAFE)
        trend = [t for t in figs[0].data if not t.stackgroup]

        expected_y_last = self._stacked_last(cd, "Completed")
        actual_y_last = list(trend[1].y)[-1]

        assert actual_y_last == expected_y_last, (
            f"Outflow line at {actual_y_last}, expected stacked top-edge {expected_y_last}. "
            f"Raw Completed value is {cd.stage_series['Completed'][-1]}."
        )

    def test_inflow_above_outflow(self, cfd_result):
        """Inflow trend line ends above the outflow trend line (In Analysis stacks higher than Completed)."""
        cd = cfd_result.chart_data
        metric = CfdMetric()
        figs = metric.render(cfd_result, SAFE)
        trend = [t for t in figs[0].data if not t.stackgroup]

        inflow_last = list(trend[0].y)[-1]
        outflow_last = list(trend[1].y)[-1]
        assert inflow_last > outflow_last, (
            f"Inflow ({inflow_last}) should be above outflow ({outflow_last})."
        )

    def test_trend_lines_below_total_height(self, cfd_result):
        """Both trend lines end below the total stacked chart height."""
        cd = cfd_result.chart_data
        metric = CfdMetric()
        figs = metric.render(cfd_result, SAFE)
        trend = [t for t in figs[0].data if not t.stackgroup]

        total = sum(cd.stage_series[s][-1] for s in cd.stages)
        for t in trend:
            assert list(t.y)[-1] <= total


class TestCfdRenderOnRealData:
    """General render checks against the real ART_E dataset."""

    def test_returns_one_figure(self, cfd_result):
        """render() returns exactly one figure for the real ART_E dataset."""
        figs = CfdMetric().render(cfd_result, SAFE)
        assert len(figs) == 1

    def test_ratio_positive(self, cfd_result):
        """In/Out ratio is positive for the real dataset."""
        assert cfd_result.stats["ratio"] > 0

    def test_in_total_greater_than_out_total(self, cfd_result):
        """in_total (entries at <First> stage) is greater than out_total (<Closed> stage)."""
        assert cfd_result.stats["in_total"] > cfd_result.stats["out_total"]
