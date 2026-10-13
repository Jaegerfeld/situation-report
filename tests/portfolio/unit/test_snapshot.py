# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       12.10.2026
# Geändert:       12.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Nebenbefund aus D8: Der D1-Contract las Flussprobleme und SLOs aus dem
#   Snapshot, der sie nie befüllte. Diese Tests sichern, dass der Snapshot
#   beide Register trägt (ohne Owner/Melder, SLO-Status zentral abgeleitet),
#   dass der D1-Contract sie zählt und dass das Delta sie vergleicht —
#   inklusive des Konferenzen-Zählers als Verschlechterung.
# =============================================================================

from __future__ import annotations

from datetime import date
from unittest.mock import patch

from portfolio.delta import compute_delta, delta_to_markdown
from portfolio.exec_summary import summary_to_markdown
from portfolio.flow_problems_config import FlowProblem
from portfolio.snapshot import Snapshot, _governance_dict
from portfolio.solution_config import SolutionConfig
from sources.base import SloRecord

NONE = lambda *a, **k: []  # noqa: E731
AS_OF = date(2026, 10, 12)


def _governance() -> dict:
    cfg = SolutionConfig(name="Demo")
    flow = [("Demo", FlowProblem("FP-1", "Shared test env", "open", ["VS A", "VS B"],
                                 source="RTE Sync", owner="Team Platform",
                                 raised_on=date(2026, 6, 1), conferences=3,
                                 follow_up_pi="PI 7")),
            ("Demo", FlowProblem("FP-2", "Release calendar", "resolved", ["VS A"],
                                 owner="Team Release"))]
    slos = [("Demo", SloRecord(service="Order Sync API", slo="p95 < 200 ms",
                               target_pct=99.9, sli_pct=99.95)),
            ("Demo", SloRecord(service="Search", slo="availability",
                               target_pct=99.9, sli_pct=98.0))]
    with patch("portfolio.snapshot._collect_flow_problems", return_value=flow), \
         patch("portfolio.snapshot._collect_slo", return_value=slos), \
         patch("portfolio.snapshot._collect_risks", NONE), \
         patch("portfolio.snapshot._collect_dependencies", NONE), \
         patch("portfolio.snapshot._collect_nfr", return_value=([], [])), \
         patch("portfolio.snapshot._collect_capabilities", NONE), \
         patch("portfolio.snapshot._collect_decisions", NONE), \
         patch("portfolio.snapshot._collect_themes", return_value=([], [])):
        return _governance_dict(cfg, log=lambda m: None)


class TestGovernanceRegisters:
    def test_eight_registers(self) -> None:
        gov = _governance()
        assert set(gov) == {"risks", "dependencies", "nfr", "runway", "capabilities",
                            "decisions", "epics", "flow_problems", "slo", "solution_areas"}

    def test_flow_problems_without_owner_or_raiser(self) -> None:
        fp = _governance()["flow_problems"]
        assert [e["id"] for e in fp] == ["FP-1", "FP-2"]
        first = fp[0]
        assert first["status"] == "open" and first["conferences"] == 3
        assert first["value_streams"] == ["VS A", "VS B"]
        assert first["raised_on"] == "2026-06-01" and first["follow_up_pi"] == "PI 7"
        assert first["solution"] == "Demo"
        assert "owner" not in first and "source" not in first

    def test_slo_status_is_derived_centrally(self) -> None:
        slo = _governance()["slo"]
        assert [(e["id"], e["status"]) for e in slo] == [("Order Sync API", "met"),
                                                         ("Search", "breached")]
        assert slo[0]["title"] == "p95 < 200 ms" and slo[0]["target_pct"] == 99.9


def _snap(as_of: date, governance: dict) -> Snapshot:
    return Snapshot(name="Demo", kind="solution", as_of=as_of, created="x", target_ct=90,
                    total={"label": "Demo", "items": 1, "completed": 1, "open": 0,
                           "median_ct": 1.0, "p85_ct": 1.0, "p95_ct": 1.0,
                           "target_ct_pct": 100.0, "median_lt": 1.0},
                    governance=governance)


class TestExecSummaryContract:
    def test_counts_flow_problems_and_slos(self) -> None:
        snap = _snap(AS_OF, _governance())
        md = summary_to_markdown(snap)
        assert "- flow_problems: 2 (open 1, resolved 1)" in md
        assert "- slo: 2 services" in md
        assert "Team Platform" not in md and "RTE Sync" not in md


class TestDeltaKnowsTheNewRegisters:
    def test_survivor_and_breach_count_as_worsening(self) -> None:
        prev = _snap(date(2026, 9, 28), {
            "flow_problems": [{"id": "FP-1", "title": "Shared test env", "status": "open",
                               "conferences": 2, "solution": "Demo"}],
            "slo": [{"id": "Search", "title": "availability", "status": "met",
                     "solution": "Demo"}]})
        now = _snap(AS_OF, {
            "flow_problems": [{"id": "FP-1", "title": "Shared test env", "status": "open",
                               "conferences": 3, "solution": "Demo"}],
            "slo": [{"id": "Search", "title": "availability", "status": "breached",
                     "solution": "Demo"}]})
        delta = compute_delta(prev, now)
        fp = delta.governance["flow_problems"].changed
        assert len(fp) == 1 and fp[0].fields == {"conferences": (2, 3)} and fp[0].worsened
        slo = delta.governance["slo"].changed
        assert len(slo) == 1 and slo[0].fields == {"status": ("met", "breached")}
        assert slo[0].worsened
        md = delta_to_markdown(delta)
        assert "## Flow problems (impediment backlog)" in md and "## SLOs" in md

    def test_counter_below_threshold_is_a_change_but_no_worsening(self) -> None:
        prev = _snap(date(2026, 9, 28), {"flow_problems": [
            {"id": "FP-1", "title": "x", "status": "open", "conferences": 1, "solution": "D"}]})
        now = _snap(AS_OF, {"flow_problems": [
            {"id": "FP-1", "title": "x", "status": "open", "conferences": 2, "solution": "D"}]})
        change = compute_delta(prev, now).governance["flow_problems"].changed[0]
        assert change.fields == {"conferences": (1, 2)} and not change.worsened

    def test_old_snapshots_without_the_registers_still_compare(self) -> None:
        prev = _snap(date(2026, 9, 28), {"risks": []})
        now = _snap(AS_OF, {"risks": [], "flow_problems": [
            {"id": "FP-9", "title": "new", "status": "open", "conferences": 1, "solution": "D"}]})
        delta = compute_delta(prev, now)
        assert [e["id"] for e in delta.governance["flow_problems"].added] == ["FP-9"]
        assert delta.governance["slo"].empty
