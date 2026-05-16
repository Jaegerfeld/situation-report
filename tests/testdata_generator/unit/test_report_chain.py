# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       17.05.2026
# Geändert:       17.05.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für testdata_generator.gui._build_report_html_file: prüft die
#   Verkettung run_transform → render_combined_html → Temp-HTML. transform_data
#   und build_reports werden gemockt (kein echtes I/O, kein Browser).
# =============================================================================

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from testdata_generator.gui import _build_report_html_file


def test_chain_writes_html_file_and_passes_full_range(tmp_path: Path):
    json_path = tmp_path / "ART_X_generated.json"
    json_path.write_text("{}", encoding="utf-8")
    workflow = tmp_path / "wf.txt"
    workflow.write_text("<First>To Do\n<Closed>Done\n", encoding="utf-8")

    with patch("transform_data.transform.run_transform") as m_tr, \
         patch("build_reports.cli.render_combined_html",
               return_value="<!DOCTYPE html><html></html>") as m_rc:
        out = _build_report_html_file(json_path, workflow, log=lambda _: None)

    assert out.endswith(".html")
    assert Path(out).read_text(encoding="utf-8").startswith("<!DOCTYPE html>")

    # transform called with derived out_dir/prefix
    _, tr_kwargs = m_tr.call_args
    assert tr_kwargs["prefix"] == "ART_X_generated"
    assert tr_kwargs["output_dir"] == tmp_path

    # render called with full range (None/None) and derived xlsx paths
    _, rc_kwargs = m_rc.call_args
    assert rc_kwargs["from_date"] is None
    assert rc_kwargs["to_date"] is None
    assert rc_kwargs["issue_times"] == tmp_path / "ART_X_generated_IssueTimes.xlsx"

    Path(out).unlink()


def test_empty_html_returns_empty_string(tmp_path: Path):
    json_path = tmp_path / "g.json"
    json_path.write_text("{}", encoding="utf-8")
    workflow = tmp_path / "wf.txt"
    workflow.write_text("<First>A\n<Closed>B\n", encoding="utf-8")

    with patch("transform_data.transform.run_transform"), \
         patch("build_reports.cli.render_combined_html", return_value=""):
        out = _build_report_html_file(json_path, workflow, log=lambda _: None)

    assert out == ""
