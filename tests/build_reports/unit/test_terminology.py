# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       15.04.2026
# Geändert:       15.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für terminology.py. Prüft Namens-Mapping in beiden Modi,
#   Fehlerverhalten bei unbekannten IDs/Modi und Vollständigkeit der Einträge.
# =============================================================================

import pytest

from build_reports.terminology import (
    FLOW_DISTRIBUTION, FLOW_LOAD, FLOW_TIME, FLOW_VELOCITY,
    GLOBAL, SAFE, all_terms, term,
)


class TestTerm:
    def test_safe_flow_time(self):
        assert term(FLOW_TIME, SAFE) == "Flow Time"

    def test_global_flow_time(self):
        assert term(FLOW_TIME, GLOBAL) == "Cycle Time"

    def test_safe_flow_velocity(self):
        assert term(FLOW_VELOCITY, SAFE) == "Flow Velocity"

    def test_global_flow_velocity(self):
        assert term(FLOW_VELOCITY, GLOBAL) == "Throughput"

    def test_safe_flow_load(self):
        assert term(FLOW_LOAD, SAFE) == "Flow Load"

    def test_global_flow_load(self):
        assert term(FLOW_LOAD, GLOBAL) == "WIP"

    def test_flow_distribution_same_in_both_modes(self):
        assert term(FLOW_DISTRIBUTION, SAFE) == term(FLOW_DISTRIBUTION, GLOBAL)

    def test_unknown_metric_id_raises(self):
        with pytest.raises(KeyError):
            term("does_not_exist", SAFE)

    def test_unknown_mode_raises(self):
        with pytest.raises(KeyError):
            term(FLOW_TIME, "Unknown")

    def test_default_mode_is_safe(self):
        assert term(FLOW_TIME) == term(FLOW_TIME, SAFE)


class TestAllTerms:
    def test_returns_dict(self):
        result = all_terms(SAFE)
        assert isinstance(result, dict)

    def test_safe_contains_all_ids(self):
        result = all_terms(SAFE)
        assert FLOW_TIME in result
        assert FLOW_VELOCITY in result
        assert FLOW_LOAD in result
        assert FLOW_DISTRIBUTION in result

    def test_global_differs_from_safe(self):
        safe = all_terms(SAFE)
        global_ = all_terms(GLOBAL)
        assert safe[FLOW_TIME] != global_[FLOW_TIME]
        assert safe[FLOW_VELOCITY] != global_[FLOW_VELOCITY]

    def test_returns_copy(self):
        # Mutating the returned dict should not affect the module
        result = all_terms(SAFE)
        result[FLOW_TIME] = "MODIFIED"
        assert term(FLOW_TIME, SAFE) == "Flow Time"
