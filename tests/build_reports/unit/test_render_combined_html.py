# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       17.05.2026
# Geändert:       17.05.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für build_reports.cli.render_combined_html: erzeugt aus den
#   ART_A-Fixtures eine einzelne kombinierte HTML-Seite und liefert bei
#   fehlenden Figures einen leeren String.
# =============================================================================

from __future__ import annotations

from pathlib import Path

from build_reports.cli import render_combined_html

_ART_A = Path(__file__).parents[2] / "testdata" / "ART_A"


def _silent(_: str) -> None:
    pass


def test_returns_single_combined_html_page():
    html = render_combined_html(
        issue_times=_ART_A / "ART_A_IssueTimes.xlsx",
        cfd=_ART_A / "ART_A_CFD.xlsx",
        workflow=_ART_A / "workflow_ART_A.txt",
        transitions=_ART_A / "ART_A_Transitions.xlsx",
        from_date=None,
        to_date=None,
        log=_silent,
    )
    assert html.startswith("<!DOCTYPE html>")
    assert "plotly-graph-div" in html
    assert 'class="metric-heading"' in html
    # CDN bundle exactly once (only the first figure embeds plotly.js)
    assert html.count("cdn.plot.ly") <= 2


def test_unknown_metric_only_yields_empty_string():
    html = render_combined_html(
        issue_times=_ART_A / "ART_A_IssueTimes.xlsx",
        cfd=_ART_A / "ART_A_CFD.xlsx",
        workflow=_ART_A / "workflow_ART_A.txt",
        transitions=_ART_A / "ART_A_Transitions.xlsx",
        metrics=["does_not_exist"],
        log=_silent,
    )
    assert html == ""
