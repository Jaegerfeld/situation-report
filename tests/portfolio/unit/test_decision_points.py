# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       14.10.2026
# Geändert:       14.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Tests des Wecker-Registers (D4 Schritt 1): Parsen und Fehlerpfade,
#   Auswertung aller vier Zustände (ausgelöst, unterschwellig, nicht
#   vereinbart, nicht berechenbar), relative Veränderung mit Vorstand,
#   Registerzählungen im Fakten-Index, P4-Druck als Zusatzpfad, Rendering mit
#   Legende, Protokoll, Collector/Report/Snapshot/Delta am Szenario, CLI,
#   Config-Roundtrip, Datenquellen-Dialog.
# =============================================================================

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import pytest

from portfolio.decision_points import (
    NOTE_NO_PATH,
    NOTE_NO_PREV,
    PRESSURE_PATH,
    count_by_status,
    evaluate_points,
    points_to_markdown,
)
from portfolio.decision_points_config import (
    DP_BELOW,
    DP_NOT_AGREED,
    DP_NOT_COMPUTABLE,
    DP_TRIGGERED,
    DecisionPoint,
    load_decision_points,
    parse_decision_points,
    save_decision_points,
)
from portfolio.facts import build_fact_index
from portfolio.snapshot import Snapshot, load_snapshot
from portfolio.solution_config import Member, SolutionConfig, parse_solution_config, to_dict
from portfolio.summary import _OVERDUE_COLOR, render_decision_points_html

REF = date(2026, 10, 13)


def _snap(open_=40, items=100, prev=False) -> Snapshot:
    return Snapshot(name="S", kind="solution", as_of=date(2026, 9, 29) if prev else REF, created="x",
                    target_ct=90, total={"label": "S", "items": items, "completed": items - open_,
                                         "open": open_, "median_ct": 12.0, "p85_ct": 30.0},
                    units=[{"label": "ART A", "items": items, "open": open_, "p85_ct": 35.0}],
                    governance={"dependencies": [
                        {"id": "D-1", "title": "x", "status": "blocked", "solution": "S"},
                        {"id": "D-2", "title": "y", "status": "at_risk", "solution": "S"}]})


class TestParse:
    def test_roundtrip_and_defaults(self, tmp_path) -> None:
        reg = parse_decision_points({"schema": 1, "points": [
            {"id": "DP-1", "title": "P85", "metric": "S1/units(ART A).p85_ct", "threshold": "30",
             "question": "Q?", "reaction": "R", "team": "ART A", "agreed_on": "2026-09-30"},
            {"id": "DP-2", "title": "open growth", "metric": "D/total.open", "op": ">=", "threshold": 10,
             "unit": "%"},
            {"id": "DP-3", "title": "no threshold yet", "metric": "S1/total.median_ct", "owner": "Team X"}]})
        a, b, c = reg.points
        assert a.op == ">=" and a.threshold == 30.0 and a.agreed and a.agreed_on == date(2026, 9, 30)
        assert b.unit == "%" and c.threshold is None and not c.agreed and c.team == "Team X"
        path = tmp_path / "dp.json"
        save_decision_points(path, reg)
        assert load_decision_points(path) == reg and json.loads(path.read_text(encoding="utf-8"))["schema"] == 1

    @pytest.mark.parametrize("entry,match", [
        ({"id": "", "title": "T", "metric": "S1/total.items"}, "non-empty 'id'"),
        ({"id": "P", "title": "", "metric": "S1/total.items"}, "'title' and 'metric'"),
        ({"id": "P", "title": "T", "metric": "total.items"}, "fact path"),
        ({"id": "P", "title": "T", "metric": "S1/total.items", "op": "=="}, "'op'"),
        ({"id": "P", "title": "T", "metric": "S1/total.items", "threshold": "viel"}, "number"),
        ({"id": "P", "title": "T", "metric": "S1/total.items", "unit": "d"}, "'unit'"),
        ({"id": "P", "title": "T", "metric": "S1/total.items", "agreed_on": "gestern"}, "YYYY-MM-DD"),
    ])
    def test_rejects(self, entry, match) -> None:
        with pytest.raises(ValueError, match=match):
            parse_decision_points({"points": [entry]})
        with pytest.raises(ValueError, match="Duplicate"):
            parse_decision_points({"points": [{"id": "P", "title": "T", "metric": "S1/a.b"},
                                              {"id": "P", "title": "T", "metric": "S1/a.b"}]})


