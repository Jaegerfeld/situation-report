# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       26.10.2026
# Geändert:       26.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für die Struktur des Demo-Datenraums (testdata_generator/
#   structure.py, Beta Schnitt 1a): Vorlagen, Validierung, Roundtrip,
#   Kompakt-Spezifikation der Kommandozeile, Namensvorschläge, Schätzung.
# =============================================================================

from __future__ import annotations

import json

import pytest

from testdata_generator.structure import (
    GREEK,
    REGISTER_NAMES,
    STRUCTURE_TEMPLATES,
    TEMPLATE_LARGE,
    TEMPLATE_SMALL,
    TEMPLATE_STANDARD,
    WARN_ARTS,
    WORKFLOW_CLASSIC,
    WORKFLOW_STAGE_MAP,
    PortfolioSpec,
    SolutionSpec,
    Structure,
    estimate,
    from_dict,
    load_structure,
    make_portfolio,
    parse_arts_spec,
    resolve_structure,
    save_structure,
    slug,
    structure_from_arts_spec,
    structure_template,
    suggest_solution_name,
    to_dict,
    validate,
)


class TestTemplates:
    def test_standard_is_the_demo_portfolio(self) -> None:
        s = structure_template(TEMPLATE_STANDARD)
        assert s.n_portfolios == 1 and s.n_solutions == 2 and s.n_arts == 6
        p = s.portfolios[0]
        assert p.name == "Demo Portfolio" and p.key == "demo_portfolio"
        alpha, beta = p.solutions
        assert alpha.name == "Alpha" and alpha.key == "alpha"
        assert alpha.workflow == WORKFLOW_CLASSIC
        assert alpha.arts == ["Alpha-1", "Alpha-2", "Alpha-3"]
        assert alpha.member_names == ["ART Alpha-1", "ART Alpha-2", "ART Alpha-3"]
        assert alpha.display_name == "Solution Alpha"
        assert beta.workflow == WORKFLOW_STAGE_MAP
        assert beta.arts == ["Beta-1", "Beta-2", "Beta-3"]

    def test_small_has_one_solution_with_two_arts(self) -> None:
        s = structure_template(TEMPLATE_SMALL)
        assert (s.n_portfolios, s.n_solutions, s.n_arts) == (1, 1, 2)

    def test_large_has_five_portfolios_and_mixed_art_counts(self) -> None:
        s = structure_template(TEMPLATE_LARGE)
        assert s.n_portfolios == 5
        counts = {len(sol.arts) for p in s.portfolios for sol in p.solutions}
        assert min(counts) == 1 and max(counts) == 6
        assert all(3 <= len(p.solutions) <= 4 for p in s.portfolios)
        # Solution names stay unique across the whole structure.
        names = [sol.name for p in s.portfolios for sol in p.solutions]
        assert len(names) == len(set(names))

    @pytest.mark.parametrize("name", STRUCTURE_TEMPLATES)
    def test_every_template_validates(self, name: str) -> None:
        validate(structure_template(name))

    def test_unknown_template_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown structure template"):
            structure_template("huge")

    def test_describe_counts(self) -> None:
        assert structure_template(TEMPLATE_STANDARD).describe() \
            == "1 Portfolio · 2 Solutions · 6 ARTs"
        assert structure_template(TEMPLATE_SMALL).describe() \
            == "1 Portfolio · 1 Solution · 2 ARTs"


