# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       26.04.2026
# Geändert:       26.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für build_reports.metrics.process_flow. Prüft Kantenzählung,
#   Knotenreihenfolge (Workflow-Stages zuerst), Self-Loop-Erkennung,
#   Rückwärts-Transitionen, fehlende Daten-Warnungen sowie das Rendering
#   (Traces, Annotations).
# =============================================================================

"""Unit tests for build_reports.metrics.process_flow."""

import pytest

from build_reports.loader import ReportData, TransitionEntry
from build_reports.metrics.process_flow import (
    ProcessFlowMetric,
    _circular_positions,
    _edge_width,
    _Edge,
)
from build_reports.terminology import PROCESS_FLOW, SAFE


def _entry(key: str, label: str) -> TransitionEntry:
    return TransitionEntry(key=key, label=label, timestamp="01.01.2025 09:00:00")


def _make_data(transitions: list[TransitionEntry], stages: list[str] | None = None) -> ReportData:
    return ReportData(transitions=transitions, stages=stages or [])


@pytest.fixture
def metric() -> ProcessFlowMetric:
    return ProcessFlowMetric()


# ---------------------------------------------------------------------------
# compute — edge counting
# ---------------------------------------------------------------------------

class TestComputeEdgeCounting:

    def test_single_issue_two_transitions_produces_one_edge(self, metric):
        data = _make_data([_entry("A-1", "Funnel"), _entry("A-1", "Analysis")])
        result = metric.compute(data, SAFE)
        assert result.stats["edge_pairs"] == 1
        assert result.stats["total_transitions"] == 1

    def test_edge_count_aggregated_across_issues(self, metric):
        """Same transition in two issues → count = 2."""
        t = [
            _entry("A-1", "Funnel"), _entry("A-1", "Analysis"),
            _entry("A-2", "Funnel"), _entry("A-2", "Analysis"),
        ]
        result = metric.compute(_make_data(t), SAFE)
        fd = result.chart_data
        edge = next(e for e in fd.edges if e.source == "Funnel" and e.target == "Analysis")
        assert edge.count == 2

    def test_relative_sums_to_one(self, metric):
        t = [
            _entry("A-1", "Funnel"), _entry("A-1", "Analysis"),
            _entry("A-1", "Analysis"), _entry("A-1", "Done"),
        ]
        result = metric.compute(_make_data(t), SAFE)
        total_relative = sum(e.relative for e in result.chart_data.edges)
        assert abs(total_relative - 1.0) < 1e-9

    def test_self_loop_detected(self, metric):
        t = [_entry("A-1", "Funnel"), _entry("A-1", "Funnel")]
        result = metric.compute(_make_data(t), SAFE)
        assert any(e.is_self_loop for e in result.chart_data.edges)

    def test_single_entry_per_issue_produces_no_edges(self, metric):
        t = [_entry("A-1", "Funnel")]
        result = metric.compute(_make_data(t), SAFE)
        assert result.chart_data is None or result.chart_data.edges == [] or result.warnings

    def test_issue_count_correct(self, metric):
        t = [
            _entry("A-1", "Funnel"), _entry("A-1", "Analysis"),
            _entry("A-2", "Funnel"), _entry("A-2", "Done"),
        ]
        result = metric.compute(_make_data(t), SAFE)
        assert result.stats["issue_count"] == 2


# ---------------------------------------------------------------------------
# compute — node ordering
# ---------------------------------------------------------------------------

class TestComputeNodeOrdering:

    def test_workflow_stages_come_first(self, metric):
        t = [
            _entry("A-1", "Created"), _entry("A-1", "Funnel"),
            _entry("A-1", "Funnel"), _entry("A-1", "Analysis"),
        ]
        data = _make_data(t, stages=["Funnel", "Analysis"])
        result = metric.compute(data, SAFE)
        nodes = result.chart_data.nodes
        funnel_idx = nodes.index("Funnel")
        analysis_idx = nodes.index("Analysis")
        created_idx = nodes.index("Created")
        assert funnel_idx < created_idx
        assert analysis_idx < created_idx

    def test_extra_statuses_appended_alphabetically(self, metric):
        t = [
            _entry("A-1", "Zebra"), _entry("A-1", "Apple"),
            _entry("A-1", "Apple"), _entry("A-1", "Mango"),
        ]
        data = _make_data(t, stages=[])
        result = metric.compute(data, SAFE)
        nodes = result.chart_data.nodes
        assert nodes == sorted(nodes)


