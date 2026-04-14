"""
Unit tests for transform_data.workflow.parse_workflow()

Tests isolate the parsing logic using the simple fixture workflow
and temporary files for error cases.
"""

import pytest
from pathlib import Path

from transform_data.workflow import parse_workflow


def test_stages_are_in_definition_order(simple_workflow_file: Path) -> None:
    wf = parse_workflow(simple_workflow_file)
    assert wf.stages == ["Funnel", "Analysis", "Implementation", "Done"]


def test_canonical_name_maps_to_itself(simple_workflow_file: Path) -> None:
    wf = parse_workflow(simple_workflow_file)
    assert wf.status_to_stage["Funnel"] == "Funnel"
    assert wf.status_to_stage["Analysis"] == "Analysis"


def test_aliases_map_to_canonical_stage(simple_workflow_file: Path) -> None:
    wf = parse_workflow(simple_workflow_file)
    assert wf.status_to_stage["New"] == "Funnel"
    assert wf.status_to_stage["Open"] == "Funnel"
    assert wf.status_to_stage["In Analysis"] == "Analysis"
    assert wf.status_to_stage["In Progress"] == "Implementation"
    assert wf.status_to_stage["In Review"] == "Implementation"
    assert wf.status_to_stage["Closed"] == "Done"


def test_first_stage_marker(simple_workflow_file: Path) -> None:
    wf = parse_workflow(simple_workflow_file)
    assert wf.first_stage == "Analysis"


def test_inprogress_stage_marker(simple_workflow_file: Path) -> None:
    wf = parse_workflow(simple_workflow_file)
    assert wf.inprogress_stage == "Implementation"


def test_closed_stage_marker(simple_workflow_file: Path) -> None:
    wf = parse_workflow(simple_workflow_file)
    assert wf.closed_stage == "Done"


def test_inprogress_defaults_to_implementation(tmp_path: Path) -> None:
    """If <InProgress> is omitted but a stage named 'Implementation' exists,
    inprogress_stage defaults to 'Implementation'."""
    wf_file = tmp_path / "wf.txt"
    wf_file.write_text("Funnel\nImplementation\nDone\n<First>Funnel\n<Closed>Done\n")
    wf = parse_workflow(wf_file)
    assert wf.inprogress_stage == "Implementation"


def test_inprogress_is_none_without_implementation_stage(tmp_path: Path) -> None:
    wf_file = tmp_path / "wf.txt"
    wf_file.write_text("Funnel\nAnalysis\nDone\n<First>Funnel\n<Closed>Done\n")
    wf = parse_workflow(wf_file)
    assert wf.inprogress_stage is None


def test_unknown_first_stage_raises(tmp_path: Path) -> None:
    wf_file = tmp_path / "wf.txt"
    wf_file.write_text("Funnel\nDone\n<First>Typo\n<Closed>Done\n")
    with pytest.raises(ValueError, match="<First>Typo"):
        parse_workflow(wf_file)


def test_unknown_closed_stage_raises(tmp_path: Path) -> None:
    wf_file = tmp_path / "wf.txt"
    wf_file.write_text("Funnel\nDone\n<First>Funnel\n<Closed>Typo\n")
    with pytest.raises(ValueError, match="<Closed>Typo"):
        parse_workflow(wf_file)


def test_unknown_inprogress_stage_raises(tmp_path: Path) -> None:
    wf_file = tmp_path / "wf.txt"
    wf_file.write_text("Funnel\nDone\n<First>Funnel\n<Closed>Done\n<InProgress>Typo\n")
    with pytest.raises(ValueError, match="<InProgress>Typo"):
        parse_workflow(wf_file)


def test_error_message_lists_known_stages(tmp_path: Path) -> None:
    wf_file = tmp_path / "wf.txt"
    wf_file.write_text("Funnel\nAnalysis\nDone\n<First>Typo\n<Closed>Done\n")
    with pytest.raises(ValueError, match="Funnel"):
        parse_workflow(wf_file)
