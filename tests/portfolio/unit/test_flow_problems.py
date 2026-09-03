# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für den Flussproblem-Backlog (B6, VSC-1): Parsen/Roundtrip,
#   abgeleitetes Cross-VS-Flag, Survivor-Regel (offen ∧ ≥3 Konferenzen),
#   Rendering (Survivor zuerst und rot, Cross-Markierung, Titelzähler),
#   Collector und die Konferenzmappe (Sektionsreihenfolge der Inputs).
# =============================================================================

from __future__ import annotations

from datetime import date

import pytest

from portfolio.aggregator import _collect_flow_problems
from portfolio.flow_problems_config import (
    FlowProblem,
    FlowProblemRegister,
    load_flow_problems,
    parse_flow_problems,
    save_flow_problems,
)
from portfolio.solution_config import Member, SolutionConfig
from portfolio.summary import _OVERDUE_COLOR, render_flow_problems_html

REF = date(2025, 6, 30)


def _problem(pid: str = "FP-1", **kwargs) -> dict:
    base = {"id": pid, "title": "Test problem", "status": "open",
            "value_streams": ["ART A"]}
    base.update(kwargs)
    return base


class TestParse:
    def test_minimal_and_derived_flags(self) -> None:
        register = parse_flow_problems({"problems": [
            _problem(), _problem("FP-2", value_streams=["A", "B"],
                                 conferences=3)]})
        single, multi = register.problems
        assert not single.cross_vs and not single.survived
        assert multi.cross_vs and multi.survived

    def test_survivor_needs_unresolved_status(self) -> None:
        resolved = parse_flow_problems({"problems": [
            _problem(status="resolved", conferences=5)]}).problems[0]
        assert not resolved.survived
        committed = parse_flow_problems({"problems": [
            _problem(status="committed", conferences=3)]}).problems[0]
        assert committed.survived

    def test_rejects_structural_errors(self) -> None:
        with pytest.raises(ValueError, match="JSON object"):
            parse_flow_problems([])
        with pytest.raises(ValueError, match="'problems' list"):
            parse_flow_problems({"problems": "x"})
        with pytest.raises(ValueError, match="'id'"):
            parse_flow_problems({"problems": [_problem(pid=" ")]})
        with pytest.raises(ValueError, match="Duplicate"):
            parse_flow_problems({"problems": [_problem(), _problem()]})
        with pytest.raises(ValueError, match="unknown status"):
            parse_flow_problems({"problems": [_problem(status="parked")]})
        with pytest.raises(ValueError, match="value_streams"):
            parse_flow_problems({"problems": [_problem(value_streams=[])]})
        with pytest.raises(ValueError, match="raised_on"):
            parse_flow_problems({"problems": [_problem(raised_on="gestern")]})
        with pytest.raises(ValueError, match=">= 1"):
            parse_flow_problems({"problems": [_problem(conferences=0)]})

    def test_roundtrip(self, tmp_path) -> None:
        register = FlowProblemRegister(problems=[
            FlowProblem("FP-1", "Env provisioning", "open",
                        value_streams=["A", "B"], source="VSC",
                        owner="System Team", raised_on=date(2025, 2, 1),
                        conferences=3,
                        resolution_commitment="Automate", follow_up_pi="PI 5",
                        notes="n"),
        ])
        path = tmp_path / "flow.json"
        save_flow_problems(path, register)
        assert load_flow_problems(path) == register


class TestRendering:
    def _entries(self):
        return [
            ("Sol A", FlowProblem("FP-2", "Fresh issue", "open",
                                  value_streams=["A"],
                                  raised_on=REF, conferences=1)),
            ("Sol A", FlowProblem("FP-1", "Survivor issue", "open",
                                  value_streams=["A", "B"],
                                  raised_on=date(2025, 1, 1),
                                  conferences=4)),
            ("Sol B", FlowProblem("FP-9", "Solved", "resolved",
                                  value_streams=["C"], conferences=2)),
        ]

    def test_survivor_sorts_first_with_red_counter_and_cross_flag(self) -> None:
        html = render_flow_problems_html(self._entries(), reference=REF)
        assert html.index("Survivor issue") < html.index("Fresh issue")
        survivor_row = next(r for r in html.split("<tr>")
                            if "Survivor issue" in r)
        assert _OVERDUE_COLOR in survivor_row
        assert "CROSS: A, B" in survivor_row
        assert "3 problems (2 unresolved, 1 cross-VS, 1 survived" in html
        assert "<th>Solution</th>" in html

    def test_empty_renders_nothing(self) -> None:
        assert render_flow_problems_html([]) == ""


class TestCollectorAndConference:
    def test_collector_labels_and_skips_broken(self, tmp_path) -> None:
        good = tmp_path / "flow.json"
        save_flow_problems(good, FlowProblemRegister(problems=[
            FlowProblem("FP-1", "T", "open", value_streams=["A"])]))
        cfg = SolutionConfig(
            name="Sol", members=[Member(name="A", issue_times="x.xlsx")],
            flow_problems=str(good))
        entries = _collect_flow_problems(cfg, log=lambda m: None)
        assert [(s, p.problem_id) for s, p in entries] == [("Sol", "FP-1")]

        bad = tmp_path / "bad.json"
        bad.write_text("{oops", encoding="utf-8")
        cfg_bad = SolutionConfig(
            name="Sol", members=[Member(name="A", issue_times="x.xlsx")],
            flow_problems=str(bad))
        warnings: list[str] = []
        assert _collect_flow_problems(cfg_bad, log=warnings.append) == []
        assert any("skipped" in w for w in warnings)
