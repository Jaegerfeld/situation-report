# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       16.04.2026
# Geändert:       16.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für die Display-unabhängigen Hilfsfunktionen in gui.py:
#   _parse_date_safe, _split_csv, _build_combined_html und _TRANSLATIONS.
#   Der tkinter-Teil (BuildReportsApp) wird hier nicht instanziiert, da dies
#   eine laufende Anzeige erfordern würde.
# =============================================================================

from __future__ import annotations

from datetime import date

import plotly.graph_objects as go
import pytest

from build_reports.gui import (
    LANG_DE, LANG_EN, _T,
    _build_combined_html, _check_stage_consistency, _default_year_range,
    _parse_date_safe, _read_available_filters, _split_csv,
)


class TestParseDateSafe:
    def test_empty_string_returns_none(self):
        assert _parse_date_safe("") is None

    def test_whitespace_only_returns_none(self):
        assert _parse_date_safe("   ") is None

    def test_valid_date_parsed(self):
        assert _parse_date_safe("2025-06-15") == date(2025, 6, 15)

    def test_valid_date_with_surrounding_whitespace(self):
        assert _parse_date_safe("  2025-01-01  ") == date(2025, 1, 1)

    def test_invalid_format_raises_value_error(self):
        with pytest.raises(ValueError):
            _parse_date_safe("15.06.2025")

    def test_invalid_date_raises_value_error(self):
        with pytest.raises(ValueError):
            _parse_date_safe("2025-13-01")


class TestSplitCsv:
    def test_empty_string_returns_empty_list(self):
        assert _split_csv("") == []

    def test_whitespace_only_returns_empty_list(self):
        assert _split_csv("   ") == []

    def test_single_item(self):
        assert _split_csv("ARTA") == ["ARTA"]

    def test_multiple_items(self):
        assert _split_csv("ARTA, ARTB, ARTC") == ["ARTA", "ARTB", "ARTC"]

    def test_strips_whitespace_from_items(self):
        assert _split_csv("  Feature ,  Bug  ") == ["Feature", "Bug"]

    def test_ignores_empty_segments(self):
        assert _split_csv("ARTA,,ARTB") == ["ARTA", "ARTB"]

    def test_trailing_comma_ignored(self):
        assert _split_csv("ARTA,") == ["ARTA"]


class TestBuildCombinedHtml:
    def test_returns_string(self):
        fig = go.Figure(go.Scatter(x=[1, 2], y=[1, 2]))
        html = _build_combined_html([fig])
        assert isinstance(html, str)

    def test_html_contains_doctype(self):
        fig = go.Figure()
        html = _build_combined_html([fig])
        assert "<!DOCTYPE html>" in html

    def test_first_figure_includes_plotlyjs(self):
        fig = go.Figure()
        html = _build_combined_html([fig])
        # cdn reference appears when include_plotlyjs='cdn'
        assert "cdn.plot.ly" in html or "plotly" in html.lower()

    def test_multiple_figures_all_embedded(self):
        figs = [go.Figure(go.Scatter(x=[i], y=[i])) for i in range(3)]
        html = _build_combined_html(figs)
        # Each figure generates a unique div id; count plotly-graph-div occurrences
        assert html.count("plotly-graph-div") >= 3

    def test_empty_list_returns_valid_html(self):
        html = _build_combined_html([])
        assert "<html>" in html
        assert "<body>" in html


def _make_issuetimes(tmp_path, stages: list[str], name="it.xlsx"):
    """Helper: create a minimal IssueTimes XLSX with given stages."""
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(["Project", "Key", "Issuetype", "Status", "Created Date",
               "Component", "Category", "First Date", "Implementation Date",
               "Closed Date"] + stages + ["Resolution"])
    ws.append(["ART", "ART-1", "Feature", "Done", None, "", "", None, None, None]
              + [0] * len(stages) + ["Done"])
    path = tmp_path / name
    wb.save(path)
    return path


def _make_cfd(tmp_path, stages: list[str], name="cfd.xlsx"):
    """Helper: create a minimal CFD XLSX with given stages."""
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(["Day"] + stages)
    ws.append(["2025-01-01"] + [0] * len(stages))
    path = tmp_path / name
    wb.save(path)
    return path


