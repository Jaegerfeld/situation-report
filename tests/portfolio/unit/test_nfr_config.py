# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       02.09.2026
# Geändert:       02.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für portfolio.nfr_config (B2): Parsen und Validieren eines
#   NFR-/Runway-Registers, Normalisierung der Status-Werte, Fehlerfälle und
#   der Datei-Roundtrip (save_nfr → load_nfr).
# =============================================================================

from __future__ import annotations

from datetime import date

import pytest

from portfolio.nfr_config import (
    STATUS_VIOLATED,
    Nfr,
    NfrRegister,
    RunwayItem,
    load_nfr,
    nfr_to_dict,
    parse_nfr,
    save_nfr,
)


def _nfr(nfr_id: str = "N-1", **kwargs) -> dict:
    base = {"id": nfr_id, "title": "Test NFR", "target": "x < 1", "status": "met"}
    base.update(kwargs)
    return base


def _item(item_id: str = "RW-1", **kwargs) -> dict:
    base = {"id": item_id, "title": "Test element", "status": "building"}
    base.update(kwargs)
    return base


class TestParseNfr:
    def test_minimal_valid_register(self) -> None:
        reg = parse_nfr({"nfrs": [_nfr()], "runway": [_item()]})
        assert reg.nfrs[0].nfr_id == "N-1"
        assert reg.nfrs[0].status == "met"
        assert reg.runway[0].status == "building"
        assert reg.runway[0].needed_by is None

    def test_both_blocks_optional_and_empty_valid(self) -> None:
        assert parse_nfr({}) == NfrRegister()
        assert parse_nfr({"nfrs": [], "runway": []}) == NfrRegister()

    def test_normalisation_and_full_fields(self) -> None:
        reg = parse_nfr({
            "nfrs": [_nfr(status="VIOLATED", actual=" 340 ms ", owner=" Team ")],
            "runway": [_item(status="Gap", needed_by="2025-05-01", notes=" n ")]})
        assert reg.nfrs[0].status == STATUS_VIOLATED
        assert reg.nfrs[0].actual == "340 ms"
        assert reg.nfrs[0].owner == "Team"
        assert reg.runway[0].status == "gap"
        assert reg.runway[0].needed_by == date(2025, 5, 1)
        assert reg.runway[0].notes == "n"

    def test_rejects_non_object_and_non_lists(self) -> None:
        with pytest.raises(ValueError, match="JSON object"):
            parse_nfr([])
        with pytest.raises(ValueError, match="'nfrs' must be a list"):
            parse_nfr({"nfrs": "x"})
        with pytest.raises(ValueError, match="'runway' must be a list"):
            parse_nfr({"runway": "x"})

    def test_rejects_missing_id_title_target(self) -> None:
        with pytest.raises(ValueError, match="'id'"):
            parse_nfr({"nfrs": [_nfr(nfr_id=" ")]})
        with pytest.raises(ValueError, match="'title'"):
            parse_nfr({"nfrs": [_nfr(title="")]})
        with pytest.raises(ValueError, match="'target'"):
            parse_nfr({"nfrs": [_nfr(target="")]})
        with pytest.raises(ValueError, match="'title'"):
            parse_nfr({"runway": [_item(title="")]})

    def test_rejects_duplicate_ids(self) -> None:
        with pytest.raises(ValueError, match="Duplicate NFR id"):
            parse_nfr({"nfrs": [_nfr(), _nfr()]})
        with pytest.raises(ValueError, match="Duplicate runway item id"):
            parse_nfr({"runway": [_item(), _item()]})

    def test_rejects_unknown_status(self) -> None:
        with pytest.raises(ValueError, match="unknown status"):
            parse_nfr({"nfrs": [_nfr(status="broken")]})
        with pytest.raises(ValueError, match="unknown status"):
            parse_nfr({"runway": [_item(status="done")]})

    def test_rejects_bad_needed_by(self) -> None:
        with pytest.raises(ValueError, match="needed_by"):
            parse_nfr({"runway": [_item(needed_by="01.05.2025")]})


class TestRoundtrip:
    def test_save_and_load_roundtrip(self, tmp_path) -> None:
        register = NfrRegister(
            nfrs=[Nfr("N-1", "Resp", "p95 < 200 ms", "violated",
                      actual="340 ms", owner="Team A", notes="hot"),
                  Nfr("N-2", "Uptime", ">= 99.5 %", "met")],
            runway=[RunwayItem("RW-1", "Failover", "gap",
                               needed_by=date(2025, 5, 1), owner="Team B")])
        path = tmp_path / "nfr.json"
        save_nfr(path, register)
        assert load_nfr(path) == register

    def test_to_dict_omits_empty_optionals(self) -> None:
        data = nfr_to_dict(NfrRegister(
            nfrs=[Nfr("N-1", "T", "t", "met")],
            runway=[RunwayItem("RW-1", "T", "building")]))
        assert "actual" not in data["nfrs"][0]
        assert "owner" not in data["nfrs"][0]
        assert "needed_by" not in data["runway"][0]
        assert data["schema"] == 1
