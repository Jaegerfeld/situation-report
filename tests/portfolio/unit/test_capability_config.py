# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       02.09.2026
# Geändert:       02.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für portfolio.capability_config (B1): Parsen und Validieren
#   einer Capability-Map, Normalisierung der Health-Werte und ART-Listen,
#   Fehlerfälle und der Datei-Roundtrip (save_capabilities →
#   load_capabilities).
# =============================================================================

from __future__ import annotations

from datetime import date

import pytest

from portfolio.capability_config import (
    HEALTH_CRITICAL,
    Capability,
    CapabilityMap,
    capabilities_to_dict,
    load_capabilities,
    parse_capabilities,
    save_capabilities,
)


def _cap(cap_id: str = "C-1", **kwargs) -> dict:
    base = {"id": cap_id, "title": "Test capability", "health": "healthy"}
    base.update(kwargs)
    return base


class TestParseCapabilities:
    def test_minimal_valid_map(self) -> None:
        cap_map = parse_capabilities({"capabilities": [_cap()]})
        cap = cap_map.capabilities[0]
        assert cap.cap_id == "C-1"
        assert cap.health == "healthy"
        assert cap.arts == []
        assert cap.assessed_on is None

    def test_empty_map_is_valid(self) -> None:
        assert parse_capabilities({"capabilities": []}) == CapabilityMap()

    def test_normalisation_and_full_fields(self) -> None:
        cap_map = parse_capabilities({"capabilities": [_cap(
            health="CRITICAL", arts=[" ART A ", "", "ART B"],
            owner=" Team ", assessed_on="2025-06-01", notes=" n ")]})
        cap = cap_map.capabilities[0]
        assert cap.health == HEALTH_CRITICAL
        assert cap.arts == ["ART A", "ART B"]
        assert cap.owner == "Team"
        assert cap.assessed_on == date(2025, 6, 1)
        assert cap.notes == "n"

    def test_rejects_non_object_and_missing_list(self) -> None:
        with pytest.raises(ValueError, match="JSON object"):
            parse_capabilities([])
        with pytest.raises(ValueError, match="'capabilities' list"):
            parse_capabilities({"capabilities": "x"})

    def test_rejects_empty_id_and_title(self) -> None:
        with pytest.raises(ValueError, match="'id'"):
            parse_capabilities({"capabilities": [_cap(cap_id=" ")]})
        with pytest.raises(ValueError, match="'title'"):
            parse_capabilities({"capabilities": [_cap(title="")]})

    def test_rejects_duplicate_id(self) -> None:
        with pytest.raises(ValueError, match="Duplicate capability id"):
            parse_capabilities({"capabilities": [_cap(), _cap()]})

    def test_rejects_unknown_health_and_bad_arts(self) -> None:
        with pytest.raises(ValueError, match="unknown health"):
            parse_capabilities({"capabilities": [_cap(health="broken")]})
        with pytest.raises(ValueError, match="'arts' must be a list"):
            parse_capabilities({"capabilities": [_cap(arts="ART A")]})

    def test_rejects_bad_assessed_on(self) -> None:
        with pytest.raises(ValueError, match="assessed_on"):
            parse_capabilities({"capabilities": [_cap(assessed_on="01.06.2025")]})


class TestRoundtrip:
    def test_save_and_load_roundtrip(self, tmp_path) -> None:
        cap_map = CapabilityMap(capabilities=[
            Capability("C-1", "First", "critical", arts=["ART A"],
                       owner="Team A", assessed_on=date(2025, 6, 1), notes="x"),
            Capability("C-2", "Second", "healthy"),
        ])
        path = tmp_path / "capabilities.json"
        save_capabilities(path, cap_map)
        assert load_capabilities(path) == cap_map

    def test_to_dict_omits_empty_optionals(self) -> None:
        data = capabilities_to_dict(CapabilityMap(
            capabilities=[Capability("C-1", "T", "healthy")]))
        entry = data["capabilities"][0]
        assert "arts" not in entry
        assert "owner" not in entry
        assert "assessed_on" not in entry
        assert "notes" not in entry
        assert data["schema"] == 1
