# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       22.06.2026
# Geändert:       22.06.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für die display-unabhängigen Teile von portfolio.gui: die
#   Übersetzungstabelle _T (alle 5 Sprachen, gleiche Keys, keine Leerwerte) und
#   die Form→SolutionConfig-Logik. Der tkinter-Teil wird nicht instanziiert.
# =============================================================================

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from portfolio.gui import (
    _T,
    LANG_DE,
    LANG_EN,
    LANG_FR,
    LANG_PT,
    LANG_RO,
    _build_delta_html_file,
    _member_dict,
    build_config_from_fields,
    default_metrics_for_mode,
)
from portfolio.solution_config import (
    KIND_PORTFOLIO,
    KIND_SOLUTION,
    MODE_COMPARISON,
    MODE_POOLED,
)

_ALL_LANGS = (LANG_DE, LANG_EN, LANG_RO, LANG_PT, LANG_FR)


class TestTranslations:
    def test_all_languages_present(self) -> None:
        for lang in _ALL_LANGS:
            assert lang in _T

    def test_same_keys_in_all_languages(self) -> None:
        ref = set(_T[LANG_DE].keys())
        for lang in _ALL_LANGS:
            assert set(_T[lang].keys()) == ref, (
                f"Key mismatch in [{lang}]: "
                f"extra={set(_T[lang]) - ref}, missing={ref - set(_T[lang])}"
            )

    def test_no_empty_values(self) -> None:
        for lang, entries in _T.items():
            for key, value in entries.items():
                assert value, f"Empty translation [{lang}][{key}]"


class TestMemberDict:
    def test_json_source_is_template(self) -> None:
        assert _member_dict("ART A", "C:/x/ART_A.json") == {
            "name": "ART A", "template": "C:/x/ART_A.json"}

    def test_xlsx_source_is_issue_times(self) -> None:
        d = _member_dict("ART B", "C:/x/ART_B_IssueTimes.xlsx")
        assert d == {"name": "ART B", "issue_times": "C:/x/ART_B_IssueTimes.xlsx"}

    def test_strips_whitespace(self) -> None:
        assert _member_dict("  ART A  ", "  x.json ")["name"] == "ART A"

    def test_portfolio_source_always_template(self) -> None:
        # Even a non-.json path is stored as a solution template for portfolios.
        d = _member_dict("Sol A", "C:/x/solutionA.xlsx", KIND_PORTFOLIO)
        assert d == {"name": "Sol A", "template": "C:/x/solutionA.xlsx"}


class TestBuildConfigFromFields:
    def test_builds_valid_config(self) -> None:
        cfg = build_config_from_fields(
            "Payments", "SAFe", "2025-01-01", "2025-12-31",
            [("ART A", "a.json"), ("ART B", "b.xlsx")], MODE_POOLED)
        assert cfg.name == "Payments"
        assert [m.name for m in cfg.members] == ["ART A", "ART B"]
        assert cfg.members[0].template == "a.json"
        assert cfg.members[1].issue_times == "b.xlsx"
        assert cfg.from_date == date(2025, 1, 1)
        assert cfg.modes == [MODE_POOLED]

    def test_ignores_empty_member_rows(self) -> None:
        cfg = build_config_from_fields(
            "Payments", "SAFe", "", "",
            [("ART A", "a.json"), ("", ""), ("ART B", "  ")], MODE_COMPARISON)
        assert [m.name for m in cfg.members] == ["ART A"]
        assert cfg.modes == [MODE_COMPARISON]

    def test_no_dates_means_none(self) -> None:
        cfg = build_config_from_fields(
            "X", "SAFe", "", "", [("ART A", "a.json")], MODE_POOLED)
        assert cfg.from_date is None and cfg.to_date is None

    def test_missing_name_raises(self) -> None:
        with pytest.raises(ValueError):
            build_config_from_fields(
                "", "SAFe", "", "", [("ART A", "a.json")], MODE_POOLED)

    def test_builds_portfolio(self) -> None:
        cfg = build_config_from_fields(
            "Tribe", "SAFe", "", "",
            [("Solution A", "solA.json"), ("Solution B", "solB.json")],
            MODE_POOLED, kind=KIND_PORTFOLIO)
        assert cfg.kind == KIND_PORTFOLIO
        assert [m.template for m in cfg.members] == ["solA.json", "solB.json"]

    def test_portfolio_member_without_template_raises(self) -> None:
        # A portfolio member given a non-template (.xlsx) is still stored as
        # template by _member_dict, so this stays valid; an empty source is
        # ignored. A portfolio with no usable members must raise.
        with pytest.raises(ValueError):
            build_config_from_fields(
                "Tribe", "SAFe", "", "", [("Solution A", "")],
                MODE_POOLED, kind=KIND_PORTFOLIO)

    def test_default_kind_is_solution(self) -> None:
        cfg = build_config_from_fields(
            "X", "SAFe", "", "", [("ART A", "a.json")], MODE_POOLED)
        assert cfg.kind == KIND_SOLUTION

    def test_terminology_flows_through(self) -> None:
        cfg = build_config_from_fields(
            "X", "SAFe", "", "", [("ART A", "a.json")], MODE_POOLED,
            terminology="Global")
        assert cfg.terminology == "Global"

    def test_terminology_defaults_safe(self) -> None:
        cfg = build_config_from_fields(
            "X", "SAFe", "", "", [("ART A", "a.json")], MODE_POOLED)
        assert cfg.terminology == "SAFe"

    def test_no_members_raises(self) -> None:
        with pytest.raises(ValueError):
            build_config_from_fields("X", "SAFe", "", "", [("", "")], MODE_POOLED)


