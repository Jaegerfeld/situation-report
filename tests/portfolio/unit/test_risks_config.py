# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       02.09.2026
# Geändert:       02.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für portfolio.risks_config (B3): Parsen und Validieren eines
#   ROAM-Risiko-Registers, Normalisierung der Kategorien, Fehlerfälle und
#   der Datei-Roundtrip (save_risks → load_risks).
# =============================================================================

from __future__ import annotations

from datetime import date

import pytest

from portfolio.risks_config import (
    IMPACT_MEDIUM,
    ROAM_OWNED,
    Risk,
    RiskRegister,
    load_risks,
    parse_risks,
    risks_to_dict,
    save_risks,
)


def _risk(risk_id: str = "R-1", **kwargs) -> dict:
    base = {"id": risk_id, "title": "Test risk", "roam": "owned"}
    base.update(kwargs)
    return base


class TestParseRisks:
    def test_minimal_valid_register(self) -> None:
        reg = parse_risks({"risks": [_risk()]})
        assert len(reg.risks) == 1
        risk = reg.risks[0]
        assert risk.risk_id == "R-1"
        assert risk.roam == ROAM_OWNED
        assert risk.impact == IMPACT_MEDIUM
        assert risk.status_since is None

    def test_empty_register_is_valid(self) -> None:
        assert parse_risks({"risks": []}).risks == []

    def test_full_fields_and_normalisation(self) -> None:
        reg = parse_risks({"risks": [_risk(
            roam="Mitigated", impact="HIGH", owner="  System Team ",
            status_since="2025-05-01", notes=" note ")]})
        risk = reg.risks[0]
        assert risk.roam == "mitigated"
        assert risk.impact == "high"
        assert risk.owner == "System Team"
        assert risk.status_since == date(2025, 5, 1)
        assert risk.notes == "note"

    def test_rejects_non_object(self) -> None:
        with pytest.raises(ValueError, match="JSON object"):
            parse_risks([])

    def test_rejects_missing_risks_list(self) -> None:
        with pytest.raises(ValueError, match="'risks' list"):
            parse_risks({"risks": "nope"})

    def test_rejects_empty_id_and_title(self) -> None:
        with pytest.raises(ValueError, match="'id'"):
            parse_risks({"risks": [_risk(risk_id=" ")]})
        with pytest.raises(ValueError, match="'title'"):
            parse_risks({"risks": [_risk(title=" ")]})

    def test_rejects_duplicate_id(self) -> None:
        with pytest.raises(ValueError, match="Duplicate risk id"):
            parse_risks({"risks": [_risk(), _risk()]})

    def test_rejects_unknown_roam_and_impact(self) -> None:
        with pytest.raises(ValueError, match="ROAM category"):
            parse_risks({"risks": [_risk(roam="parked")]})
        with pytest.raises(ValueError, match="impact"):
            parse_risks({"risks": [_risk(impact="huge")]})

    def test_rejects_bad_date(self) -> None:
        with pytest.raises(ValueError, match="status_since"):
            parse_risks({"risks": [_risk(status_since="01.05.2025")]})


class TestRoundtrip:
    def test_save_and_load_roundtrip(self, tmp_path) -> None:
        register = RiskRegister(risks=[
            Risk("R-1", "First", "owned", owner="Team A", impact="high",
                 status_since=date(2025, 4, 1), notes="hot"),
            Risk("R-2", "Second", "resolved"),
        ])
        path = tmp_path / "risks.json"
        save_risks(path, register)
        assert load_risks(path) == register

    def test_to_dict_omits_empty_optionals(self) -> None:
        data = risks_to_dict(RiskRegister(risks=[Risk("R-1", "T", "accepted")]))
        entry = data["risks"][0]
        assert "owner" not in entry
        assert "status_since" not in entry
        assert "notes" not in entry
        assert data["schema"] == 1
