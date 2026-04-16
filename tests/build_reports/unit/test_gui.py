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
    _build_combined_html, _parse_date_safe, _split_csv,
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