class TestDefaultMetricsForMode:
    def test_pooled_excludes_flow_load(self) -> None:
        assert "flow_load" not in default_metrics_for_mode(MODE_POOLED)

    def test_comparison_includes_flow_load(self) -> None:
        assert "flow_load" in default_metrics_for_mode(MODE_COMPARISON)


class TestBuildDeltaHtmlFile:
    def test_renders_delta_of_two_snapshot_files(self, tmp_path) -> None:
        from datetime import date as _date

        from portfolio.snapshot import Snapshot, save_snapshot

        def snap(as_of: _date, completed: int) -> Snapshot:
            return Snapshot(
                name="Demo", kind="portfolio", as_of=as_of,
                created="2025-06-30T12:00:00", target_ct=90,
                total={"label": "Demo", "items": 100, "completed": completed,
                       "open": 100 - completed, "median_ct": 8.0,
                       "p85_ct": 18.0, "p95_ct": 30.0, "target_ct_pct": 95.0,
                       "median_lt": 16.0, "p85_lt": 39.0},
                governance={"risks": [], "dependencies": [], "nfr": [],
                            "runway": [], "capabilities": [], "decisions": []})

        prev_p = tmp_path / "prev.json"
        now_p = tmp_path / "now.json"
        save_snapshot(prev_p, snap(_date(2025, 6, 16), 60))
        save_snapshot(now_p, snap(_date(2025, 6, 30), 75))

        out = _build_delta_html_file(prev_p, now_p)
        html = Path(out).read_text(encoding="utf-8")
        assert html.startswith("<!DOCTYPE html>")
        assert "+15 items completed" in html
        Path(out).unlink()

    def test_propagates_snapshot_errors(self, tmp_path) -> None:
        from portfolio.snapshot import Snapshot, save_snapshot

        a = tmp_path / "a.json"
        b = tmp_path / "b.json"
        save_snapshot(a, Snapshot(name="A", kind="solution", as_of=date(2025, 6, 1),
                                  created="", target_ct=90, total={}))
        save_snapshot(b, Snapshot(name="B", kind="solution", as_of=date(2025, 6, 2),
                                  created="", target_ct=90, total={}))
        with pytest.raises(ValueError, match="different reports"):
            _build_delta_html_file(a, b)


class TestPreservedFieldsRoundTrip:
    """Phase 0 des Portfolio-Datenraum-Konzepts (04.09.2026): Felder, die
    das Formular nicht editiert, muessen jeden Neuaufbau aus den Feldern
    ueberleben (Speichern, Report, Snapshot, Mappe)."""

    def _loaded(self):
        from portfolio.solution_config import parse_solution_config
        return parse_solution_config({
            "schema": 1, "app": "situation_report", "kind": KIND_SOLUTION,
            "name": "Beta", "framework": "LeSS",
            "members": [{"name": "B-1", "issue_times": "b1.xlsx"}],
            "stage_map": {"stages": {"Vorlauf": ["Backlog"],
                                     "Umsetzung": ["Dev"],
                                     "Fertig": ["Done"]},
                          "first_stage": "Umsetzung",
                          "closed_stage": "Fertig"},
            "risks": "registers/risks.json", "nfr": "registers/nfr.json",
            "capabilities": "registers/capabilities.json",
            "dependencies": "registers/dependencies.json",
            "decisions": "registers/decisions.json",
            "slo": "registers/slo.json", "dora": "registers/dora.json",
            "flow_problems": "registers/flow_problems.json",
            "themes": "registers/themes.json",
            "report": {"modes": [MODE_POOLED]},
        })

    def test_form_rebuild_alone_drops_the_fields(self) -> None:
        # Der dokumentierte Alt-Fehler: build_config_from_fields kennt die
        # Nicht-Formular-Felder nicht — ohne merge gehen sie verloren.
        built = build_config_from_fields(
            "Beta", "SAFe", "", "", [("B-1", "b1.xlsx")], MODE_POOLED)
        assert built.risks == "" and built.themes == ""
        assert built.stage_map is None

    def test_merge_restores_every_preserved_field(self) -> None:
        from portfolio.gui import _PRESERVED_FIELDS, merge_preserved_fields
        loaded = self._loaded()
        built = build_config_from_fields(
            "Beta umbenannt", "SAFe", "", "", [("B-1", "b1.xlsx")],
            MODE_POOLED)
        merged = merge_preserved_fields(built, loaded)
        for f in _PRESERVED_FIELDS:
            assert getattr(merged, f) == getattr(loaded, f), f
        # Formular-Felder bleiben die des Neuaufbaus.
        assert merged.name == "Beta umbenannt"
        assert merged.framework == "LeSS"
        assert merged.stage_map is not None
        assert merged.slo == "registers/slo.json"

    def test_merge_without_loaded_config_is_identity(self) -> None:
        from portfolio.gui import merge_preserved_fields
        built = build_config_from_fields(
            "Neu", "SAFe", "", "", [("A", "a.xlsx")], MODE_POOLED)
        assert merge_preserved_fields(built, None) is built

    def test_full_roundtrip_via_save_and_reload(self, tmp_path) -> None:
        from portfolio.gui import merge_preserved_fields
        from portfolio.solution_config import (
            load_solution_config,
            save_solution_config,
            to_dict,
        )
        loaded = self._loaded()
        rebuilt = merge_preserved_fields(build_config_from_fields(
            "Beta", "SAFe", "", "", [("B-1", "b1.xlsx")], MODE_POOLED),
            loaded)
        out = tmp_path / "roundtrip.json"
        save_solution_config(out, rebuilt)
        assert to_dict(load_solution_config(out)) == to_dict(loaded)