class TestEvaluate:
    def test_four_states_and_order(self) -> None:
        idx = build_fact_index(_snap())
        points = [
            DecisionPoint("DP-nc", "needs prev", "D/total.open", ">=", 10.0, "%"),
            DecisionPoint("DP-na", "not agreed", "S1/total.median_ct"),
            DecisionPoint("DP-b", "below", "S1/governance.dependencies.count(blocked)", ">=", 2.0),
            DecisionPoint("DP-t", "triggered", "S1/units(ART A).p85_ct", ">=", 30.0),
            DecisionPoint("DP-missing", "no such path", "S1/units(ART Z).open", "<", 1.0),
        ]
        results = evaluate_points(points, idx)
        assert [r.point.point_id for r in results] == ["DP-t", "DP-b", "DP-na", "DP-nc", "DP-missing"]
        by_id = {r.point.point_id: r for r in results}
        assert by_id["DP-t"].status == DP_TRIGGERED and by_id["DP-t"].shown_value == "35"
        assert by_id["DP-b"].status == DP_BELOW and by_id["DP-b"].value == 1.0
        assert by_id["DP-na"].status == DP_NOT_AGREED and by_id["DP-na"].shown_threshold == "-"
        assert by_id["DP-nc"].status == DP_NOT_COMPUTABLE and by_id["DP-nc"].note == NOTE_NO_PREV
        assert by_id["DP-missing"].note == NOTE_NO_PATH
        assert count_by_status(results) == {"triggered": 1, "below": 1, "not_agreed": 1, "not_computable": 2}

    def test_relative_change_with_prev_and_pressure_extra(self) -> None:
        idx = build_fact_index(_snap(open_=46), prev=_snap(open_=40, prev=True))
        pct = DecisionPoint("DP-pct", "open +10 %", "D/total.open", ">=", 10.0, "%")
        abs_ = DecisionPoint("DP-abs", "open +5", "D/total.open", ">=", 5.0)
        press = DecisionPoint("DP-p4", "pressure", PRESSURE_PATH, ">=", 12.0)
        res = {r.point.point_id: r for r in evaluate_points([pct, abs_, press], idx, {PRESSURE_PATH: 14.0})}
        assert res["DP-pct"].status == DP_TRIGGERED and res["DP-pct"].shown_value == "15 %"
        assert res["DP-abs"].status == DP_TRIGGERED and res["DP-abs"].value == 6.0
        assert res["DP-p4"].status == DP_TRIGGERED and res["DP-p4"].shown_threshold == ">= 12"
        assert evaluate_points([press], idx)[0].status == DP_NOT_COMPUTABLE

    def test_count_facts_in_the_index(self) -> None:
        idx = build_fact_index(_snap())
        assert idx.by_path["S1/governance.dependencies.count"].value == "2"
        assert idx.by_path["S1/governance.dependencies.count(blocked)"].value == "1"


class TestRenderAndProtocol:
    def test_html_shades_triggered_and_carries_legend(self) -> None:
        idx = build_fact_index(_snap())
        results = evaluate_points([DecisionPoint("DP-t", "P85", "S1/units(ART A).p85_ct", ">=", 30.0,
                                                 question="Cut scope?", reaction="Proposal"),
                                   DecisionPoint("DP-na", "median", "S1/total.median_ct")], idx)
        html = render_decision_points_html([("S", r) for r in results], lang="de")
        assert "2 Wecker · 1 ausgelöst · 0 unterschwellig · 1 nicht vereinbart · 0 nicht berechenbar" in html
        assert f"background:{_OVERDUE_COLOR};font-weight:700'>ausgelöst" in html and "Cut scope?" in html
        assert "Ohne Schwelle weckt kein Wecker" in html
        assert render_decision_points_html([], lang="en") == ""

    @pytest.mark.parametrize("lang", ["de", "en", "ro", "pt", "fr"])
    def test_every_language(self, lang) -> None:
        idx = build_fact_index(_snap())
        results = evaluate_points([DecisionPoint("DP-1", "x", "S1/total.items", ">=", 1.0)], idx)
        assert "<table" in render_decision_points_html([("S", r) for r in results], lang=lang)

    def test_markdown_protocol(self) -> None:
        idx = build_fact_index(_snap())
        results = evaluate_points([DecisionPoint("DP-1", "x", "S1/total.items", ">=", 1.0)], idx)
        md = points_to_markdown(results, idx, "de")
        assert md.startswith("# Entscheidungspunkte — S (2026-10-13)") and "| DP-1 x |" in md and "ausgelöst" in md
        assert "Decision points" in points_to_markdown(results, idx, "en")