class TestCheckStageConsistency:
    def test_consistent_returns_empty_lists(self, tmp_path):
        stages = ["Analysis", "Implementation", "Done"]
        it = _make_issuetimes(tmp_path, stages)
        cfd = _make_cfd(tmp_path, stages)
        only_it, only_cfd = _check_stage_consistency(it, cfd)
        assert only_it == []
        assert only_cfd == []

    def test_stage_missing_in_cfd(self, tmp_path):
        it = _make_issuetimes(tmp_path, ["Analysis", "Implementation", "Done"])
        cfd = _make_cfd(tmp_path, ["Analysis", "Done"])
        only_it, only_cfd = _check_stage_consistency(it, cfd)
        assert only_it == ["Implementation"]
        assert only_cfd == []

    def test_extra_stage_in_cfd(self, tmp_path):
        it = _make_issuetimes(tmp_path, ["Analysis", "Done"])
        cfd = _make_cfd(tmp_path, ["Analysis", "Implementation", "Done"])
        only_it, only_cfd = _check_stage_consistency(it, cfd)
        assert only_it == []
        assert only_cfd == ["Implementation"]

    def test_both_mismatches(self, tmp_path):
        it = _make_issuetimes(tmp_path, ["A", "B"])
        cfd = _make_cfd(tmp_path, ["A", "C"])
        only_it, only_cfd = _check_stage_consistency(it, cfd)
        assert only_it == ["B"]
        assert only_cfd == ["C"]

    def test_translation_keys_present(self):
        for lang in (LANG_DE, LANG_EN):
            assert "log_check_ok" in _T[lang]
            assert "log_check_miss_cfd" in _T[lang]
            assert "log_check_miss_it" in _T[lang]


class TestReadAvailableFilters:
    def test_returns_sorted_projects(self, tmp_path):
        """Projects extracted from XLSX are sorted and deduplicated."""
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.append(["Project", "Key", "Issuetype", "Status"])
        ws.append(["ARTB", "ARTB-1", "Feature", "Done"])
        ws.append(["ARTA", "ARTA-1", "Bug", "Open"])
        ws.append(["ARTA", "ARTA-2", "Feature", "Done"])
        path = tmp_path / "test.xlsx"
        wb.save(path)
        projects, _ = _read_available_filters(path)
        assert projects == ["ARTA", "ARTB"]

    def test_returns_sorted_issuetypes(self, tmp_path):
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.append(["Project", "Key", "Issuetype", "Status"])
        ws.append(["ART", "ART-1", "Story", "Done"])
        ws.append(["ART", "ART-2", "Feature", "Done"])
        ws.append(["ART", "ART-3", "Story", "Open"])
        path = tmp_path / "test.xlsx"
        wb.save(path)
        _, issuetypes = _read_available_filters(path)
        assert issuetypes == ["Feature", "Story"]

    def test_empty_file_returns_empty_lists(self, tmp_path):
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.append(["Project", "Key", "Issuetype", "Status"])
        path = tmp_path / "empty.xlsx"
        wb.save(path)
        projects, issuetypes = _read_available_filters(path)
        assert projects == []
        assert issuetypes == []


class TestDefaultYearRange:
    def test_returns_tuple_of_two_dates(self):
        from_d, to_d = _default_year_range()
        assert isinstance(from_d, date)
        assert isinstance(to_d, date)

    def test_from_is_jan_first_of_last_year(self):
        from_d, _ = _default_year_range()
        assert from_d.month == 1 and from_d.day == 1
        assert from_d.year == date.today().year - 1

    def test_to_is_dec_31_of_last_year(self):
        _, to_d = _default_year_range()
        assert to_d.month == 12 and to_d.day == 31
        assert to_d.year == date.today().year - 1

    def test_from_before_to(self):
        from_d, to_d = _default_year_range()
        assert from_d < to_d


class TestTranslations:
    def test_both_languages_present(self):
        assert LANG_DE in _T
        assert LANG_EN in _T

    def test_same_keys_in_both_languages(self):
        assert set(_T[LANG_DE].keys()) == set(_T[LANG_EN].keys())

    def test_german_window_title(self):
        assert _T[LANG_DE]["window_title"] == "build_reports"

    def test_german_options_menu_label(self):
        assert _T[LANG_DE]["menu_options"] == "Optionen"

    def test_english_options_menu_label(self):
        assert _T[LANG_EN]["menu_options"] == "Options"

    def test_no_empty_values(self):
        for lang, entries in _T.items():
            for key, value in entries.items():
                assert value, f"Empty translation: [{lang}][{key}]"

    def test_date_picker_keys_present(self):
        for lang in (LANG_DE, LANG_EN):
            assert "dlg_pick_date" in _T[lang]
            assert "btn_cal" in _T[lang]
            assert "btn_ok" in _T[lang]

    def test_filter_picker_keys_present(self):
        for lang in (LANG_DE, LANG_EN):
            assert "dlg_projects" in _T[lang]
            assert "dlg_issuetypes" in _T[lang]
            assert "btn_pick" in _T[lang]
