# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       02.07.2026
# Geändert:       02.07.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für die Projekt-Template-Abschnittsfunktionen von
#   simulate.gui (_build_template_section / _parse_template_section) sowie die
#   Registrierung von MODULE_SIMULATE im gemeinsamen project_template.
# =============================================================================

from __future__ import annotations

import project_template
from simulate.gui import (
    _TEMPLATE_FIELDS,
    _build_template_section,
    _parse_template_section,
)


def test_build_section_has_all_fields_as_strings():
    sec = _build_template_section({"runs": 25000, "history_days": 180})
    assert set(sec) == set(_TEMPLATE_FIELDS)
    assert sec["runs"] == "25000"
    assert sec["history_days"] == "180"
    assert sec["issue_times"] == ""


def test_parse_round_trip():
    values = {k: f"v_{k}" for k in _TEMPLATE_FIELDS}
    sec = _build_template_section(values)
    assert _parse_template_section(sec) == sec


def test_parse_missing_keys_default_to_empty():
    parsed = _parse_template_section({})
    assert all(parsed[k] == "" for k in _TEMPLATE_FIELDS)


def test_expected_fields_present():
    assert "issue_times" in _TEMPLATE_FIELDS
    assert "cfd" in _TEMPLATE_FIELDS
    assert "seed" in _TEMPLATE_FIELDS


def test_module_simulate_registered():
    assert project_template.MODULE_SIMULATE == "simulate"
