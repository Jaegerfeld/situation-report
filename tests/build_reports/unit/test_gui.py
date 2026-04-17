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
    _build_combined_html, _build_template_dict, _check_stage_consistency,
    _default_date_range, _parse_date_safe, _parse_template_dict,
    _read_available_filters, _split_csv, _TEMPLATE_VERSION,
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

    def test_section_break_heading_inserted(self):
        figs = [go.Figure(), go.Figure()]
        html = _build_combined_html(figs, section_breaks={0: "Flow Time"})
        assert "Flow Time" in html
        assert "metric-heading" in html

    def test_section_break_only_at_correct_index(self):
        figs = [go.Figure(), go.Figure()]
        html = _build_combined_html(figs, section_breaks={1: "Throughput"})
        # Heading must appear before the second figure block
        idx_heading = html.index("Throughput")
        # At least one plotly div precedes the heading
        idx_first_div = html.index("plotly-graph-div")
        assert idx_first_div < idx_heading

    def test_no_section_breaks_produces_no_h2(self):
        fig = go.Figure()
        html = _build_combined_html([fig], section_breaks=None)
        assert "<h2" not in html


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


class TestDefaultDateRange:
    def test_returns_tuple_of_two_dates(self):
        from_d, to_d = _default_date_range()
        assert isinstance(from_d, date)
        assert isinstance(to_d, date)

    def test_to_is_today(self):
        _, to_d = _default_date_range()
        assert to_d == date.today()

    def test_from_is_365_days_before_today(self):
        from datetime import timedelta
        from_d, _ = _default_date_range()
        assert from_d == date.today() - timedelta(days=365)

    def test_from_before_to(self):
        from_d, to_d = _default_date_range()
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
            assert "btn_last_365" in _T[lang]

    def test_filter_picker_keys_present(self):
        for lang in (LANG_DE, LANG_EN):
            assert "dlg_projects" in _T[lang]
            assert "dlg_issuetypes" in _T[lang]
            assert "btn_pick" in _T[lang]

    def test_template_keys_present(self):
        for lang in (LANG_DE, LANG_EN):
            assert "menu_template" in _T[lang]
            assert "menu_tpl_save" in _T[lang]
            assert "menu_tpl_load" in _T[lang]
            assert "log_tpl_saved" in _T[lang]
            assert "log_tpl_loaded" in _T[lang]
            assert "log_tpl_error" in _T[lang]

    def test_tooltip_keys_present(self):
        required = [
            "tip_issue_times", "tip_cfd", "tip_pi_config", "tip_browse",
            "tip_from", "tip_to", "tip_cal", "tip_last_365",
            "tip_projects", "tip_issuetypes", "tip_pick",
            "tip_ct_a", "tip_ct_b", "tip_show", "tip_pdf",
        ]
        for lang in (LANG_DE, LANG_EN):
            for key in required:
                assert key in _T[lang], f"Missing tooltip key [{lang}][{key}]"

    def test_metric_tooltip_keys_present(self):
        from build_reports.metrics import all_metrics
        for plugin in all_metrics():
            tip_key = f"tip_metric_{plugin.metric_id}"
            # Only check keys that are defined (not all metrics need one)
            if tip_key in _T[LANG_DE]:
                assert tip_key in _T[LANG_EN], (
                    f"Tooltip key {tip_key} present in DE but missing in EN"
                )


# ---------------------------------------------------------------------------
# Helper for template tests
# ---------------------------------------------------------------------------

def _sample_template(**overrides) -> dict:
    """Return a minimal valid template dict, with optional field overrides."""
    base = dict(
        issue_times="/data/it.xlsx",
        cfd="/data/cfd.xlsx",
        pi_config="",
        from_date="2024-01-01",
        to_date="2024-12-31",
        projects="ARTA, ARTB",
        issuetypes="Feature",
        terminology="safe",
        ct_method="A",
        metrics={"flow_time": True, "throughput": False},
        language="de",
    )
    base.update(overrides)
    return base


class TestBuildTemplateDict:
    def test_contains_version(self):
        tpl = _build_template_dict(**_sample_template())
        assert "version" in tpl
        assert isinstance(tpl["version"], int)

    def test_roundtrip_fields(self):
        state = _sample_template()
        tpl = _build_template_dict(**state)
        for key in ("issue_times", "cfd", "pi_config", "from_date", "to_date",
                    "projects", "issuetypes", "terminology", "ct_method", "language"):
            assert tpl[key] == state[key]

    def test_metrics_preserved(self):
        metrics = {"flow_time": True, "throughput": False}
        tpl = _build_template_dict(**_sample_template(metrics=metrics))
        assert tpl["metrics"] == metrics

    def test_empty_paths_allowed(self):
        tpl = _build_template_dict(**_sample_template(issue_times="", cfd=""))
        assert tpl["issue_times"] == ""
        assert tpl["cfd"] == ""


class TestParseTemplateDict:
    def test_valid_roundtrip(self):
        state = _sample_template()
        tpl = _build_template_dict(**state)
        parsed = _parse_template_dict(tpl)
        for key in ("issue_times", "cfd", "pi_config", "from_date", "to_date",
                    "projects", "issuetypes", "terminology", "ct_method", "language"):
            assert parsed[key] == state[key]

    def test_missing_keys_get_defaults(self):
        parsed = _parse_template_dict({"version": 1})
        assert parsed["issue_times"] == ""
        assert parsed["cfd"] == ""
        assert parsed["pi_config"] == ""
        assert parsed["from_date"] == ""
        assert parsed["to_date"] == ""
        assert isinstance(parsed["metrics"], dict)

    def test_non_dict_raises_value_error(self):
        with pytest.raises(ValueError):
            _parse_template_dict([1, 2, 3])

    def test_future_version_raises_value_error(self):
        with pytest.raises(ValueError, match="version"):
            _parse_template_dict({"version": 9999})

    def test_metrics_is_dict(self):
        parsed = _parse_template_dict({"version": 1, "metrics": {"flow_time": True}})
        assert parsed["metrics"] == {"flow_time": True}

    def test_json_serialisable(self):
        import json
        state = _sample_template()
        tpl = _build_template_dict(**state)
        # Must not raise
        json.dumps(tpl)
