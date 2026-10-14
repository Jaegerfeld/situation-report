# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       14.10.2026
# Geändert:       14.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Tests der Auffälligkeits-Hinweise (D4 Schritt 2): Reihe laden (Fremd-
#   dateien überspringen, je as_of ein Stand), zu wenige Stände, Median/MAD,
#   MAD 0 schweigt, Begrenzung, Daten und Texte ausgeschlossen, Markdown.
#   Dazu die KI-Erklärschicht: relevante Fakten je Pfadfamilie, Contract,
#   zitierte Erklärung besteht, unzitierte wird verworfen (Wecker bleibt),
#   Mock antwortet mit dem Unbekannt-Satz, CLI --history/--narrate,
#   Einseiter mit ausgelöstem Wecker.
# =============================================================================

from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from llm.base import DEPLOYMENT_MOCK, LlmResult
from llm.guard import UNKNOWN_ANSWERS
from portfolio.alarm_explain import (
    explain_contract,
    explain_triggered,
    explanations_to_markdown,
    relevant_facts,
)
from portfolio.anomalies import (
    HINT_LIMIT,
    MIN_STANDS,
    detect_anomalies,
    hints_to_markdown,
    load_series,
    numeric_facts,
)
from portfolio.decision_points import evaluate_points
from portfolio.decision_points_config import DecisionPoint
from portfolio.facts import build_fact_index
from portfolio.snapshot import Snapshot, save_snapshot

REF = date(2026, 10, 13)


def _snap(day: int, open_: int, p85: float = 30.0, blocked: int = 1) -> Snapshot:
    deps = [{"id": f"D-{i}", "title": "x", "status": "blocked" if i < blocked else "on_track", "solution": "S"}
            for i in range(3)]
    return Snapshot(name="S", kind="solution", as_of=REF - timedelta(days=day), created="x", target_ct=90,
                    total={"label": "S", "items": 100, "completed": 100 - open_, "open": open_,
                           "median_ct": 10.0, "p85_ct": p85},
                    units=[{"label": "ART A", "items": 100, "open": open_, "p85_ct": p85}],
                    governance={"dependencies": deps,
                                "risks": [{"id": "R-1", "title": "t", "roam": "owned", "since": "2026-09-01",
                                           "solution": "S"}]})


class TestSeries:
    def test_load_series_skips_foreign_files_and_sorts(self, tmp_path) -> None:
        for day, open_ in ((28, 40), (7, 46), (21, 41), (14, 42)):
            save_snapshot(tmp_path / f"s{day}.json", _snap(day, open_))
        (tmp_path / "notes.json").write_text('{"hello": 1}', encoding="utf-8")
        (tmp_path / "broken.json").write_text("{", encoding="utf-8")
        series = load_series(tmp_path)
        assert [s.as_of for s in series] == sorted(s.as_of for s in series) and len(series) == 4

    def test_numeric_facts_exclude_dates_and_texts(self) -> None:
        facts = numeric_facts(build_fact_index(_snap(0, 40)))
        assert "S1/total.open" in facts and "S1/governance.dependencies.count(blocked)" in facts
        assert not any(p.endswith(".since") or p.endswith(".title") for p in facts)


class TestDetect:
    def test_too_few_stands(self) -> None:
        rep = detect_anomalies([_snap(14, 40), _snap(7, 41), _snap(0, 90)])
        assert not rep.enough and rep.hints == [] and MIN_STANDS == 4
        assert "keine Statistik" in hints_to_markdown(rep, "de")

    def test_outlier_against_history_mad_zero_silent(self) -> None:
        series = [_snap(28, 40, 30.0), _snap(21, 42, 30.0), _snap(14, 41, 30.0), _snap(7, 43, 30.0),
                  _snap(0, 80, 30.0)]
        rep = detect_anomalies(series)
        assert rep.enough and rep.latest_as_of == REF.isoformat()
        paths = [h.path for h in rep.hints]
        assert "S1/total.open" in paths and "S1/units(ART A).open" in paths
        assert not any("p85" in p for p in paths)            # constant history: MAD 0, silent
        assert rep.hints[0].score >= rep.hints[-1].score          # strongest first
        top = next(h for h in rep.hints if h.path == "S1/total.open")
        assert top.median == 41.5 and top.prior_min == 40 and top.prior_max == 43 and top.stands == 4
        md = hints_to_markdown(rep, "de")
        assert "Kandidaten für Wecker" in md and "`S1/total.open`" in md and "keine Alarme" in md

    def test_limit_counts_the_rest(self) -> None:
        base = [_snap(28, 40), _snap(21, 41), _snap(14, 42), _snap(7, 43)]
        wild = _snap(0, 300, p85=90.0, blocked=3)
        wild.total["items"] = 900; wild.total["completed"] = 600; wild.total["median_ct"] = 50.0
        wild.units[0].update({"items": 900, "p85_ct": 90.0})
        for s in base:
            s.total["items"] = 100 + s.as_of.day % 3; s.total["median_ct"] = 10.0 + s.as_of.day % 2
            s.units[0]["p85_ct"] = 30.0 + s.as_of.day % 2
        rep = detect_anomalies(base + [wild], limit=2)
        assert len(rep.hints) == 2 and rep.more >= 1 and HINT_LIMIT == 10
        assert rep.hints[0].score >= rep.hints[1].score