class TestDatenquellenDialogCore:
    """Phase 2 des Datenraum-Konzepts: die display-unabhaengigen Bausteine
    des Datenquellen-Dialogs (Fuellhelfer, Status je Feld, Relativierung
    beim Speichern)."""

    def test_fill_from_datenraum_finds_standard_names_only(
            self, tmp_path) -> None:
        from portfolio.gui import fill_from_datenraum
        reg = tmp_path / "registers"
        reg.mkdir()
        for name in ("risks", "slo", "themes"):
            (reg / f"{name}.json").write_text("{}", encoding="utf-8")
        (reg / "anderes.json").write_text("{}", encoding="utf-8")
        found = fill_from_datenraum(tmp_path)
        assert set(found) == {"risks", "slo", "themes"}
        assert found["risks"] == str((reg / "risks.json").resolve())
        # Der registers/-Ordner selbst funktioniert ebenfalls als Ziel.
        assert set(fill_from_datenraum(reg)) == {"risks", "slo", "themes"}

    def test_fill_is_explicit_not_auto_discovery(self, tmp_path) -> None:
        # Entscheidung (2): eine leere Auswahl liefert nichts — niemand
        # bekommt Register, nur weil Dateien daneben liegen.
        from portfolio.gui import fill_from_datenraum
        assert fill_from_datenraum(tmp_path) == {}

    def test_register_field_status(self, tmp_path) -> None:
        from portfolio.gui import (
            STATUS_EMPTY,
            STATUS_FOUND,
            STATUS_MISSING,
            register_field_status,
        )
        (tmp_path / "registers").mkdir()
        (tmp_path / "registers" / "risks.json").write_text(
            "{}", encoding="utf-8")
        assert register_field_status(tmp_path, "") == STATUS_EMPTY
        assert register_field_status(
            tmp_path, "registers/risks.json") == STATUS_FOUND
        assert register_field_status(
            tmp_path, "registers/fehlt.json") == STATUS_MISSING
        # Ohne base_dir zaehlt der Wert wie bisher (CWD/absolut).
        assert register_field_status(
            None, str(tmp_path / "registers" / "risks.json")) == STATUS_FOUND

    def test_relativize_rewrites_only_paths_inside_the_folder(
            self, tmp_path) -> None:
        from portfolio.gui import relativize_paths
        from portfolio.solution_config import Member, SolutionConfig
        outside = tmp_path.parent / "woanders.xlsx"
        cfg = SolutionConfig(
            name="S",
            members=[Member(name="A",
                            issue_times=str(tmp_path / "arts" / "a.xlsx"),
                            workflow=str(outside))],
            risks=str(tmp_path / "registers" / "risks.json"),
            slo="registers/slo.json")
        out = relativize_paths(cfg, tmp_path / "solution.json")
        assert out.members[0].issue_times == "arts/a.xlsx"
        assert out.members[0].workflow == str(outside)  # außerhalb: unverändert
        assert out.risks == "registers/risks.json"
        assert out.slo == "registers/slo.json"  # bereits relativ: unverändert

    def test_dialog_values_roundtrip_into_a_portable_file(
            self, tmp_path) -> None:
        # Fuellhelfer → Config → relativierend speichern → laden → aufloesen.
        import dataclasses as dc

        from portfolio.gui import fill_from_datenraum, relativize_paths
        from portfolio.solution_config import (
            Member,
            SolutionConfig,
            load_solution_config,
            resolve_config_path,
            save_solution_config,
        )
        reg = tmp_path / "registers"
        reg.mkdir()
        (reg / "risks.json").write_text("{}", encoding="utf-8")
        cfg = dc.replace(
            SolutionConfig(name="S",
                           members=[Member(name="A", issue_times="a.xlsx")]),
            **fill_from_datenraum(tmp_path))
        target = tmp_path / "solution.json"
        save_solution_config(target, relativize_paths(cfg, target))
        loaded = load_solution_config(target)
        assert loaded.risks == "registers/risks.json"
        assert resolve_config_path(loaded.base_dir, loaded.risks).is_file()
