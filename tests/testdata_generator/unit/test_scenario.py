# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       02.09.2026
# Geändert:       02.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für das Portfolio-Szenario (testdata_generator/scenario.py):
#   Artefakt-Vollständigkeit, Roundtrip durch die echten Parser
#   (load_solution_config, load_pi_config, Pooling), die eingebauten
#   Demo-Geschichten (Ausreißer, schwache Quelle, stage_map) und
#   Determinismus bei festem Seed und Referenzdatum.
# =============================================================================

from __future__ import annotations

from datetime import date

import pytest

from build_reports.pi_config import load_pi_config
from portfolio.aggregator import build_pooled_report_data
from portfolio.solution_config import KIND_PORTFOLIO, load_solution_config
from portfolio.summary import CONFIDENCE_LOW, SourceQuality
from testdata_generator.scenario import build_portfolio_scenario

REF = date(2025, 6, 30)


@pytest.fixture(scope="module")
def scenario(tmp_path_factory):
    """Build the scenario once per module (generation takes a few seconds)."""
    out = tmp_path_factory.mktemp("demo")
    paths = build_portfolio_scenario(out, seed=42, reference=REF,
                                     log=lambda m: None)
    return out, paths


class TestArtifacts:
    def test_all_expected_files_exist(self, scenario) -> None:
        out, paths = scenario
        for key in ("portfolio", "solution_alpha", "solution_beta",
                    "risks_alpha", "risks_beta", "nfr_alpha", "nfr_beta",
                    "pi_config", "readme"):
            assert paths[key].exists(), key
        assert len(list((out / "arts").glob("*_IssueTimes.xlsx"))) == 6
        assert len(list((out / "arts").glob("*_Transitions.xlsx"))) == 6
        # Die schwache Quelle Beta-3 liefert bewusst kein CFD.
        assert len(list((out / "arts").glob("*_CFD.xlsx"))) == 5
        assert len(list((out / "raw").glob("*_jira.json"))) == 6

    def test_pi_config_loads_and_covers_window(self, scenario) -> None:
        _, paths = scenario
        intervals = load_pi_config(paths["pi_config"])
        assert len(intervals) >= 4
        assert intervals[-1].to_date == REF


class TestConfigsRoundtrip:
    def test_solution_beta_carries_stage_map(self, scenario) -> None:
        _, paths = scenario
        cfg = load_solution_config(paths["solution_beta"])
        assert cfg.stage_map is not None
        assert list(cfg.stage_map.stages.keys()) == ["Vorlauf", "Umsetzung", "Fertig"]
        assert cfg.stage_map.first_stage == "Umsetzung"

    def test_solution_alpha_has_no_stage_map(self, scenario) -> None:
        _, paths = scenario
        assert load_solution_config(paths["solution_alpha"]).stage_map is None

    def test_portfolio_references_both_solutions(self, scenario) -> None:
        _, paths = scenario
        cfg = load_solution_config(paths["portfolio"])
        assert cfg.kind == KIND_PORTFOLIO
        assert len(cfg.members) == 2


