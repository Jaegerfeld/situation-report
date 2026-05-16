# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       16.05.2026
# Geändert:       16.05.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für die Projekt-Template-Abschnittsfunktionen von helper.gui
#   (_build_template_section / _parse_template_section).
# =============================================================================

from __future__ import annotations

from helper.gui import _build_template_section, _parse_template_section


def test_build_section():
    sec = _build_template_section(["a.json", "b.json"], "merged.json", False)
    assert sec == {
        "inputs": ["a.json", "b.json"],
        "output": "merged.json",
        "dedup": False,
    }


def test_parse_round_trip():
    sec = _build_template_section(["x.json"], "out.json", True)
    assert _parse_template_section(sec) == sec


def test_parse_defaults():
    assert _parse_template_section({}) == {
        "inputs": [],
        "output": "",
        "dedup": True,
    }


def test_parse_non_list_inputs_coerced_to_empty():
    assert _parse_template_section({"inputs": "not-a-list"})["inputs"] == []
