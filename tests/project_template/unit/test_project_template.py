# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       16.05.2026
# Geändert:       16.05.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für project_template: v5-Round-Trip, Legacy-v4-Erkennung
#   (flaches build_reports-Template ohne "modules"), Abschnitt-Erhalt beim
#   Speichern aus einem einzelnen Modul sowie Sprach-Handling.
# =============================================================================

from __future__ import annotations

import json
from pathlib import Path

import pytest

import project_template as pt


class TestNormalise:
    def test_legacy_v4_wrapped_under_build_reports(self):
        env = pt._normalise(
            {"version": 4, "issue_times": "IT.xlsx", "language": "en"}
        )
        assert env["schema"] == pt.SCHEMA_VERSION
        assert env["modules"][pt.MODULE_BUILD_REPORTS]["issue_times"] == "IT.xlsx"
        assert env["language"] == "en"

    def test_legacy_without_language_defaults(self):
        env = pt._normalise({"version": 4, "issue_times": "X"})
        assert env["language"] == pt.DEFAULT_LANGUAGE

    def test_v5_envelope_passthrough(self):
        env = pt._normalise(
            {
                "schema": 5,
                "language": "fr",
                "modules": {pt.MODULE_HELPER: {"output": "m.json"}},
            }
        )
        assert env["language"] == "fr"
        assert env["modules"][pt.MODULE_HELPER]["output"] == "m.json"

    def test_non_dict_raises(self):
        with pytest.raises(ValueError):
            pt._normalise(["not", "a", "dict"])


class TestRoundTrip:
    def test_save_and_load_single_section(self, tmp_path: Path):
        f = tmp_path / "proj.json"
        pt.save_template(
            f, pt.MODULE_TRANSFORM_DATA, {"prefix": "ART_A"}, language="de"
        )
        env = pt.load_template(f)
        assert env["schema"] == 5
        assert pt.get_section(env, pt.MODULE_TRANSFORM_DATA)["prefix"] == "ART_A"
        assert env["language"] == "de"

    def test_section_preserved_across_modules(self, tmp_path: Path):
        f = tmp_path / "proj.json"
        pt.save_template(f, pt.MODULE_BUILD_REPORTS, {"issue_times": "IT.xlsx"})
        pt.save_template(f, pt.MODULE_TESTDATA_GENERATOR, {"project": "TEST"})

        env = pt.load_template(f)
        assert pt.get_section(env, pt.MODULE_BUILD_REPORTS)["issue_times"] == "IT.xlsx"
        assert pt.get_section(env, pt.MODULE_TESTDATA_GENERATOR)["project"] == "TEST"

    def test_resave_replaces_only_own_section(self, tmp_path: Path):
        f = tmp_path / "proj.json"
        pt.save_template(f, pt.MODULE_HELPER, {"output": "a.json"})
        pt.save_template(f, pt.MODULE_BUILD_REPORTS, {"cfd": "C.xlsx"})
        pt.save_template(f, pt.MODULE_HELPER, {"output": "b.json"})

        env = pt.load_template(f)
        assert pt.get_section(env, pt.MODULE_HELPER)["output"] == "b.json"
        assert pt.get_section(env, pt.MODULE_BUILD_REPORTS)["cfd"] == "C.xlsx"

    def test_save_onto_legacy_v4_file_upgrades_and_preserves(self, tmp_path: Path):
        f = tmp_path / "legacy.json"
        f.write_text(
            json.dumps({"version": 4, "issue_times": "old.xlsx"}),
            encoding="utf-8",
        )
        pt.save_template(f, pt.MODULE_HELPER, {"output": "m.json"})

        on_disk = json.loads(f.read_text(encoding="utf-8"))
        assert on_disk["schema"] == 5
        assert on_disk["modules"][pt.MODULE_BUILD_REPORTS]["issue_times"] == "old.xlsx"
        assert on_disk["modules"][pt.MODULE_HELPER]["output"] == "m.json"

    def test_language_kept_when_not_passed(self, tmp_path: Path):
        f = tmp_path / "proj.json"
        pt.save_template(f, pt.MODULE_HELPER, {"output": "x"}, language="fr")
        pt.save_template(f, pt.MODULE_BUILD_REPORTS, {"cfd": "y"})
        assert pt.load_template(f)["language"] == "fr"

    def test_get_section_missing_returns_empty(self, tmp_path: Path):
        f = tmp_path / "proj.json"
        pt.save_template(f, pt.MODULE_HELPER, {"output": "x"})
        env = pt.load_template(f)
        assert pt.get_section(env, pt.MODULE_TRANSFORM_DATA) == {}
