# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       22.06.2026
# Geändert:       22.06.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für portfolio.solution_config: Validierung und Parsing einer
#   Solution-Konfiguration aus einem JSON-Objekt (ohne Dateizugriff).
# =============================================================================

from __future__ import annotations

from datetime import date

import pytest

from portfolio.solution_config import (
    KIND_SOLUTION,
    parse_solution_config,
    to_dict,
)


def _valid_dict() -> dict:
    return {
        "schema": 1,
        "kind": "solution",
        "name": "Payments Solution",
        "framework": "SAFe",
        "members": [
            {"name": "ART Alpha", "template": "C:/x/ART_Alpha.json"},
            {"name": "ART Beta", "issue_times": "C:/x/ART_Beta_IssueTimes.xlsx"},
        ],
        "report": {"from_date": "2025-01-01", "to_date": "2025-12-31",
                   "modes": ["pooled"]},
    }


class TestValid:
    def test_parses_name_and_kind(self) -> None:
        cfg = parse_solution_config(_valid_dict())
        assert cfg.name == "Payments Solution"
        assert cfg.kind == KIND_SOLUTION

    def test_parses_members(self) -> None:
        cfg = parse_solution_config(_valid_dict())
        assert [m.name for m in cfg.members] == ["ART Alpha", "ART Beta"]
        assert cfg.members[0].template.endswith("ART_Alpha.json")
        assert cfg.members[1].issue_times.endswith("ART_Beta_IssueTimes.xlsx")

    def test_parses_report_dates(self) -> None:
        cfg = parse_solution_config(_valid_dict())
        assert cfg.from_date == date(2025, 1, 1)
        assert cfg.to_date == date(2025, 12, 31)

    def test_dates_optional(self) -> None:
        d = _valid_dict()
        d.pop("report")
        cfg = parse_solution_config(d)
        assert cfg.from_date is None and cfg.to_date is None
        assert cfg.modes == ["pooled"]


class TestInvalid:
    def test_missing_name_raises(self) -> None:
        d = _valid_dict()
        d["name"] = ""
        with pytest.raises(ValueError, match="name"):
            parse_solution_config(d)

    def test_empty_members_raises(self) -> None:
        d = _valid_dict()
        d["members"] = []
        with pytest.raises(ValueError, match="members"):
            parse_solution_config(d)

    def test_member_without_source_raises(self) -> None:
        d = _valid_dict()
        d["members"] = [{"name": "ART Alpha"}]
        with pytest.raises(ValueError, match="template.*issue_times|issue_times"):
            parse_solution_config(d)

    def test_unknown_kind_raises(self) -> None:
        d = _valid_dict()
        d["kind"] = "team"
        with pytest.raises(ValueError, match="kind"):
            parse_solution_config(d)


class TestPortfolio:
    def _portfolio_dict(self) -> dict:
        return {
            "schema": 1,
            "kind": "portfolio",
            "name": "Group Portfolio",
            "framework": "SAFe",
            "members": [
                {"name": "Solution A", "template": "C:/x/SolutionA.json"},
                {"name": "Solution B", "template": "C:/x/SolutionB.json"},
            ],
        }

    def test_portfolio_parses(self) -> None:
        cfg = parse_solution_config(self._portfolio_dict())
        assert cfg.kind == "portfolio"
        assert [m.name for m in cfg.members] == ["Solution A", "Solution B"]
        assert cfg.members[0].template.endswith("SolutionA.json")

    def test_portfolio_member_needs_template(self) -> None:
        d = self._portfolio_dict()
        # A portfolio member referencing raw issue_times instead of a solution
        # template is rejected.
        d["members"] = [{"name": "Solution A", "issue_times": "C:/x/A.xlsx"}]
        with pytest.raises(ValueError, match="template"):
            parse_solution_config(d)


class TestSerialisation:
    def test_roundtrip_equal(self) -> None:
        cfg = parse_solution_config(_valid_dict())
        assert parse_solution_config(to_dict(cfg)) == cfg

    def test_to_dict_omits_empty_member_fields(self) -> None:
        cfg = parse_solution_config(_valid_dict())
        member_dicts = to_dict(cfg)["members"]
        # ART Beta was given only issue_times → no empty 'template'/'cfd' keys
        beta = member_dicts[1]
        assert "issue_times" in beta
        assert "template" not in beta and "cfd" not in beta

    def test_to_dict_serialises_dates(self) -> None:
        cfg = parse_solution_config(_valid_dict())
        report = to_dict(cfg)["report"]
        assert report["from_date"] == "2025-01-01"
        assert report["to_date"] == "2025-12-31"
