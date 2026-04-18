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
    """Tests for the term() function — metric display name lookup by mode."""

    def test_safe_flow_time(self):
        """Flow Time metric maps to 'Flow Time' in SAFe mode."""
        assert term(FLOW_TIME, SAFE) == "Flow Time"

    def test_global_flow_time(self):
        """Flow Time metric maps to 'Cycle Time' in Global mode."""
        assert term(FLOW_TIME, GLOBAL) == "Cycle Time"

    def test_safe_flow_velocity(self):
        """Flow Velocity metric maps to 'Flow Velocity' in SAFe mode."""
        assert term(FLOW_VELOCITY, SAFE) == "Flow Velocity"

    def test_global_flow_velocity(self):
        """Flow Velocity metric maps to 'Throughput' in Global mode."""
        assert term(FLOW_VELOCITY, GLOBAL) == "Throughput"

    def test_safe_flow_load(self):
        """Flow Load metric maps to 'Flow Load' in SAFe mode."""
        assert term(FLOW_LOAD, SAFE) == "Flow Load"

    def test_global_flow_load(self):
        """Flow Load metric maps to 'WIP' in Global mode."""
        assert term(FLOW_LOAD, GLOBAL) == "WIP"

    def test_flow_distribution_same_in_both_modes(self):
        """Flow Distribution label is identical in SAFe and Global modes."""
        assert term(FLOW_DISTRIBUTION, SAFE) == term(FLOW_DISTRIBUTION, GLOBAL)

    def test_unknown_metric_id_raises(self):
        """Passing an unregistered metric ID raises KeyError."""
        with pytest.raises(KeyError):
            term("does_not_exist", SAFE)

    def test_unknown_mode_raises(self):
        """Passing an unrecognised terminology mode raises KeyError."""
        with pytest.raises(KeyError):
            term(FLOW_TIME, "Unknown")

    def test_default_mode_is_safe(self):
        """term() without an explicit mode argument defaults to SAFe mode."""
        assert term(FLOW_TIME) == term(FLOW_TIME, SAFE)


class TestAllTerms:
    """Tests for the all_terms() function — full mode-to-names mapping."""

    def test_returns_dict(self):
        """all_terms() returns a dict for the given mode."""
        result = all_terms(SAFE)
        assert isinstance(result, dict)

    def test_safe_contains_all_ids(self):
        """SAFe mode dict contains all core metric IDs."""
        result = all_terms(SAFE)
        assert FLOW_TIME in result
        assert FLOW_VELOCITY in result
        assert FLOW_LOAD in result
        assert FLOW_DISTRIBUTION in result

    def test_global_differs_from_safe(self):
        """Global mode uses different labels than SAFe for renamed metrics."""
        safe = all_terms(SAFE)
        global_ = all_terms(GLOBAL)
        assert safe[FLOW_TIME] != global_[FLOW_TIME]
        assert safe[FLOW_VELOCITY] != global_[FLOW_VELOCITY]

    def test_returns_copy(self):
        """Mutating the returned dict does not affect the terminology module state."""
        result = all_terms(SAFE)
        result[FLOW_TIME] = "MODIFIED"
        assert term(FLOW_TIME, SAFE) == "Flow Time"