# ---------------------------------------------------------------------------
# compute — missing data
# ---------------------------------------------------------------------------

class TestComputeWarnings:

    def test_empty_transitions_returns_warning(self, metric):
        result = metric.compute(_make_data([]), SAFE)
        assert result.chart_data is None
        assert result.warnings

    def test_no_chart_data_when_no_transitions(self, metric):
        result = metric.compute(ReportData(), SAFE)
        assert result.chart_data is None


# ---------------------------------------------------------------------------
# layout helpers
# ---------------------------------------------------------------------------

class TestCircularPositions:

    def test_single_node_at_origin(self):
        pos = _circular_positions(["A"])
        assert pos["A"] == (0.0, 0.0)

    def test_all_nodes_on_unit_circle(self):
        nodes = ["A", "B", "C", "D", "E"]
        pos = _circular_positions(nodes)
        for n in nodes:
            x, y = pos[n]
            r = (x ** 2 + y ** 2) ** 0.5
            assert abs(r - 1.0) < 1e-9

    def test_nodes_evenly_spaced(self):
        import math
        nodes = ["A", "B", "C"]
        pos = _circular_positions(nodes)
        coords = list(pos.values())
        dists = []
        for i in range(len(coords)):
            j = (i + 1) % len(coords)
            dx = coords[j][0] - coords[i][0]
            dy = coords[j][1] - coords[i][1]
            dists.append(math.hypot(dx, dy))
        assert max(dists) - min(dists) < 1e-9


class TestEdgeWidth:

    def test_max_edge_gets_max_width(self):
        edge = _Edge("A", "B", count=100, relative=1.0)
        w = _edge_width(edge, max_count=100)
        assert w == pytest.approx(10.0)

    def test_zero_max_count_returns_min_width(self):
        edge = _Edge("A", "B", count=0, relative=0.0)
        w = _edge_width(edge, max_count=0)
        assert w == pytest.approx(1.0)

    def test_half_count_gives_midrange_width(self):
        edge = _Edge("A", "B", count=50, relative=0.5)
        w = _edge_width(edge, max_count=100)
        assert w == pytest.approx(5.5)


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------

class TestRender:

    def _result_with_data(self, metric):
        t = [
            _entry("A-1", "Funnel"), _entry("A-1", "Analysis"),
            _entry("A-2", "Analysis"), _entry("A-2", "Funnel"),  # bidirectional
            _entry("A-3", "Funnel"), _entry("A-3", "Funnel"),    # self-loop
        ]
        return metric.compute(_make_data(t, stages=["Funnel", "Analysis"]), SAFE)

    def test_returns_one_figure(self, metric):
        figs = metric.render(self._result_with_data(metric), SAFE)
        assert len(figs) == 1

    def test_empty_result_returns_no_figures(self, metric):
        result = metric.compute(_make_data([]), SAFE)
        figs = metric.render(result, SAFE)
        assert figs == []

    def test_node_trace_present(self, metric):
        figs = metric.render(self._result_with_data(metric), SAFE)
        # Last trace is the node scatter (markers+text)
        node_trace = figs[0].data[-1]
        assert "markers" in node_trace.mode

    def test_figure_has_annotations(self, metric):
        figs = metric.render(self._result_with_data(metric), SAFE)
        assert len(figs[0].layout.annotations) > 0

    def test_title_contains_issue_count(self, metric):
        figs = metric.render(self._result_with_data(metric), SAFE)
        assert "3 issues" in figs[0].layout.title.text

    def test_metric_id_is_process_flow(self, metric):
        assert metric.metric_id == PROCESS_FLOW
