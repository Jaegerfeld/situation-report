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
    _format_label,
    _node_size,
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
        """Workflow stages appear before non-workflow nodes."""
        t = [
            _entry("A-1", "Funnel"), _entry("A-1", "Analysis"),
            _entry("A-1", "Analysis"), _entry("A-1", "Limbo"),
        ]
        data = _make_data(t, stages=["Funnel", "Analysis"])
        result = metric.compute(data, SAFE)
        nodes = result.chart_data.nodes
        funnel_idx = nodes.index("Funnel")
        analysis_idx = nodes.index("Analysis")
        limbo_idx = nodes.index("Limbo")
        assert funnel_idx < limbo_idx
        assert analysis_idx < limbo_idx

    def test_extra_statuses_appended_alphabetically(self, metric):
        t = [
            _entry("A-1", "Zebra"), _entry("A-1", "Apple"),
            _entry("A-1", "Apple"), _entry("A-1", "Mango"),
        ]
        data = _make_data(t, stages=[])
        result = metric.compute(data, SAFE)
        nodes = result.chart_data.nodes
        assert nodes == sorted(nodes)

    def test_created_maps_to_first_stage(self, metric):
        """'Created' label is replaced by stages[0]; no separate Created node."""
        t = [_entry("A-1", "Created"), _entry("A-1", "Analysis")]
        data = _make_data(t, stages=["Funnel", "Analysis"])
        result = metric.compute(data, SAFE)
        assert result.chart_data is not None
        assert "Created" not in result.chart_data.nodes
        assert any(
            e.source == "Funnel" and e.target == "Analysis"
            for e in result.chart_data.edges
        )

    def test_created_followed_by_first_stage_no_self_loop(self, metric):
        """Created → first_stage → X collapses to first_stage → X, no self-loop."""
        t = [
            _entry("A-1", "Created"),
            _entry("A-1", "Funnel"),
            _entry("A-1", "Analysis"),
        ]
        data = _make_data(t, stages=["Funnel", "Analysis"])
        result = metric.compute(data, SAFE)
        assert not any(e.is_self_loop for e in result.chart_data.edges)

    def test_created_without_workflow_stays_as_created(self, metric):
        """When no stages are defined, 'Created' is kept as-is (no first stage to map to)."""
        t = [_entry("A-1", "Created"), _entry("A-1", "Analysis")]
        data = _make_data(t, stages=[])
        result = metric.compute(data, SAFE)
        assert result.chart_data is not None
        assert "Created" in result.chart_data.nodes


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


# ---------------------------------------------------------------------------
# label helpers
# ---------------------------------------------------------------------------

class TestFormatLabel:

    def test_short_label_unchanged(self):
        assert _format_label("Funnel") == "Funnel"

    def test_long_single_word_unchanged(self):
        assert _format_label("Implementation") == "Implementation"

    def test_long_multiword_wraps(self):
        result = _format_label("In Progress")
        assert "<br>" in result
        parts = result.split("<br>")
        assert len(parts) == 2
        assert all(p.strip() for p in parts)

    def test_wrapped_parts_contain_all_words(self):
        result = _format_label("On Hold Now")
        joined = result.replace("<br>", " ")
        assert joined == "On Hold Now"

    def test_label_at_threshold_unchanged(self):
        # exactly _LABEL_WRAP_AT chars should not be wrapped
        label = "A" * 9
        assert _format_label(label) == label


class TestNodeSize:

    def test_size_increases_with_label_length(self):
        assert _node_size("Done") <= _node_size("Analysis") <= _node_size("Implementation")

    def test_wrapped_label_uses_longest_line_for_sizing(self):
        # "In<br>Progress" → max line "Progress" = 8 chars → same tier as "Analysis" (8)
        assert _node_size("In<br>Progress") == _node_size("Analysis")
