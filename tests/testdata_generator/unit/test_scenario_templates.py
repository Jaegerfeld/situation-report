# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       26.10.2026
# Geändert:       26.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Die Geschichts-Vorlagen im gebauten Datenraum (Beta Schnitt 2): Ruhig
#   ohne Wendungen, Eskalation mit Druck Stand für Stand, Erholung mit
#   abklingenden Ereignissen, Schalter in der Kommandozeile — geprüft über
#   die eingefrorenen Stände, die Register und die Delta-Briefings.
# =============================================================================

from __future__ import annotations

import json
from datetime import date

import pytest

from portfolio.delta import compute_delta
from portfolio.dependency_config import DEP_BLOCKED, DEP_ON_TRACK, load_dependencies
from portfolio.slo_config import load_slo, slo_status
from portfolio.snapshot import load_snapshot
from portfolio.solution_config import load_solution_config
from portfolio.summary import CONFIDENCE_LOW, CONFIDENCE_MEDIUM
from testdata_generator.scenario import build_portfolio_scenario
from testdata_generator.story import (
    EVENT_BLOCKED,
    EVENT_OUTLIER,
    TEMPLATE_CALM,
    TEMPLATE_ESCALATION,
    TEMPLATE_RECOVERY,
    load_story,
)

REF = date(2025, 6, 30)


def _risk_ids(snapshot) -> set[str]:
    return {r["id"] for r in snapshot.governance["risks"]}


def _dep_status(snapshot, dep_id: str) -> str | None:
    for d in snapshot.governance["dependencies"]:
        if d["id"] == dep_id:
            return str(d["status"])
    return None


def _art_p85(solution_cfg) -> dict[str, float]:
    """P85 cycle time per ART of one solution (the comparison units)."""
    from portfolio.aggregator import load_comparison_units
    from portfolio.summary import compute_summary
    cfg = load_solution_config(solution_cfg)
    return {u.source_prefix: compute_summary(u, u.source_prefix, 90).p85_ct
            for u in load_comparison_units(cfg, log=lambda m: None)}


def _confidence(snapshot, label: str) -> str | None:
    for s in snapshot.sources:
        if s["label"] == label:
            return str(s["confidence"])
    return None


@pytest.fixture(scope="module")
def calm(tmp_path_factory):
    out = tmp_path_factory.mktemp("calm")
    paths = build_portfolio_scenario(out, seed=42, reference=REF, log=lambda m: None,
                                     scale="s", stands=3, template=TEMPLATE_CALM)
    return out, paths


@pytest.fixture(scope="module")
def escalation(tmp_path_factory):
    out = tmp_path_factory.mktemp("escalation")
    paths = build_portfolio_scenario(out, seed=42, reference=REF, log=lambda m: None,
                                     scale="s", stands=6, template=TEMPLATE_ESCALATION)
    return out, paths


@pytest.fixture(scope="module")
def recovery(tmp_path_factory):
    out = tmp_path_factory.mktemp("recovery")
    paths = build_portfolio_scenario(out, seed=42, reference=REF, log=lambda m: None,
                                     scale="s", stands=6, template=TEMPLATE_RECOVERY)
    return out, paths


class TestCalm:
    def test_no_turning_points_anywhere(self, calm) -> None:
        _, paths = calm
        story = load_story(paths["story"])
        assert story.template == TEMPLATE_CALM and story.stands == 3
        assert all(not e.enabled for e in story.events)
        last = load_snapshot(paths["snapshot_now"])
        assert "BR-2" not in _risk_ids(last)
        assert _dep_status(last, "AD-1") == DEP_ON_TRACK
        assert _dep_status(last, "BD-3") == DEP_ON_TRACK
        assert all(slo_status(r) != "breached" for r in load_slo(paths["slo_beta"]).records)
        deps = load_dependencies(paths["dependencies_alpha"])
        assert not any(d.status == DEP_BLOCKED for d in deps.dependencies)

    def test_no_outlier_and_no_weak_source(self, calm) -> None:
        _, paths = calm
        last = load_snapshot(paths["snapshot_now"])
        # Without the outlier the three Alpha ARTs stay within a factor of two.
        alpha = _art_p85(paths["solution_alpha"])
        assert len(alpha) == 3 and max(alpha.values()) < 2 * min(alpha.values())
        assert _confidence(last, "ART Beta-3") != CONFIDENCE_LOW
        readme = paths["readme"].read_text(encoding="utf-8")
        assert "Calm" in readme and "_(off)_" in readme

    def test_deltas_stay_governance_quiet(self, calm) -> None:
        _, paths = calm
        snaps = [load_snapshot(p) for p in paths["snapshots"]]
        for prev, now in zip(snaps, snaps[1:]):
            delta = compute_delta(prev, now)
            assert delta.completed_delta > 0
            assert delta.governance["risks"].added == []
            assert delta.governance["dependencies"].changed == []


