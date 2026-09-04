# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       04.09.2026
# Geändert:       04.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests der Register-Generatoren (Datenraum Phase 3): Seed-
#   Determinismus, Skalen-Monotonie (s ⊂ m < l), die prev/now-Regel
#   (prev ist eine echte Teilmenge, gemeinsame Einträge sind identisch)
#   und die Anker-Invarianten, die die erzählten Geschichten einzigartig
#   halten (nie violated/breached/blocked/überfällig/Survivor/Orphan/
#   Zombie aus der Grundmenge; Owner sind Teams; nur echte ART-Namen).
# =============================================================================

from __future__ import annotations

import dataclasses
from datetime import date

import pytest

from portfolio.capability_config import CapabilityMap
from portfolio.decision_config import ASSUMPTION_OPEN, KIND_ASSUMPTION, DecisionLog
from portfolio.dependency_config import DEP_BLOCKED, DependencyRegister
from portfolio.flow_problems_config import FlowProblemRegister
from portfolio.nfr_config import RUNWAY_GAP, STATUS_VIOLATED, NfrRegister
from portfolio.risks_config import RiskRegister
from portfolio.slo_config import SloRegister, slo_status
from portfolio.themes_config import ThemesRegister, orphan_theme_ids, zombie_epics
from testdata_generator.register_gen import (
    SCALE_L,
    SCALE_M,
    SCALE_PROFILES,
    SCALE_S,
    populate_registers,
)

REF = date(2026, 6, 30)
ARTS = ["ART Alpha-1", "ART Alpha-2", "ART Alpha-3"]


def _empty() -> dict[str, object]:
    return {"risks": RiskRegister(), "nfr": NfrRegister(),
            "capabilities": CapabilityMap(),
            "dependencies": DependencyRegister(),
            "decisions": DecisionLog(), "slo": SloRegister(),
            "dora": object(),  # Generator fasst DORA nie an
            "flow_problems": FlowProblemRegister(),
            "themes": ThemesRegister()}


def _build(scale: str = SCALE_M, prev: bool = False,
           seed: int = 42) -> dict[str, object]:
    regs = _empty()
    populate_registers(regs, "alpha", ARTS, REF, seed=seed, scale=scale,
                       prev=prev)
    return regs


def _ids(regs: dict[str, object]) -> dict[str, list[str]]:
    return {
        "risks": [r.risk_id for r in regs["risks"].risks],
        "nfr": [n.nfr_id for n in regs["nfr"].nfrs],
        "runway": [r.item_id for r in regs["nfr"].runway],
        "caps": [c.cap_id for c in regs["capabilities"].capabilities],
        "deps": [d.dep_id for d in regs["dependencies"].dependencies],
        "decisions": [e.entry_id for e in regs["decisions"].entries],
        "slo": [r.service for r in regs["slo"].records],
        "flow": [p.problem_id for p in regs["flow_problems"].problems],
        "themes": [t.theme_id for t in regs["themes"].themes],
        "epics": [e.epic_id for e in regs["themes"].epics],
    }


class TestDeterminismAndScales:
    def test_same_seed_same_registers(self) -> None:
        a, b = _build(), _build()
        assert dataclasses.asdict(a["risks"]) == dataclasses.asdict(b["risks"])
        assert dataclasses.asdict(a["themes"]) == dataclasses.asdict(
            b["themes"])
        assert _ids(a) == _ids(b)

    def test_different_seed_different_content(self) -> None:
        a, b = _build(seed=42), _build(seed=43)
        assert dataclasses.asdict(a["risks"]) != dataclasses.asdict(b["risks"])

    def test_scale_s_adds_nothing(self) -> None:
        regs = _build(scale=SCALE_S)
        assert all(not v for v in _ids(regs).values())

    def test_scales_grow_monotonically(self) -> None:
        m = sum(len(v) for v in _ids(_build(scale=SCALE_M)).values())
        line = sum(len(v) for v in _ids(_build(scale=SCALE_L)).values())
        assert 0 < m < line

    def test_unknown_scale_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="Unknown scale"):
            _build(scale="xl")


class TestPrevNowRule:
    def test_prev_is_a_strict_subset_with_identical_shared_entries(
            self) -> None:
        now, prev = _build(prev=False), _build(prev=True)
        now_risks = {r.risk_id: r for r in now["risks"].risks}
        prev_risks = {r.risk_id: r for r in prev["risks"].risks}
        assert set(prev_risks) < set(now_risks)
        for rid, risk in prev_risks.items():
            # Gemeinsame Eintraege sind feldidentisch — kein Drift-Rauschen
            # im Delta, nur echte "added"-Zugaenge.
            assert risk == now_risks[rid]

    def test_prev_epics_reference_only_prev_themes(self) -> None:
        prev = _build(prev=True)
        theme_ids = {t.theme_id for t in prev["themes"].themes}
        assert all(e.theme in theme_ids for e in prev["themes"].epics)


class TestAnchorInvariants:
    """Die Grundmenge darf die erzählten Geschichten nie verwässern."""

    @pytest.fixture(scope="class")
    def large(self) -> dict[str, object]:
        return _build(scale=SCALE_L)

    def test_no_aging_no_violated_no_overdue(self, large) -> None:
        assert all((REF - r.status_since).days <= 30
                   for r in large["risks"].risks)
        assert all(n.status != STATUS_VIOLATED for n in large["nfr"].nfrs)
        assert all(not (i.status == RUNWAY_GAP and i.needed_by
                        and i.needed_by < REF)
                   for i in large["nfr"].runway)
        open_assumptions = [e for e in large["decisions"].entries
                            if e.kind == KIND_ASSUMPTION
                            and e.status == ASSUMPTION_OPEN]
        assert all(e.review_by and e.review_by > REF
                   for e in open_assumptions)

    def test_no_blocked_no_breached_no_survivors(self, large) -> None:
        assert all(d.status != DEP_BLOCKED
                   for d in large["dependencies"].dependencies)
        assert all(slo_status(r) != "breached" for r in large["slo"].records)
        assert all(p.conferences <= 2
                   for p in large["flow_problems"].problems)

    def test_no_orphans_no_zombies_no_drift(self, large) -> None:
        themes: ThemesRegister = large["themes"]
        assert orphan_theme_ids(themes) == set()
        assert zombie_epics(themes) == []
        assert all(set(c.arts) <= set(ARTS)
                   for c in large["capabilities"].capabilities)
        assert all(d.from_art in ARTS and d.to_art in ARTS
                   for d in large["dependencies"].dependencies)
        assert all(e.train in ARTS for e in themes.epics)

    def test_owners_are_teams_never_persons(self, large) -> None:
        owners = ({r.owner for r in large["risks"].risks}
                  | {n.owner for n in large["nfr"].nfrs}
                  | {p.owner for p in large["flow_problems"].problems})
        assert owners
        for owner in owners:
            assert "Team" in owner or "Gilde" in owner, owner

    def test_supersedes_stays_an_anchor_story(self, large) -> None:
        assert all(not e.supersedes for e in large["decisions"].entries)


class TestScaleProfilesShape:
    def test_profiles_cover_all_scales(self) -> None:
        assert set(SCALE_PROFILES) == {SCALE_S, SCALE_M, SCALE_L}
