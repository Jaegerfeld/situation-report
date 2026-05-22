# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       22.05.2026
# Geändert:       22.05.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Acceptance-Test für die Datenübergabe transform_data → build_reports.
#   Führt eine echte Transformation auf dem ART_A-Datensatz aus, schreibt das
#   Handover-Template und prüft, dass build_reports daraus exakt die drei
#   erzeugten XLSX-Dateien und die Workflow-Datei wieder ausliest.
# =============================================================================

"""Acceptance test for the transform_data → build_reports data hand-over."""

from pathlib import Path

import project_template as pt
from build_reports.gui import _parse_template_dict
from transform_data.gui import write_handover_template
from transform_data.transform import run_transform


def test_handover_template_round_trips_to_build_reports(
    ata_json: Path, ata_workflow: Path, tmp_path: Path
):
    """A hand-over template written after a real run is loadable by build_reports."""
    out_dir = tmp_path / "out"
    result = run_transform(ata_json, ata_workflow, output_dir=out_dir, prefix="ART_A")

    handover = tmp_path / "handover.json"
    write_handover_template(
        handover,
        result,
        json_file=str(ata_json),
        workflow_file=str(ata_workflow),
        output_dir=str(out_dir),
        prefix="ART_A",
        language="en",
    )

    envelope = pt.load_template(handover)

    # build_reports section carries the three transformed files + workflow
    br_section = pt.get_section(envelope, pt.MODULE_BUILD_REPORTS)
    state = _parse_template_dict(br_section)
    assert Path(state["issue_times"]) == result.issue_times
    assert Path(state["cfd"]) == result.cfd
    assert Path(state["transitions"]) == result.transitions
    assert Path(state["workflow"]) == ata_workflow
    assert state["pi_config"] == ""

    # All referenced report files actually exist on disk
    for key in ("issue_times", "cfd", "transitions"):
        assert Path(state[key]).is_file()

    # transform_data section is preserved for round-tripping the source paths
    td_section = pt.get_section(envelope, pt.MODULE_TRANSFORM_DATA)
    assert td_section["json_file"] == str(ata_json)
    assert td_section["prefix"] == "ART_A"
    assert envelope["language"] == "en"


def test_handover_carries_loaded_template_build_reports_settings(
    ata_json: Path, ata_workflow: Path, tmp_path: Path
):
    """A loaded project template's PI config and filters reach build_reports."""
    out_dir = tmp_path / "out"
    result = run_transform(ata_json, ata_workflow, output_dir=out_dir, prefix="ART_A")

    # A project template the user had loaded in transform_data, carrying
    # build_reports settings that transform_data itself never produces.
    base_tpl = tmp_path / "project.json"
    pt.save_template(
        base_tpl,
        pt.MODULE_BUILD_REPORTS,
        {
            "issue_times": "outdated.xlsx",
            "pi_config": str(tmp_path / "pi_config.json"),
            "projects": "ART_A",
            "metrics": {"flow_time": True, "cfd": False},
        },
        language="en",
    )

    handover = tmp_path / "handover.json"
    write_handover_template(
        handover,
        result,
        json_file=str(ata_json),
        workflow_file=str(ata_workflow),
        output_dir=str(out_dir),
        prefix="ART_A",
        language="en",
        base_template=base_tpl,
    )

    section = pt.get_section(pt.load_template(handover), pt.MODULE_BUILD_REPORTS)
    state = _parse_template_dict(section)
    # fresh transform output replaces the outdated path
    assert Path(state["issue_times"]) == result.issue_times
    # build_reports settings from the loaded template carry over
    assert Path(state["pi_config"]) == tmp_path / "pi_config.json"
    assert state["projects"] == "ART_A"
    assert state["metrics"] == {"flow_time": True, "cfd": False}
