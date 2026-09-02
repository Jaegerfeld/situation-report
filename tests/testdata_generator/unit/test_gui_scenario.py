# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       02.09.2026
# Geändert:       02.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für den Demo-Portfolio-Pfad der testdata_generator-GUI:
#   _build_portfolio_report_html_file (Szenario-Config → Portfolio-Report →
#   Temp-HTML; Rendering gemockt und einmal echt) und die Vollständigkeit
#   der neuen Übersetzungs-Keys (de/en-Parität). Kein tkinter-Fenster nötig.
# =============================================================================

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from testdata_generator.gui import _T, _build_portfolio_report_html_file


def test_portfolio_chain_writes_html_file(tmp_path: Path) -> None:
    portfolio_json = tmp_path / "portfolio.json"
    portfolio_json.write_text("{}", encoding="utf-8")

    with patch("portfolio.solution_config.load_solution_config",
               return_value="cfg") as m_load, \
         patch("portfolio.aggregator.render_html",
               return_value="<!DOCTYPE html><html></html>") as m_render:
        out = _build_portfolio_report_html_file(
            portfolio_json, log=lambda _: None)

    assert out.endswith(".html")
    assert Path(out).read_text(encoding="utf-8").startswith("<!DOCTYPE html>")
    m_load.assert_called_once_with(portfolio_json)
    assert m_render.call_args.args[0] == "cfg"
    Path(out).unlink()


def test_portfolio_chain_returns_empty_when_no_figures(tmp_path: Path) -> None:
    portfolio_json = tmp_path / "portfolio.json"
    portfolio_json.write_text("{}", encoding="utf-8")

    with patch("portfolio.solution_config.load_solution_config",
               return_value="cfg"), \
         patch("portfolio.aggregator.render_html", return_value=""):
        out = _build_portfolio_report_html_file(
            portfolio_json, log=lambda _: None)

    assert out == ""


def test_portfolio_chain_end_to_end_with_real_scenario(tmp_path: Path) -> None:
    """The real chain: scenario -> portfolio report -> temp HTML file."""
    from datetime import date

    from testdata_generator.scenario import build_portfolio_scenario

    paths = build_portfolio_scenario(
        tmp_path, seed=42, reference=date(2025, 6, 30), log=lambda _: None)
    out = _build_portfolio_report_html_file(
        paths["portfolio"], log=lambda _: None)

    assert out.endswith(".html")
    html = Path(out).read_text(encoding="utf-8")
    assert "Data Quality per Source" in html
    assert "ROAM Risk Board" in html
    Path(out).unlink()


def test_scenario_translation_keys_exist_in_de_and_en() -> None:
    keys = ("lbl_scenario", "btn_scenario", "btn_scenario_report",
            "dlg_scenario_dir", "log_scenario_started", "log_scenario_done",
            "log_scenario_hint", "log_scenario_error")
    for lang in ("de", "en"):
        for key in keys:
            assert key in _T[lang], f"{key} missing in {lang}"
    # Platzhalter-Konsistenz: die formatierten Meldungen tragen genau ein {}.
    for lang in ("de", "en"):
        assert _T[lang]["log_scenario_done"].count("{}") == 1
        assert _T[lang]["log_scenario_error"].count("{}") == 1
