# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       22.05.2026
# Geändert:       22.05.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für die Tk-freien Hilfsfunktionen von transform_data.gui:
#   den Aufbau des build_reports-Abschnitts und das Schreiben des
#   Handover-Templates für die Datenübergabe an build_reports.
# =============================================================================

"""Unit tests for the Tk-free hand-over helpers in transform_data.gui."""

from pathlib import Path

import project_template as pt
from transform_data.gui import _build_handover_section, write_handover_template
from transform_data.transform import TransformResult


def _result(base: Path) -> TransformResult:
    """Build a TransformResult pointing at three XLSX paths under base."""
    return TransformResult(
        transitions=base / "P_Transitions.xlsx",
        issue_times=base / "P_IssueTimes.xlsx",
        cfd=base / "P_CFD.xlsx",
    )


def test_build_handover_section_maps_all_paths(tmp_path):
    """_build_handover_section fills the four build_reports path keys."""
    section = _build_handover_section(_result(tmp_path), str(tmp_path / "wf.txt"))
    assert section["issue_times"] == str(tmp_path / "P_IssueTimes.xlsx")
    assert section["cfd"] == str(tmp_path / "P_CFD.xlsx")
    assert section["transitions"] == str(tmp_path / "P_Transitions.xlsx")
    assert section["workflow"] == str(tmp_path / "wf.txt")


def test_build_handover_section_leaves_pi_config_empty(tmp_path):
    """The PI config stays empty — the user selects it in build_reports."""
    section = _build_handover_section(_result(tmp_path), "wf.txt")
    assert section["pi_config"] == ""


def test_write_handover_template_writes_both_sections(tmp_path):
    """write_handover_template stores a transform_data and a build_reports section."""
    handover = tmp_path / "handover.json"
    write_handover_template(
        handover,
        _result(tmp_path),
        json_file=str(tmp_path / "P.json"),
        workflow_file=str(tmp_path / "wf.txt"),
        output_dir=str(tmp_path),
        prefix="P",
        language="de",
    )
    envelope = pt.load_template(handover)
    assert pt.get_section(envelope, pt.MODULE_BUILD_REPORTS)["cfd"] == str(
        tmp_path / "P_CFD.xlsx"
    )
    assert pt.get_section(envelope, pt.MODULE_TRANSFORM_DATA)["prefix"] == "P"
    assert envelope["language"] == "de"


def test_build_handover_section_merges_base_section(tmp_path):
    """A base section's PI config / filters are preserved; only paths are replaced."""
    base = {
        "issue_times": "stale.xlsx",
        "pi_config": "my_pi.json",
        "projects": "ART_A,ART_B",
        "metrics": {"flow_time": True, "cfd": False},
    }
    section = _build_handover_section(_result(tmp_path), "wf.txt", base)
    # fresh paths win
    assert section["issue_times"] == str(tmp_path / "P_IssueTimes.xlsx")
    assert section["workflow"] == "wf.txt"
    # build_reports-only settings carry over from the base section
    assert section["pi_config"] == "my_pi.json"
    assert section["projects"] == "ART_A,ART_B"
    assert section["metrics"] == {"flow_time": True, "cfd": False}


def test_write_handover_template_carries_base_template_settings(tmp_path):
    """write_handover_template merges a base template's build_reports section."""
    base_tpl = tmp_path / "project.json"
    pt.save_template(
        base_tpl,
        pt.MODULE_BUILD_REPORTS,
        {"issue_times": "old.xlsx", "pi_config": "pi.json", "projects": "ART_A"},
        language="en",
    )
    handover = tmp_path / "handover.json"
    write_handover_template(
        handover,
        _result(tmp_path),
        json_file=str(tmp_path / "P.json"),
        workflow_file=str(tmp_path / "wf.txt"),
        output_dir=str(tmp_path),
        prefix="P",
        language="en",
        base_template=base_tpl,
    )
    section = pt.get_section(pt.load_template(handover), pt.MODULE_BUILD_REPORTS)
    assert section["cfd"] == str(tmp_path / "P_CFD.xlsx")
    assert section["pi_config"] == "pi.json"
    assert section["projects"] == "ART_A"


def test_write_handover_template_ignores_unreadable_base_template(tmp_path):
    """A missing base template is ignored — the hand-over still works."""
    handover = tmp_path / "handover.json"
    write_handover_template(
        handover,
        _result(tmp_path),
        json_file=str(tmp_path / "P.json"),
        workflow_file=str(tmp_path / "wf.txt"),
        output_dir=str(tmp_path),
        prefix="P",
        language="en",
        base_template=tmp_path / "does_not_exist.json",
    )
    section = pt.get_section(pt.load_template(handover), pt.MODULE_BUILD_REPORTS)
    assert section["cfd"] == str(tmp_path / "P_CFD.xlsx")
    assert section["pi_config"] == ""
