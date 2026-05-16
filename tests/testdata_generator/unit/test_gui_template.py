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
#   testdata_generator.gui (_build_template_section / _parse_template_section).
# =============================================================================

from __future__ import annotations

from testdata_generator.gui import (
    _TEMPLATE_FIELDS,
    _build_template_section,
    _parse_template_section,
)


def test_build_section_has_all_fields_as_strings():
    sec = _build_template_section({"issues": 100, "pattern_strength": 50})
    assert set(sec) == set(_TEMPLATE_FIELDS)
    assert sec["issues"] == "100"
    assert sec["pattern_strength"] == "50"
    assert sec["workflow"] == ""


def test_parse_round_trip():
    values = {k: f"v_{k}" for k in _TEMPLATE_FIELDS}
    sec = _build_template_section(values)
    assert _parse_template_section(sec) == sec


def test_parse_missing_keys_default_to_empty():
    parsed = _parse_template_section({})
    assert all(parsed[k] == "" for k in _TEMPLATE_FIELDS)


def test_pattern_strength_field_present():
    assert "pattern_strength" in _TEMPLATE_FIELDS