class TestEscalation:
    def test_pressure_rises_stand_by_stand(self, escalation) -> None:
        _, paths = escalation
        snaps = [load_snapshot(p) for p in paths["snapshots"]]
        beta_slo = [[r for r in s.governance["slo"] if r["id"] == "Order Sync API"] for s in snaps]
        assert beta_slo[0][0]["status"] != "breached"
        assert beta_slo[1][0]["status"] == "breached"             # early
        assert _dep_status(snaps[2], "AD-1") != DEP_BLOCKED
        assert _dep_status(snaps[3], "AD-1") == DEP_BLOCKED         # mid
        assert _dep_status(snaps[3], "BD-3") != DEP_BLOCKED
        assert _dep_status(snaps[4], "BD-3") == DEP_BLOCKED         # late
        assert _confidence(snaps[3], "ART Beta-3") == CONFIDENCE_MEDIUM
        assert _confidence(snaps[4], "ART Beta-3") == CONFIDENCE_LOW
        assert "BR-2" not in _risk_ids(snaps[4]) and "BR-2" in _risk_ids(snaps[5])

    def test_each_delta_tells_one_step(self, escalation) -> None:
        _, paths = escalation
        texts = [md.read_text(encoding="utf-8") for md, _ in paths["deltas"]]
        assert "Order Sync API" in texts[0]                       # 01->02 the SLO breach
        assert "AD-1" in texts[2]                                 # 03->04 blocked
        assert "BD-3" in texts[3] and "ART Beta-3" in texts[3]   # 04->05 cross seam + decay
        assert "BR-2" in texts[4]                                 # 05->06 new risk
        story = load_story(paths["story"])
        blocked = next(e for e in story.events if e.event_id == EVENT_BLOCKED)
        assert blocked.stand_from == 4 and blocked.stand_to is None


class TestRecovery:
    def test_starts_bad_and_heals(self, recovery) -> None:
        _, paths = recovery
        snaps = [load_snapshot(p) for p in paths["snapshots"]]
        assert _dep_status(snaps[0], "AD-1") == DEP_BLOCKED
        assert _dep_status(snaps[1], "AD-1") == DEP_BLOCKED        # early = stand 2
        assert _dep_status(snaps[2], "AD-1") != DEP_BLOCKED
        assert _dep_status(snaps[0], "BD-3") == DEP_BLOCKED
        assert _dep_status(snaps[3], "BD-3") == DEP_BLOCKED        # mid = stand 4
        assert _dep_status(snaps[4], "BD-3") != DEP_BLOCKED
        first_slo = [r for r in snaps[0].governance["slo"] if r["id"] == "Order Sync API"][0]
        last_slo = [r for r in snaps[-1].governance["slo"] if r["id"] == "Order Sync API"][0]
        assert first_slo["status"] == "breached" and last_slo["status"] != "breached"
        assert _confidence(snaps[4], "ART Beta-3") == CONFIDENCE_MEDIUM
        assert _confidence(snaps[5], "ART Beta-3") != CONFIDENCE_MEDIUM
        assert "BR-2" not in _risk_ids(snaps[-1])

    def test_outlier_finds_its_pace(self, recovery) -> None:
        _, paths = recovery
        snaps = [load_snapshot(p) for p in paths["snapshots"]]
        # The portfolio stands compare solutions: Alpha's pooled P85 drops once
        # the outlier (active in stands 1-4) finds its pace ...
        p85_early = {u["label"]: u["p85_ct"] for u in snaps[0].units}["Solution Alpha"]
        p85_late = {u["label"]: u["p85_ct"] for u in snaps[-1].units}["Solution Alpha"]
        assert p85_early > 1.5 * p85_late
        # ... and in the healed room the three Alpha ARTs are peers again.
        alpha = _art_p85(paths["solution_alpha"])
        assert max(alpha.values()) < 2 * min(alpha.values())
        story = load_story(paths["story"])
        outlier = next(e for e in story.events if e.event_id == EVENT_OUTLIER)
        assert (outlier.stand_from, outlier.stand_to) == (1, 4)
        readme = paths["readme"].read_text(encoding="utf-8")
        assert "stands 01 to 04" in readme and "Recovery" in readme

    def test_registers_in_the_room_show_the_healed_state(self, recovery) -> None:
        _, paths = recovery
        cfg = load_solution_config(paths["solution_beta"])
        assert cfg.name == "Solution Beta"
        deps = load_dependencies(paths["dependencies_beta"])
        assert all(d.status != DEP_BLOCKED for d in deps.dependencies)
        data = json.loads(paths["story"].read_text(encoding="utf-8"))
        assert data["template"] == TEMPLATE_RECOVERY and data["schema"] == 2


class TestSwitchesInTheRoom:
    def test_switch_turns_a_turning_point_off(self, tmp_path) -> None:
        messages: list[str] = []
        paths = build_portfolio_scenario(tmp_path, seed=42, reference=REF, log=messages.append,
                                         scale="s", stands=2, switches={"E3": False, "E8": False})
        last = load_snapshot(paths["snapshot_now"])
        assert _dep_status(last, "AD-1") != DEP_BLOCKED
        assert _dep_status(last, "BD-3") == DEP_BLOCKED            # E4 still on
        assert _confidence(last, "ART Beta-3") == CONFIDENCE_MEDIUM   # no decay
        story = load_story(paths["story"])
        assert {e.event_id for e in story.events if not e.enabled} == {"E3", "E8"}

    def test_unknown_template_is_rejected_before_building(self, tmp_path) -> None:
        with pytest.raises(ValueError, match="Unknown story template"):
            build_portfolio_scenario(tmp_path, reference=REF, log=lambda m: None, template="drama")
        assert not (tmp_path / "portfolio.json").exists()
