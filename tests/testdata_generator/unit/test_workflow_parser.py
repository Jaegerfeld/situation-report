# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       02.05.2026
# Geändert:       02.05.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für testdata_generator.workflow_parser (Re-Export von
#   transform_data.workflow). Prüft, dass der via testdata_generator
#   exportierte Parser für alle relevanten Workflow-Formate korrekte
#   WorkflowSpec-Objekte erzeugt.
# =============================================================================

from __future__ import annotations

from pathlib import Path

import pytest

from testdata_generator.workflow_parser import WorkflowSpec, parse_workflow


@pytest.fixture()
def simple_workflow(tmp_path: Path) -> Path:
    """Minimal workflow with three stages, markers, and one alias."""
    content = (
        "Funnel:New\n"
        "Analysis:In Analysis\n"
        "Done:Closed\n"
        "<First>Analysis\n"
        "<Closed>Done\n"
    )
    p = tmp_path / "workflow.txt"
    p.write_text(content, encoding="utf-8")
    return p


@pytest.fixture()
def no_markers_workflow(tmp_path: Path) -> Path:
    """Workflow without <First> / <Closed> markers."""
    content = "Backlog\nIn Progress\nDone\n"
    p = tmp_path / "workflow_no_markers.txt"
    p.write_text(content, encoding="utf-8")
    return p


class TestParseStages:
    def test_stages_in_order(self, simple_workflow: Path) -> None:
        """Stages are returned in file order."""
        spec = parse_workflow(simple_workflow)
        assert spec.stages == ["Funnel", "Analysis", "Done"]

    def test_stage_count(self, simple_workflow: Path) -> None:
        """All defined stages are present."""
        spec = parse_workflow(simple_workflow)
        assert len(spec.stages) == 3


class TestMarkers:
    def test_first_stage_marker(self, simple_workflow: Path) -> None:
        """<First> marker sets first_stage correctly."""
        spec = parse_workflow(simple_workflow)
        assert spec.first_stage == "Analysis"

    def test_closed_stage_marker(self, simple_workflow: Path) -> None:
        """<Closed> marker sets closed_stage correctly."""
        spec = parse_workflow(simple_workflow)
        assert spec.closed_stage == "Done"

    def test_missing_markers_first_is_none(self, no_markers_workflow: Path) -> None:
        """Without <First> marker, first_stage is None."""
        spec = parse_workflow(no_markers_workflow)
        assert spec.first_stage is None

    def test_missing_markers_closed_is_none(self, no_markers_workflow: Path) -> None:
        """Without <Closed> marker, closed_stage is None."""
        spec = parse_workflow(no_markers_workflow)
        assert spec.closed_stage is None


class TestAliases:
    def test_alias_maps_to_canonical(self, simple_workflow: Path) -> None:
        """Aliases are mapped to their canonical stage name."""
        spec = parse_workflow(simple_workflow)
        assert spec.status_to_stage["New"] == "Funnel"
        assert spec.status_to_stage["In Analysis"] == "Analysis"
        assert spec.status_to_stage["Closed"] == "Done"

    def test_canonical_maps_to_itself(self, simple_workflow: Path) -> None:
        """Canonical stage names map to themselves."""
        spec = parse_workflow(simple_workflow)
        assert spec.status_to_stage["Funnel"] == "Funnel"
        assert spec.status_to_stage["Analysis"] == "Analysis"


class TestReturnType:
    def test_returns_workflow_spec(self, simple_workflow: Path) -> None:
        """parse_workflow returns a WorkflowSpec (Workflow alias)."""
        spec = parse_workflow(simple_workflow)
        assert isinstance(spec, WorkflowSpec)
