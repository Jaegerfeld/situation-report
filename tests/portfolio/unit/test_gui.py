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

import pytest

from portfolio.gui import (
    LANG_DE,
    LANG_EN,
    LANG_FR,
    LANG_PT,
    LANG_RO,
    _T,
    _member_dict,
    build_config_from_fields,
    default_metrics_for_mode,
)
from portfolio.solution_config import MODE_COMPARISON, MODE_POOLED

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

    def test_no_members_raises(self) -> None:
        with pytest.raises(ValueError):
            build_config_from_fields("X", "SAFe", "", "", [("", "")], MODE_POOLED)


class TestDefaultMetricsForMode:
    def test_pooled_excludes_flow_load(self) -> None:
        assert "flow_load" not in default_metrics_for_mode(MODE_POOLED)

    def test_comparison_includes_flow_load(self) -> None:
        assert "flow_load" in default_metrics_for_mode(MODE_COMPARISON)