class TestValidation:
    def _one(self, **kw) -> Structure:
        base = {"name": "Alpha", "arts": ["Alpha-1"], "workflow": WORKFLOW_CLASSIC}
        base.update(kw)
        return Structure([PortfolioSpec("P", [SolutionSpec(**base)])])

    def test_no_portfolio(self) -> None:
        with pytest.raises(ValueError, match="at least one portfolio"):
            validate(Structure([]))

    def test_no_solution(self) -> None:
        with pytest.raises(ValueError, match="at least one solution"):
            validate(Structure([PortfolioSpec("P", [])]))

    def test_solution_without_art(self) -> None:
        with pytest.raises(ValueError, match="at least one ART"):
            validate(self._one(arts=[]))

    def test_unknown_workflow(self) -> None:
        with pytest.raises(ValueError, match="workflow 'kanban' unknown"):
            validate(self._one(workflow="kanban"))

    def test_duplicate_art_within_portfolio(self) -> None:
        s = Structure([PortfolioSpec("P", [
            SolutionSpec("Alpha", ["X-1"]), SolutionSpec("Beta", ["X-1"])])])
        with pytest.raises(ValueError, match="ART name 'X-1' is not unique"):
            validate(s)

    def test_duplicate_solution_key(self) -> None:
        s = Structure([PortfolioSpec("P", [
            SolutionSpec("Alpha", ["A-1"]), SolutionSpec("alpha", ["B-1"])])])
        with pytest.raises(ValueError, match="solution key 'alpha' is not unique"):
            validate(s)

    def test_duplicate_portfolio_key(self) -> None:
        s = Structure([PortfolioSpec("Nord", [SolutionSpec("A", ["A-1"])]),
                       PortfolioSpec("nord", [SolutionSpec("B", ["B-1"])])])
        with pytest.raises(ValueError, match="portfolio key 'nord' is not unique"):
            validate(s)

    def test_file_unsafe_name(self) -> None:
        with pytest.raises(ValueError, match="only letters"):
            validate(self._one(arts=["Alpha/1"]))

    def test_empty_and_padded_names(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            validate(self._one(name=""))
        with pytest.raises(ValueError, match="whitespace"):
            validate(self._one(name=" Alpha"))

    def test_wrong_schema(self) -> None:
        with pytest.raises(ValueError, match="schema"):
            validate(Structure(structure_template(TEMPLATE_SMALL).portfolios, schema=2))


class TestSerialisation:
    def test_roundtrip_file(self, tmp_path) -> None:
        s = structure_template(TEMPLATE_LARGE)
        path = tmp_path / "structure.json"
        save_structure(path, s)
        loaded = load_structure(path)
        assert to_dict(loaded) == to_dict(s)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["schema"] == 1
        assert data["portfolios"][0]["solutions"][0]["arts"] == ["Alpha-1", "Alpha-2", "Alpha-3"]

    def test_from_dict_validates(self) -> None:
        with pytest.raises(ValueError, match="'portfolios' must be a list"):
            from_dict({"schema": 1})
        with pytest.raises(ValueError, match="'arts' must be a list"):
            from_dict({"portfolios": [{"name": "P", "solutions": [
                {"name": "A", "arts": "A-1"}]}]})

    def test_from_dict_defaults_workflow_to_classic(self) -> None:
        s = from_dict({"portfolios": [{"name": "P", "solutions": [
            {"name": "A", "arts": ["A-1"]}]}]})
        assert s.portfolios[0].solutions[0].workflow == WORKFLOW_CLASSIC

    def test_display_prefix_is_not_doubled(self) -> None:
        sol = SolutionSpec("Solution Nord", ["Nord-1"])
        assert sol.short == "Nord" and sol.display_name == "Solution Nord"
        assert sol.key == "nord"
        assert to_dict(Structure([PortfolioSpec("P", [sol])]))[
            "portfolios"][0]["solutions"][0]["name"] == "Nord"

    def test_invalid_json_file(self, tmp_path) -> None:
        path = tmp_path / "broken.json"
        path.write_text("{not json", encoding="utf-8")
        with pytest.raises(ValueError, match="not valid JSON"):
            load_structure(path)


class TestBuilding:
    def test_slug(self) -> None:
        assert slug("Solution Süd") == "sued"
        assert slug("Portfolio Nord-West 2") == "portfolio_nord_west_2"
        assert slug("Ärger & Öl") == "aerger_oel"

    def test_suggest_names_beyond_greek(self) -> None:
        assert suggest_solution_name(0) == "Alpha"
        assert suggest_solution_name(len(GREEK) - 1) == "Omega"
        assert suggest_solution_name(len(GREEK)) == "S25"

    def test_make_portfolio_names_and_arts(self) -> None:
        p = make_portfolio("P", [(3, WORKFLOW_CLASSIC), (1, WORKFLOW_STAGE_MAP)])
        assert [s.name for s in p.solutions] == ["Alpha", "Beta"]
        assert p.solutions[1].arts == ["Beta-1"]
        assert p.arts == ["Alpha-1", "Alpha-2", "Alpha-3", "Beta-1"]
        custom = make_portfolio("P", [(2, WORKFLOW_CLASSIC)], names=["Nord"])
        assert custom.solutions[0].arts == ["Nord-1", "Nord-2"]

    def test_parse_arts_spec(self) -> None:
        assert parse_arts_spec("3,4s,1") == [
            (3, WORKFLOW_CLASSIC), (4, WORKFLOW_STAGE_MAP), (1, WORKFLOW_CLASSIC)]
        assert parse_arts_spec(" 2c , 5 ") == [(2, WORKFLOW_CLASSIC), (5, WORKFLOW_CLASSIC)]

    @pytest.mark.parametrize("bad", ["", "3,,1", "a", "3x", "0", "3,0"])
    def test_parse_arts_spec_rejects(self, bad: str) -> None:
        with pytest.raises(ValueError):
            parse_arts_spec(bad)

    def test_structure_from_arts_spec(self) -> None:
        s = structure_from_arts_spec("3,4s,1")
        assert s.describe() == "1 Portfolio · 3 Solutions · 8 ARTs"
        assert s.portfolios[0].solutions[1].workflow == WORKFLOW_STAGE_MAP
        assert s.portfolios[0].solutions[2].arts == ["Gamma-1"]

    def test_resolve_structure(self, tmp_path) -> None:
        assert resolve_structure(None).describe() == "1 Portfolio · 2 Solutions · 6 ARTs"
        assert resolve_structure("small").n_arts == 2
        path = tmp_path / "s.json"
        save_structure(path, structure_from_arts_spec("1"))
        assert resolve_structure(path).n_arts == 1


class TestEstimate:
    def test_standard_numbers(self) -> None:
        e = estimate(structure_template(TEMPLATE_STANDARD), stands=6)
        assert (e.portfolios, e.solutions, e.arts) == (1, 2, 6)
        assert e.jira_exports == 6 and e.workbooks == 18
        assert e.registers == 2 * len(REGISTER_NAMES) == 22
        assert e.stands == 6 and e.deltas == 5
        assert not e.warn

    def test_large_warns_on_arts(self) -> None:
        e = estimate(structure_template(TEMPLATE_LARGE), stands=6, scale="m")
        assert e.arts >= WARN_ARTS and e.warn
        assert "ARTs" in e.warn_reason
        assert e.stands == 30 and e.deltas == 25

    def test_five_small_portfolios_warn_only_at_scale_l(self) -> None:
        s = Structure([PortfolioSpec(f"P{i}", [SolutionSpec(f"S{i}", [f"S{i}-1"])])
                       for i in range(5)])
        assert not estimate(s, scale="m").warn
        assert estimate(s, scale="l").warn
