# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       26.04.2026
# Geändert:       26.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für transform_data.transform.run_transform. Prüft die
#   End-to-End-Pipeline: korrekte Ausgabedateien, Log-Ausgaben für
#   Issuezählung, Pfade, fehlende Workflow-Marker und unmappte Status.
# =============================================================================

"""Unit tests for transform_data.transform.run_transform."""

import json
from pathlib import Path

import pytest

from transform_data.transform import run_transform


WORKFLOW_FULL = "\n".join([
    "Funnel",
    "Analysis",
    "Done",
    "<First>Analysis",
    "<Closed>Done",
])

WORKFLOW_NO_MARKERS = "\n".join(["Funnel", "Analysis", "Done"])


def _make_issue(key: str = "T-1", to_status: str = "Analysis") -> dict:
    """Build a minimal Jira issue dict with one status transition."""
    return {
        "key": key,
        "fields": {
            "project": {"key": "T"},
            "issuetype": {"name": "Story"},
            "status": {"name": to_status},
            "created": "2025-01-01T09:00:00.000+0100",
            "components": [],
            "resolution": None,
        },
        "changelog": {
            "histories": [{
                "created": "2025-01-02T10:00:00.000+0100",
                "items": [{"field": "status", "fromString": "Funnel", "toString": to_status}],
            }]
        },
    }


@pytest.fixture
def workflow_file(tmp_path) -> Path:
    """Three-stage workflow with <First> and <Closed> markers."""
    p = tmp_path / "workflow.txt"
    p.write_text(WORKFLOW_FULL)
    return p


@pytest.fixture
def json_file(tmp_path) -> Path:
    """Jira JSON export with a single issue (T-1 → Analysis)."""
    p = tmp_path / "T.json"
    p.write_text(json.dumps({"issues": [_make_issue()]}))
    return p


class TestRunTransform:
    """Tests for run_transform — full pipeline orchestration."""

    def test_creates_all_three_output_files(self, json_file, workflow_file, tmp_path):
        """run_transform writes Transitions, IssueTimes, and CFD xlsx files."""
        out = tmp_path / "out"
        run_transform(json_file, workflow_file, output_dir=out, prefix="T")
        assert (out / "T_Transitions.xlsx").exists()
        assert (out / "T_IssueTimes.xlsx").exists()
        assert (out / "T_CFD.xlsx").exists()

    def test_default_output_dir_is_json_parent(self, json_file, workflow_file):
        """Without output_dir, files are written next to the JSON file."""
        run_transform(json_file, workflow_file)
        assert (json_file.parent / "T_Transitions.xlsx").exists()
        assert (json_file.parent / "T_IssueTimes.xlsx").exists()

    def test_default_prefix_is_json_stem(self, json_file, workflow_file):
        """Without prefix, the JSON file stem is used as output prefix."""
        run_transform(json_file, workflow_file)
        assert (json_file.parent / "T_Transitions.xlsx").exists()

    def test_log_reports_issue_count(self, json_file, workflow_file, tmp_path):
        """log is called with a message containing the number of processed issues."""
        messages: list[str] = []
        run_transform(json_file, workflow_file, output_dir=tmp_path, prefix="T",
                      log=messages.append)
        assert any("1" in m and "issue" in m.lower() for m in messages)

    def test_log_reports_all_three_output_paths(self, json_file, workflow_file, tmp_path):
        """log is called with the paths of all three output files."""
        messages: list[str] = []
        run_transform(json_file, workflow_file, output_dir=tmp_path, prefix="T",
                      log=messages.append)
        combined = "\n".join(messages)
        assert "Transitions.xlsx" in combined
        assert "IssueTimes.xlsx" in combined
        assert "CFD.xlsx" in combined

    def test_missing_first_marker_is_logged(self, json_file, tmp_path):
        """A warning is logged when <First> marker is absent from the workflow."""
        wf = tmp_path / "wf_no_markers.txt"
        wf.write_text(WORKFLOW_NO_MARKERS)
        messages: list[str] = []
        run_transform(json_file, wf, output_dir=tmp_path, prefix="T", log=messages.append)
        assert any("First" in m for m in messages)

    def test_missing_closed_marker_is_logged(self, json_file, tmp_path):
        """A warning is logged when <Closed> marker is absent from the workflow."""
        wf = tmp_path / "wf_no_markers.txt"
        wf.write_text(WORKFLOW_NO_MARKERS)
        messages: list[str] = []
        run_transform(json_file, wf, output_dir=tmp_path, prefix="T", log=messages.append)
        assert any("Closed" in m for m in messages)

    def test_unmapped_status_is_logged(self, workflow_file, tmp_path):
        """A warning is logged when a Jira status does not appear in the workflow."""
        issue = _make_issue(to_status="Unknown Status")
        issue["changelog"]["histories"][0]["items"][0]["fromString"] = "Unknown Status"
        jf = tmp_path / "T.json"
        jf.write_text(json.dumps({"issues": [issue]}))
        messages: list[str] = []
        run_transform(jf, workflow_file, output_dir=tmp_path, prefix="T", log=messages.append)
        assert any("WARNUNG" in m for m in messages)

    def test_multiple_issues_all_processed(self, workflow_file, tmp_path):
        """Multiple issues in the JSON are all written to the output files."""
        import openpyxl
        issues = [_make_issue(key=f"T-{i}") for i in range(1, 6)]
        jf = tmp_path / "T.json"
        jf.write_text(json.dumps({"issues": issues}))
        messages: list[str] = []
        run_transform(jf, workflow_file, output_dir=tmp_path, prefix="T", log=messages.append)
        assert any("5" in m for m in messages)
        wb = openpyxl.load_workbook(tmp_path / "T_IssueTimes.xlsx")
        ws = wb.active
        assert ws.max_row == 6  # header + 5 issues