class TestBuiltInStories:
    def test_pooling_works_and_beta_uses_custom_stages(self, scenario) -> None:
        _, paths = scenario
        cfg = load_solution_config(paths["solution_beta"])
        pooled = build_pooled_report_data(cfg, log=lambda m: None)
        assert pooled.stages == ["Vorlauf", "Umsetzung", "Fertig"]
        assert len(pooled.issues) > 0

    def test_weak_source_is_low_confidence(self, scenario) -> None:
        _, paths = scenario
        cfg = load_solution_config(paths["solution_beta"])
        qualities: list[SourceQuality] = []
        build_pooled_report_data(cfg, log=lambda m: None, quality_sink=qualities)
        by_name = {q.label: q for q in qualities}
        weak = by_name["ART Beta-3"]
        assert weak.confidence == CONFIDENCE_LOW
        assert weak.has_cfd is False
        # Datenstand der schwachen Quelle liegt ~60 Tage zurück.
        assert weak.age_days is not None and weak.age_days >= 55

    def test_healthy_sources_have_cfd_and_fresh_data(self, scenario) -> None:
        _, paths = scenario
        cfg = load_solution_config(paths["solution_alpha"])
        qualities: list[SourceQuality] = []
        pooled = build_pooled_report_data(cfg, log=lambda m: None,
                                          quality_sink=qualities)
        assert all(q.has_cfd for q in qualities)
        # Frisch relativ zum Szenario-Referenzdatum (nicht zu heute) pruefen:
        for q in qualities:
            assert q.data_as_of is not None
            assert (REF - q.data_as_of).days <= 30
        assert len(pooled.issues) == 360

    def test_roam_registers_load_and_carry_two_aging_risks(self, scenario) -> None:
        from portfolio.risks_config import ROAM_OWNED, load_risks
        _, paths = scenario
        alpha = load_risks(paths["risks_alpha"])
        beta = load_risks(paths["risks_beta"])
        assert alpha.risks and beta.risks
        aging = [r for r in alpha.risks + beta.risks
                 if r.roam == ROAM_OWNED and r.status_since is not None
                 and (REF - r.status_since).days > 30]
        assert len(aging) == 2
        assert load_solution_config(paths["solution_alpha"]).risks
        assert load_solution_config(paths["solution_beta"]).risks

    def test_portfolio_collects_risks_from_both_solutions(self, scenario) -> None:
        from portfolio.aggregator import _collect_risks
        _, paths = scenario
        cfg = load_solution_config(paths["portfolio"])
        entries = _collect_risks(cfg, log=lambda m: None)
        assert {source for source, _ in entries} == {"Solution Alpha", "Solution Beta"}
        assert len(entries) == 9

    def test_nfr_registers_load_and_tell_their_story(self, scenario) -> None:
        from portfolio.nfr_config import (
            RUNWAY_GAP,
            STATUS_VIOLATED,
            load_nfr,
        )
        _, paths = scenario
        alpha = load_nfr(paths["nfr_alpha"])
        beta = load_nfr(paths["nfr_beta"])
        assert alpha.nfrs and alpha.runway and beta.nfrs and beta.runway
        # Die Geschichte: genau eine verletzte NFR und eine überfällige Lücke,
        # beide bei Solution Beta.
        assert not any(n.status == STATUS_VIOLATED for n in alpha.nfrs)
        violated = [n for n in beta.nfrs if n.status == STATUS_VIOLATED]
        assert len(violated) == 1
        gaps = [r for r in beta.runway if r.status == RUNWAY_GAP]
        assert len(gaps) == 1
        assert gaps[0].needed_by is not None and gaps[0].needed_by < REF

    def test_portfolio_collects_nfr_from_both_solutions(self, scenario) -> None:
        from portfolio.aggregator import _collect_nfr
        _, paths = scenario
        cfg = load_solution_config(paths["portfolio"])
        nfrs, runway = _collect_nfr(cfg, log=lambda m: None)
        assert {source for source, _ in nfrs} == {"Solution Alpha", "Solution Beta"}
        assert len(nfrs) == 6
        assert len(runway) == 4

    def test_outlier_art_has_clearly_higher_cycle_time(self, scenario) -> None:
        from portfolio.aggregator import load_members
        from portfolio.summary import compute_summary
        _, paths = scenario
        cfg = load_solution_config(paths["solution_alpha"])
        summaries = {d.source_prefix: compute_summary(d, d.source_prefix)
                     for d in load_members(cfg, log=lambda m: None)}
        outlier = summaries["ART Alpha-3"].median_ct
        others = [summaries["ART Alpha-1"].median_ct, summaries["ART Alpha-2"].median_ct]
        assert outlier is not None and all(o is not None for o in others)
        assert outlier > 1.5 * max(others)


class TestDeterminism:
    def test_same_seed_same_issue_times(self, tmp_path) -> None:
        import openpyxl
        a = tmp_path / "a"
        b = tmp_path / "b"
        build_portfolio_scenario(a, seed=7, reference=REF, log=lambda m: None)
        build_portfolio_scenario(b, seed=7, reference=REF, log=lambda m: None)
        wa = openpyxl.load_workbook(a / "arts" / "Alpha-1_IssueTimes.xlsx").active
        wb = openpyxl.load_workbook(b / "arts" / "Alpha-1_IssueTimes.xlsx").active
        rows_a = [tuple(r) for r in wa.iter_rows(values_only=True)]
        rows_b = [tuple(r) for r in wb.iter_rows(values_only=True)]
        assert rows_a == rows_b
