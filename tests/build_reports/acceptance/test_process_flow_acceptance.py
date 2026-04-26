# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       26.04.2026
# Geändert:       26.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Acceptance-Tests für die Process Flow Metrik auf Basis des realen
#   ART_E-Datensatzes (feedback/Ideen/ART_E_Transitions.xlsx). Prüft
#   fachliche Korrektheit: Anzahl Knoten, Übergänge, Top-Transition,
#   Erkennung bidirektionaler Kanten und korrekte Darstellbarkeit der Figure.
# =============================================================================

"""Acceptance tests for ProcessFlowMetric using the real ART_E dataset."""

from pathlib import Path

import pytest

from build_reports.loader import load_transitions, ReportData
from build_reports.metrics.process_flow import ProcessFlowMetric, _FlowData
from build_reports.terminology import SAFE

ART_E_TRANSITIONS = (
    Path(__file__).parent.parent.parent.parent
    / "feedback" / "Ideen" / "ART_E_Transitions.xlsx"
)


@pytest.fixture(scope="module")
def art_e_data() -> ReportData:
    """Load ART_E Transitions.xlsx once for all acceptance tests."""
    return ReportData(transitions=load_transitions(ART_E_TRANSITIONS))


@pytest.fixture(scope="module")
def art_e_result(art_e_data):
    """Compute ProcessFlowMetric on ART_E data."""
    return ProcessFlowMetric().compute(art_e_data, SAFE)


@pytest.fixture(scope="module")
def art_e_flow(art_e_result) -> _FlowData:
    return art_e_result.chart_data


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

class TestArtELoading:

    def test_transitions_file_loads(self, art_e_data):
        assert len(art_e_data.transitions) == 1137  # 1138 rows - 1 header

    def test_all_entries_have_key_and_label(self, art_e_data):
        assert all(t.key and t.label for t in art_e_data.transitions)

    def test_issue_count_matches_expected(self, art_e_result):
        assert art_e_result.stats["issue_count"] == 341


# ---------------------------------------------------------------------------
# Computed graph structure
# ---------------------------------------------------------------------------

class TestArtEGraphStructure:

    def test_nine_unique_statuses_as_nodes(self, art_e_flow):
        assert art_e_flow.nodes is not None
        assert len(art_e_flow.nodes) == 9

    def test_expected_statuses_present(self, art_e_flow):
        expected = {
            "Backlog", "Completed", "Created", "Done",
            "Funnel", "In Analysis", "In Implementation", "Monitoring", "On Hold",
        }
        assert set(art_e_flow.nodes) == expected

    def test_thirty_unique_transition_pairs(self, art_e_flow):
        assert len(art_e_flow.edges) == 30

    def test_total_transitions_count(self, art_e_result):
        assert art_e_result.stats["total_transitions"] == 796

    def test_no_compute_warnings(self, art_e_result):
        assert art_e_result.warnings == []


# ---------------------------------------------------------------------------
# Top transitions (domain correctness)
# ---------------------------------------------------------------------------

class TestArtETopTransitions:

    def test_top_transition_is_backlog_to_in_implementation(self, art_e_flow):
        top = art_e_flow.edges[0]
        assert top.source == "Backlog"
        assert top.target == "In Implementation"
        assert top.count == 148

    def test_created_to_in_analysis_second(self, art_e_flow):
        counts = {(e.source, e.target): e.count for e in art_e_flow.edges}
        assert counts[("Created", "In Analysis")] == 136

    def test_bidirectional_pair_in_analysis_funnel(self, art_e_flow):
        """Both In Analysis→Funnel and Funnel→In Analysis must exist."""
        pairs = {(e.source, e.target) for e in art_e_flow.edges}
        assert ("In Analysis", "Funnel") in pairs
        assert ("Funnel", "In Analysis") in pairs

    def test_self_loop_funnel_to_funnel(self, art_e_flow):
        self_loops = [e for e in art_e_flow.edges if e.is_self_loop]
        assert any(e.source == "Funnel" for e in self_loops)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

class TestArtERender:

    def test_render_returns_one_figure(self, art_e_result):
        figs = ProcessFlowMetric().render(art_e_result, SAFE)
        assert len(figs) == 1

    def test_figure_title_contains_issue_count(self, art_e_result):
        figs = ProcessFlowMetric().render(art_e_result, SAFE)
        assert "341 issues" in figs[0].layout.title.text

    def test_figure_title_contains_transition_count(self, art_e_result):
        figs = ProcessFlowMetric().render(art_e_result, SAFE)
        assert "796 transitions" in figs[0].layout.title.text

    def test_figure_has_node_and_edge_traces(self, art_e_result):
        figs = ProcessFlowMetric().render(art_e_result, SAFE)
        # edges (30) + 1 node trace + self-loop traces
        assert len(figs[0].data) >= 31

    def test_figure_has_annotations_for_counts(self, art_e_result):
        figs = ProcessFlowMetric().render(art_e_result, SAFE)
        assert len(figs[0].layout.annotations) > 30
