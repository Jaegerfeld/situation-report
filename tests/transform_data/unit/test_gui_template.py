# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       16.05.2026
# Geändert:       16.05.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für die Projekt-Template-Abschnittsfunktionen von
#   transform_data.gui (_build_template_section / _parse_template_section).
# =============================================================================

from __future__ import annotations

from transform_data.gui import _build_template_section, _parse_template_section


def test_build_section_contains_all_fields():
    sec = _build_template_section("a.json", "wf.txt", "/out", "ART_A")
    assert sec == {
        "json_file": "a.json",
        "workflow_file": "wf.txt",
        "output_dir": "/out",
        "prefix": "ART_A",
    }


def test_parse_round_trip():
    sec = _build_template_section("a.json", "wf.txt", "/out", "ART_A")
    assert _parse_template_section(sec) == sec


def test_parse_missing_keys_default_to_empty():
    assert _parse_template_section({}) == {
        "json_file": "",
        "workflow_file": "",
        "output_dir": "",
        "prefix": "",
    }
