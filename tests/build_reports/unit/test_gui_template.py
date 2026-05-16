# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       16.05.2026
# Geändert:       16.05.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für die Integration von build_reports.gui mit dem gemeinsamen
#   project_template (v5-Hülle). Prüft Round-Trip über save/load und das
#   Lesen alter v4-Templates (flach, ohne "modules").
# =============================================================================

from __future__ import annotations

import json
from pathlib import Path

import project_template as pt
from build_reports.gui import _build_template_dict, _parse_template_dict


def test_v5_round_trip_via_project_template(tmp_path: Path):
    f = tmp_path / "proj.json"
    tpl = _build_template_dict(
        issue_times="IT.xlsx", cfd="C.xlsx", from_date="", to_date="",
        projects="", issuetypes="", terminology="SAFe", ct_method="A",
        metrics={"cfd": True, "flow_time": False}, language="de",
    )
    pt.save_template(f, pt.MODULE_BUILD_REPORTS, tpl, language="de")

    env = pt.load_template(f)
    section = pt.get_section(env, pt.MODULE_BUILD_REPORTS)
    state = _parse_template_dict(section)
    assert state["issue_times"] == "IT.xlsx"
    assert state["metrics"] == {"cfd": True, "flow_time": False}


def test_legacy_v4_flat_file_still_loads(tmp_path: Path):
    f = tmp_path / "legacy.json"
    f.write_text(
        json.dumps({"version": 4, "issue_times": "old.xlsx", "language": "en"}),
        encoding="utf-8",
    )
    env = pt.load_template(f)
    section = pt.get_section(env, pt.MODULE_BUILD_REPORTS)
    section.setdefault("language", env["language"])
    state = _parse_template_dict(section)
    assert state["issue_times"] == "old.xlsx"
    assert state["language"] == "en"