class TestConfigAndGui:
    def test_config_field(self) -> None:
        cfg = SolutionConfig(name="S", members=[Member(name="A", issue_times="a.xlsx")],
                             decision_points="registers/decision_points.json")
        assert parse_solution_config(to_dict(cfg)) == cfg
        assert "decision_points" not in to_dict(SolutionConfig(name="S", members=[]))

    def test_dialog_knows_the_register(self, tmp_path) -> None:
        from portfolio.gui import _T, REGISTER_FIELDS, fill_from_datenraum
        assert "decision_points" in REGISTER_FIELDS
        for lang in ("de", "en", "ro", "pt", "fr"):
            assert "reg_decision_points" in _T[lang]
        (tmp_path / "registers").mkdir()
        (tmp_path / "registers" / "decision_points.json").write_text("{}", encoding="utf-8")
        assert fill_from_datenraum(tmp_path) == {
            "decision_points": str((tmp_path / "registers" / "decision_points.json").resolve())}


@pytest.fixture(scope="module")
def demo(tmp_path_factory):
    from testdata_generator.scenario import build_portfolio_scenario
    return build_portfolio_scenario(tmp_path_factory.mktemp("demo"), seed=42, reference=REF,
                                    log=lambda m: None)


class TestScenarioStory:
    def test_alpha_points_in_report_snapshot_and_delta(self, demo) -> None:
        from portfolio.aggregator import evaluate_decision_points, render_pooled_html
        from portfolio.delta import compute_delta
        from portfolio.solution_config import load_solution_config
        cfg = load_solution_config(demo["solution_alpha"])
        res = {r.point.point_id: r for _, r in evaluate_decision_points(cfg, log=lambda m: None)}
        assert res["DP-A1"].status == DP_TRIGGERED and res["DP-A3"].status == DP_BELOW
        assert res["DP-A4"].status == DP_NOT_AGREED and res["DP-A2"].status == DP_NOT_COMPUTABLE
        html = render_pooled_html(cfg, log=lambda *_: None, lang="de")
        assert "Entscheidungspunkte (Wecker-Register)" in html and "DP-A1" in html
        prev, now = load_snapshot(demo["snapshot_prev"]), load_snapshot(demo["snapshot_now"])
        assert {e["id"] for e in now.governance["decision_points"]} >= {"DP-A1", "DP-B1"}
        assert all("owner" not in e for e in now.governance["decision_points"])
        # the portfolio stand cannot resolve ART-level paths: honest "not computable"
        a1 = next(e for e in now.governance["decision_points"] if e["id"] == "DP-A1")
        assert a1["status"] == DP_NOT_COMPUTABLE
        assert "decision_points" in compute_delta(prev, now).governance

    def test_cli_alarms_with_prev_makes_relative_points_computable(self, demo, tmp_path) -> None:
        from portfolio.cli import _run_alarms, build_parser
        assert build_parser().parse_args(["c.json", "--alarms", "w.md"]).alarms == Path("w.md")
        ns = argparse.Namespace(config=Path(demo["solution_alpha"]), alarms=tmp_path / "w.md",
                                ask_snapshot=None, since_snapshot=Path(demo["snapshot_prev"]),
                                as_of=REF, target_ct=90, llm_lang="de")
        _run_alarms(ns)
        md = (tmp_path / "w.md").read_text(encoding="utf-8")
        assert "DP-A1" in md and "ausgelöst" in md
        # the prev stand is the portfolio's: S0/total.open exists, so DP-A2 computes a relative change
        assert "DP-A2" in md and "nicht berechenbar (needs a previous stand" not in md.split("DP-A2")[1].split("\n")[0]

    def test_register_file_written(self, demo) -> None:
        reg = load_decision_points(demo["points_alpha"])
        assert [p.point_id for p in reg.points] == ["DP-A1", "DP-A2", "DP-A3", "DP-A4"]
        assert all(p.team for p in reg.points)
