# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       22.06.2026
# Geändert:       04.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für portfolio.solution_config: Validierung und Parsing einer
#   Solution-Konfiguration aus einem JSON-Objekt (ohne Dateizugriff).
# =============================================================================

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from portfolio.solution_config import (
    KIND_SOLUTION,
    Member,
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

    def test_terminology_defaults_safe(self) -> None:
        cfg = parse_solution_config(_valid_dict())  # report has no terminology
        assert cfg.terminology == "SAFe"

    def test_terminology_parsed_and_serialised(self) -> None:
        d = _valid_dict()
        d["report"]["terminology"] = "Global"
        cfg = parse_solution_config(d)
        assert cfg.terminology == "Global"
        assert to_dict(cfg)["report"]["terminology"] == "Global"
        assert parse_solution_config(to_dict(cfg)) == cfg

    def test_invalid_terminology_falls_back_to_safe(self) -> None:
        d = _valid_dict()
        d["report"]["terminology"] = "Nonsense"
        assert parse_solution_config(d).terminology == "SAFe"


# ---------------------------------------------------------------------------
# A4: optional custom stage map
# ---------------------------------------------------------------------------

def _stage_map_dict() -> dict:
    return {
        "stages": {
            "Backlog": ["Funnel", "Analysis"],
            "In Arbeit": ["Implementing", "Review"],
            "Fertig": ["Done", "Released"],
        },
        "first_stage": "In Arbeit",
        "closed_stage": "Fertig",
    }


class TestStageMap:
    def test_absent_block_yields_none(self) -> None:
        cfg = parse_solution_config(_valid_dict())
        assert cfg.stage_map is None

    def test_valid_block_is_parsed(self) -> None:
        d = _valid_dict()
        d["stage_map"] = _stage_map_dict()
        cfg = parse_solution_config(d)
        assert list(cfg.stage_map.stages.keys()) == ["Backlog", "In Arbeit", "Fertig"]
        assert cfg.stage_map.first_stage == "In Arbeit"
        assert cfg.stage_map.lookup()["Review"] == "In Arbeit"

    def test_duplicate_source_stage_rejected(self) -> None:
        d = _valid_dict()
        sm = _stage_map_dict()
        sm["stages"]["Fertig"].append("Analysis")  # already in Backlog
        d["stage_map"] = sm
        with pytest.raises(ValueError, match="Analysis"):
            parse_solution_config(d)

    def test_unknown_boundary_marker_rejected(self) -> None:
        d = _valid_dict()
        sm = _stage_map_dict()
        sm["first_stage"] = "Nirvana"
        d["stage_map"] = sm
        with pytest.raises(ValueError, match="first_stage"):
            parse_solution_config(d)

    def test_identical_markers_rejected(self) -> None:
        d = _valid_dict()
        sm = _stage_map_dict()
        sm["closed_stage"] = "In Arbeit"
        d["stage_map"] = sm
        with pytest.raises(ValueError, match="must differ"):
            parse_solution_config(d)

    def test_empty_group_rejected(self) -> None:
        d = _valid_dict()
        sm = _stage_map_dict()
        sm["stages"]["Backlog"] = []
        d["stage_map"] = sm
        with pytest.raises(ValueError, match="Backlog"):
            parse_solution_config(d)

    def test_roundtrip_through_to_dict(self) -> None:
        d = _valid_dict()
        d["stage_map"] = _stage_map_dict()
        cfg = parse_solution_config(d)
        again = parse_solution_config(to_dict(cfg))
        assert again.stage_map == cfg.stage_map

    def test_v1_dict_without_block_roundtrips_without_block(self) -> None:
        cfg = parse_solution_config(_valid_dict())
        assert "stage_map" not in to_dict(cfg)


class TestResolveConfigPath:
    """Die Datenraum-Pfadregel (Phase 1, 04.09.2026): relativ = relativ
    zur Config-Datei; absolut unveraendert; CWD-Altbestand per Fallback."""

    def test_absolute_passes_through(self, tmp_path) -> None:
        from portfolio.solution_config import resolve_config_path
        p = tmp_path / "x.json"
        assert resolve_config_path(tmp_path, str(p)) == p

    def test_relative_resolves_against_config_folder(self, tmp_path) -> None:
        from portfolio.solution_config import resolve_config_path
        target = tmp_path / "registers" / "risks.json"
        target.parent.mkdir()
        target.write_text("{}", encoding="utf-8")
        assert resolve_config_path(
            tmp_path, "registers/risks.json") == target

    def test_missing_file_points_at_config_relative_location(
            self, tmp_path) -> None:
        # Fehlermeldungen sollen auf den GEMEINTEN Ort zeigen.
        from portfolio.solution_config import resolve_config_path
        assert resolve_config_path(tmp_path, "registers/fehlt.json") == (
            tmp_path / "registers" / "fehlt.json")

    def test_legacy_cwd_fallback_warns(self, tmp_path, monkeypatch) -> None:
        from portfolio.solution_config import resolve_config_path
        cwd = tmp_path / "arbeitsverzeichnis"
        base = tmp_path / "configs"
        cwd.mkdir(); base.mkdir()
        (cwd / "alt.json").write_text("{}", encoding="utf-8")
        monkeypatch.chdir(cwd)
        warnings: list[str] = []
        resolved = resolve_config_path(base, "alt.json", warnings.append)
        assert resolved == Path("alt.json")
        assert warnings and "portable" in warnings[0]

    def test_no_base_keeps_todays_behaviour(self) -> None:
        from portfolio.solution_config import resolve_config_path
        assert resolve_config_path(None, "irgendwo/x.json") == Path(
            "irgendwo/x.json")

    def test_loader_sets_base_dir_but_never_serialises_it(
            self, tmp_path) -> None:
        from portfolio.solution_config import (
            SolutionConfig,
            load_solution_config,
            save_solution_config,
            to_dict,
        )
        cfg_file = tmp_path / "solution.json"
        save_solution_config(cfg_file, SolutionConfig(
            name="S", members=[Member(name="A", issue_times="a.xlsx")]))
        loaded = load_solution_config(cfg_file)
        assert loaded.base_dir == tmp_path.resolve()
        assert "base_dir" not in to_dict(loaded)


class TestArtDepthSetting:
    """Die ART-Tiefe gehoert zur Report-Einstellung und muss den Weg
    Speichern → Laden unveraendert ueberstehen. Verallgemeinerte Lehre aus
    dem base_dir-Feldbefund (04.09.2026): jedes neue Konfigurationsfeld
    bekommt seinen Rundlauf-Test in derselben Aenderung."""

    def test_defaults_to_off(self) -> None:
        cfg = parse_solution_config(_valid_dict())  # report kennt art_depth nicht
        assert cfg.art_depth is False

    def test_parsed_and_serialised(self) -> None:
        d = _valid_dict()
        d["report"]["art_depth"] = True
        cfg = parse_solution_config(d)
        assert cfg.art_depth is True
        assert to_dict(cfg)["report"]["art_depth"] is True
        assert parse_solution_config(to_dict(cfg)) == cfg

    def test_off_leaves_the_file_untouched(self) -> None:
        """Ausgeschaltet schreibt die Einstellung nichts in die Datei —
        bestehende Konfigurationen aendern sich durch das Feature nicht."""
        cfg = parse_solution_config(_valid_dict())
        assert "art_depth" not in to_dict(cfg)["report"]
