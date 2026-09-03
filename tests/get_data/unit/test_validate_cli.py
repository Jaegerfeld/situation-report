# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für get_data.validate und die CLI (C3, Export-Weg):
#   Export-Prüfung (Pflichtfelder, fehlender Changelog, vergessene
#   Folgeseiten, Duplikate) — auch gegen die ECHTEN Rohdaten des
#   Testdaten-Generators — sowie die Unterbefehle fetch (gemockt,
#   Token nur per Umgebungsvariable) und check (Exit-Codes).
#   Zusätzlich der GUI-Übersetzungs-Paritätstest (de/en).
# =============================================================================

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from get_data.cli import main as cli_main
from get_data.validate import validate_export, validate_export_file


def _issue(key: str = "A-1", changelog: bool = True) -> dict:
    issue = {"key": key,
             "fields": {"issuetype": {"name": "Feature"},
                        "created": "2025-01-01T09:00:00.000+0000",
                        "status": {"name": "Done"}}}
    if changelog:
        issue["changelog"] = {"histories": [{"items": []}]}
    return issue


class TestValidateExport:
    def test_valid_envelope_and_bare_list(self) -> None:
        envelope = {"total": 2, "issues": [_issue("A-1"), _issue("A-2")]}
        assert validate_export(envelope).ok
        assert validate_export([_issue("A-1")]).ok

    def test_real_testdata_export_passes(self) -> None:
        raw = json.loads(Path("testdata_generator/ART_A.json")
                         .read_text(encoding="utf-8"))
        check = validate_export(raw)
        assert check.ok, check.errors
        assert check.issue_count > 0

    def test_rejects_non_export_and_empty(self) -> None:
        assert not validate_export({"foo": 1}).ok
        assert not validate_export({"issues": []}).ok
        assert not validate_export("nope").ok

    def test_missing_required_fields_are_errors(self) -> None:
        broken = _issue("A-1")
        del broken["fields"]["created"]
        check = validate_export({"issues": [broken, _issue("A-2")]})
        assert not check.ok
        assert any("fields.created" in e for e in check.errors)

    def test_missing_changelog_everywhere_is_error_partial_is_warning(self) -> None:
        all_missing = validate_export(
            {"issues": [_issue("A-1", changelog=False)]})
        assert any("expand=changelog" in e for e in all_missing.errors)
        partial = validate_export(
            {"issues": [_issue("A-1"), _issue("A-2", changelog=False)]})
        assert partial.ok
        assert any("no changelog" in w for w in partial.warnings)

    def test_forgotten_pages_detected_via_total(self) -> None:
        check = validate_export({"total": 250, "issues": [_issue("A-1")]})
        assert not check.ok
        assert any("pages are missing" in e for e in check.errors)

    def test_duplicates_warn_and_point_to_helper(self) -> None:
        check = validate_export({"issues": [_issue("A-1"), _issue("A-1")]})
        assert check.ok
        assert any("helper" in w for w in check.warnings)

    def test_file_read_and_json_errors_become_errors(self, tmp_path) -> None:
        missing = validate_export_file(tmp_path / "nope.json")
        assert any("Cannot read" in e for e in missing.errors)
        bad = tmp_path / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        assert any("valid JSON" in e
                   for e in validate_export_file(bad).errors)


class TestCli:
    def test_check_exit_codes(self, tmp_path, capsys) -> None:
        good = tmp_path / "good.json"
        good.write_text(json.dumps({"issues": [_issue()]}), encoding="utf-8")
        assert cli_main(["check", str(good)]) == 0
        assert "ready for transform_data" in capsys.readouterr().out

        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps({"total": 9, "issues": [_issue()]}),
                       encoding="utf-8")
        assert cli_main(["check", str(bad)]) == 2

    def test_fetch_requires_token_env(self, tmp_path, capsys,
                                      monkeypatch) -> None:
        monkeypatch.delenv("JIRA_TOKEN", raising=False)
        rc = cli_main(["fetch", "--url", "https://j.example.com",
                       "--project", "A", "--output",
                       str(tmp_path / "out.json")])
        assert rc == 1
        assert "JIRA_TOKEN" in capsys.readouterr().err

    def test_fetch_happy_path_with_mocked_client(self, tmp_path,
                                                 monkeypatch) -> None:
        monkeypatch.setenv("JIRA_TOKEN", "tok")
        with patch("get_data.cli.fetch_to_file", return_value=3) as m_fetch:
            rc = cli_main(["fetch", "--url", "https://j.example.com",
                           "--project", "ART_A", "--auth", "bearer",
                           "--output", str(tmp_path / "out.json")])
        assert rc == 0
        config = m_fetch.call_args.args[0]
        assert config.token == "tok"
        assert config.auth_mode == "bearer"

    def test_fetch_surfaces_client_errors(self, tmp_path, capsys,
                                          monkeypatch) -> None:
        monkeypatch.setenv("JIRA_TOKEN", "tok")
        with patch("get_data.cli.fetch_to_file",
                   side_effect=RuntimeError("HTTP 401")):
            rc = cli_main(["fetch", "--url", "https://j.example.com",
                           "--project", "A", "--output",
                           str(tmp_path / "o.json")])
        assert rc == 1
        assert "HTTP 401" in capsys.readouterr().err


class TestGuiTranslations:
    def test_de_and_en_have_identical_keys_and_no_empty_values(self) -> None:
        from get_data.gui import _T
        assert set(_T["de"].keys()) == set(_T["en"].keys())
        for lang, entries in _T.items():
            for key, value in entries.items():
                assert value, f"Empty translation [{lang}][{key}]"