class TestExplain:
    def _result(self):
        idx = build_fact_index(_snap(0, 40, p85=35.0), prev=_snap(14, 30, p85=20.0))
        point = DecisionPoint("DP-1", "P85 of ART A", "S1/units(ART A).p85_ct", ">=", 30.0,
                              question="Cut scope?")
        return evaluate_points([point], idx)[0], idx

    def test_relevant_facts_and_contract(self) -> None:
        r, idx = self._result()
        facts = relevant_facts(r, idx)
        paths = [f.path for f in facts]
        assert paths[0] == "S1/units(ART A).p85_ct" and "S1/total.open" in paths and "S0/units(ART A).p85_ct" in paths
        assert not any("governance" in p for p in paths)
        c = explain_contract(r, facts, idx)
        assert c.startswith("# Alarm-Contract - S (2026-10-13)\nDecision point: DP-1 P85 of ART A\nMetric: S1/units(ART A).p85_ct\nValue: 35")
        assert "- [S1/units(ART A).p85_ct]" in c
        # a dependency point draws the dependency register
        dep = DecisionPoint("DP-2", "blocked", "S1/governance.dependencies.count(blocked)", ">=", 1.0)
        dr = evaluate_points([dep], idx)[0]
        assert any(f.path.startswith("S1/governance.dependencies") for f in relevant_facts(dr, idx))

    def test_cited_passes_uncited_discarded_point_stands(self, tmp_path) -> None:
        r, idx = self._result()
        answers = iter(["P85 liegt bei 35 Tagen [S1/units(ART A).p85_ct], im Vorstand bei 20 [S0/units(ART A).p85_ct].",
                        "Das Team ist überlastet und sollte entlastet werden."])

        class Prov:
            provider_id = "cyc"; deployment_class = DEPLOYMENT_MOCK; default_model = "cyc-1"

            def complete(self, s, p, c):
                return LlmResult(text=next(answers), provider_id="cyc", model="cyc-1",
                                 deployment_class=DEPLOYMENT_MOCK)
        with patch("llm.narrate.discover_providers", return_value={"cyc": Prov()}):
            good = explain_triggered([r], idx, provider_id="cyc", audit_path=tmp_path / "a.jsonl",
                                     log=lambda m: None)["DP-1"]
            bad = explain_triggered([r], idx, provider_id="cyc", audit_path=tmp_path / "a.jsonl",
                                    log=lambda m: None)["DP-1"]
        assert good.ok and good.text.startswith("P85 liegt bei 35") and "KI-formulierter" in good.banner
        assert not bad.ok and bad.rejected.startswith("citation guard: uncited")
        records = [json.loads(line) for line in (tmp_path / "a.jsonl").read_text(encoding="utf-8").splitlines()]
        assert [x["guard_passed"] for x in records] == [True, True, False] and records[-1]["purpose"] == "d4_anomaly"
        md = explanations_to_markdown([r], {"DP-1": bad}, "de")
        assert "Erklärung verworfen" in md and "DP-1" in md

    def test_mock_answers_unknown_and_non_triggered_skipped(self) -> None:
        r, idx = self._result()
        below = evaluate_points([DecisionPoint("DP-9", "x", "S1/total.open", ">=", 999.0)], idx)[0]
        out = explain_triggered([r, below], idx, provider_id="mock", log=lambda m: None)
        assert list(out) == ["DP-1"] and out["DP-1"].text == UNKNOWN_ANSWERS["de"]
        assert "keine Erklärung angefordert" in explanations_to_markdown([r], {}, "de")


@pytest.fixture(scope="module")
def demo(tmp_path_factory):
    from testdata_generator.scenario import build_portfolio_scenario
    return build_portfolio_scenario(tmp_path_factory.mktemp("demo"), seed=42, reference=REF,
                                    log=lambda m: None)


class TestCliAndOnepager:
    def test_alarms_with_history_and_narrate(self, demo, tmp_path) -> None:
        from portfolio.cli import _run_alarms, build_parser
        from portfolio.snapshot import load_snapshot
        assert build_parser().parse_args(["c.json", "--alarms", "w.md", "--history", "h"]).history == Path("h")
        hist = tmp_path / "hist"
        base = load_snapshot(demo["snapshot_now"])
        for i in range(4):
            s = Snapshot(name=base.name, kind=base.kind, as_of=REF - timedelta(days=7 * (4 - i)),
                         created="x", target_ct=90, total=dict(base.total, open=base.total["open"] - 10 + i),
                         units=[dict(u) for u in base.units], sources=[], governance={})
            save_snapshot(hist / f"s{i}.json", s)
        ns = argparse.Namespace(config=Path(demo["solution_alpha"]), alarms=tmp_path / "w.md", ask_snapshot=None,
                                since_snapshot=None, as_of=REF, target_ct=90, llm_lang="de", narrate="mock",
                                llm_model=None, llm_base_url=None, history=hist)
        _run_alarms(ns)
        md = (tmp_path / "w.md").read_text(encoding="utf-8")
        assert "## Erklärungen zu ausgelösten Weckern" in md and "### DP-A1" in md and UNKNOWN_ANSWERS["de"] in md
        assert "## Auffälligkeits-Hinweise" in md and "Stände bis" in md

    def test_onepager_leads_with_triggered_points(self, demo) -> None:
        from portfolio.onepager import build_onepager
        from portfolio.solution_config import load_solution_config
        op = build_onepager(load_solution_config(demo["solution_alpha"]), "de", reference=REF,
                            log=lambda m: None)
        assert op.bluf.startswith("1 Wecker ausgelöst")
        assert any("Wecker ausgelöst: DP-A1" in line for line in op.cells["flow"]["q3"].decide)
        assert any(s.startswith("decision_points: 4 (1 triggered)") for s in op.sources)
