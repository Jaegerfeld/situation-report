# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       14.10.2026
# Geändert:       14.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Tests des Noise-Audits (D7): Varianten (Lauf 1 unverändert, eigene vor
#   festen Rahmen, Wiederholung bei großem n), Analyse einer Antwort, Maße
#   (Konsistenz, Kern, Streuung, Zahlen-Abweichung, Quoten) mit gesteuerten
#   Antworten, verworfene Läufe zählen, Export verboten, Protokoll-Datei,
#   Stabs-Einschätzungen, CLI-Dispatch, GUI-Texte.
# =============================================================================

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from llm.base import DEPLOYMENT_MOCK, LlmResult
from llm.guard import UNKNOWN_ANSWERS
from portfolio.facts import FactIndex, build_fact_index
from portfolio.noise import (
    DEFAULT_RUNS,
    NoiseReport,
    Run,
    analyse_answer,
    noise_to_markdown,
    question_variants,
    read_variants,
    read_views,
    run_noise,
    run_noise_audit,
)
from portfolio.snapshot import load_snapshot
from portfolio.solution_config import load_solution_config

REF = date(2026, 10, 13)


@pytest.fixture(scope="module")
def demo(tmp_path_factory):
    from testdata_generator.scenario import build_portfolio_scenario
    return build_portfolio_scenario(tmp_path_factory.mktemp("demo"), seed=42, reference=REF,
                                    log=lambda m: None)


@pytest.fixture(scope="module")
def alpha(demo):
    return load_solution_config(demo["solution_alpha"]), load_snapshot(demo["snapshot_now"])


def _cycling_provider(answers: list[str]):
    class Cycling:
        provider_id = "cyc"
        deployment_class = DEPLOYMENT_MOCK
        default_model = "cyc-1"
        calls = 0

        def complete(self, system, prompt, config):
            text = answers[self.calls % len(answers)]
            self.calls += 1
            return LlmResult(text=text, provider_id="cyc", model="cyc-1",
                             deployment_class=DEPLOYMENT_MOCK, endpoint="mock://cyc")
    return Cycling()


class TestVariants:
    def test_first_unchanged_then_own_then_frames_then_repeat(self) -> None:
        v = question_variants("Was ist offen?", 4, "de", extra=["Offene Items?"])
        assert v[0] == "Was ist offen?" and v[1] == "Offene Items?"
        assert v[2] == "Kurz gefasst: Was ist offen?" and v[3].endswith("Was ist offen?")
        many = question_variants("Q?", 12, "en")
        assert len(many) == 12 and many[0] == "Q?" and many.count("Q?") == 2   # wraps around
        with pytest.raises(ValueError):
            question_variants("Q?", 0)
        assert DEFAULT_RUNS == 5

    def test_read_variants_and_views(self, tmp_path) -> None:
        (tmp_path / "v.txt").write_text("A?\n\n  B? \n", encoding="utf-8")
        assert read_variants(tmp_path / "v.txt") == ["A?", "B?"]
        (tmp_path / "s.txt").write_text("Erste\nSicht.\n\nZweite Sicht.\n", encoding="utf-8")
        assert read_views(tmp_path / "s.txt") == ["Erste Sicht.", "Zweite Sicht."]


class TestMeasures:
    def _report(self, texts: list[str], rejected: set[int] = frozenset()) -> NoiseReport:
        runs = []
        for i, t in enumerate(texts):
            r = Run(variant=f"v{i}", answer=t, model="m")
            if i in rejected:
                r.rejected = "guard"
            else:
                analyse_answer(r)
            runs.append(r)
        idx = FactIndex(name="S", kind="solution", as_of="2026-10-13")
        return NoiseReport(question="Q?", runs=runs, index=idx)

    def test_consistency_core_scatter_conflicts(self) -> None:
        rep = self._report([
            "D-7 ist at_risk [S1/governance.dependencies(D-7).status]. Median 39 Tage [S1/total.median_ct].",
            "D-7 ist at_risk [S1/governance.dependencies(D-7).status]. Median 39 Tage [S1/total.median_ct].",
            "D-7 ist at_risk [S1/governance.dependencies(D-7).status]. Es gibt 41 offene Items [S1/total.open]. "
            "Median 40 Tage [S1/total.median_ct].",
        ])
        assert rep.consistency == round(100 * (1.0 + 2 / 3 + 2 / 3) / 3, 1)
        assert rep.core == ["S1/governance.dependencies(D-7).status", "S1/total.median_ct"]
        assert list(rep.scattered) == ["S1/total.open"]
        assert rep.scattered["S1/total.open"][0][0] == 3
        assert "S1/total.median_ct" in rep.number_conflicts
        assert rep.unknown_rate == 0.0 and rep.rejected_rate == 0.0

    def test_unknown_and_rejected_rates_and_too_few(self) -> None:
        rep = self._report([UNKNOWN_ANSWERS["de"], "x", UNKNOWN_ANSWERS["de"], "Satz [S1/a]."], rejected={1})
        assert rep.unknown_rate == 50.0 and rep.rejected_rate == 25.0
        assert rep.consistency is not None   # three valid runs
        single = self._report(["Satz [S1/a]."])
        assert single.consistency is None and single.core == [] and single.scattered == {}
        text = noise_to_markdown(single, "de")
        assert "weniger als zwei gültige Antworten" in text


class TestRun:
    def test_runs_against_one_stand_counts_rejected_and_writes_protocol(self, alpha, tmp_path) -> None:
        cfg, snap = alpha
        idx = build_fact_index(snap)
        open_v = idx.by_path["S1/total.open"].value
        items_v = idx.by_path["S1/total.items"].value
        answers = [f"Offen sind {open_v} Items [S1/total.open].",
                   f"Offen: {open_v} [S1/total.open]. Gesamt {items_v} [S1/total.items].",
                   "Keine Zitate hier.",                                   # rejected (uncited)
                   UNKNOWN_ANSWERS["de"]]
        prov = _cycling_provider(answers)
        with patch("llm.narrate.discover_providers", return_value={"cyc": prov}):
            rep = run_noise(cfg, "Wie viele offen?", tmp_path / "n.noise.md", n=4, provider_id="cyc",
                            lang="de", snapshot=snap, views=["Ich tippe auf 40."], log=lambda m: None)
        assert prov.calls == 4 and len(rep.runs) == 4
        assert rep.rejected_rate == 25.0 and rep.unknown_rate == 25.0
        assert rep.core == ["S1/total.open"] and list(rep.scattered) == ["S1/total.items"]
        text = (tmp_path / "n.noise.md").read_text(encoding="utf-8")
        assert text.startswith("# Noise-Audit — ") and "| 3 | " in text and "verworfen" in text
        assert "Einschätzungen des Stabs" in text and "1. Ich tippe auf 40." in text
        assert f"Index-Prüfsumme (SHA-256): {rep.index.digest()}" in text
        assert "### Lauf 2 — Kurz gefasst: Wie viele offen?" in text

    def test_export_is_refused_and_mock_is_fully_consistent(self, alpha, tmp_path) -> None:
        cfg, snap = alpha
        with pytest.raises(ValueError, match="export"):
            run_noise_audit(cfg, "F?", n=2, provider_id="export", snapshot=snap, log=lambda m: None)
        rep = run_noise_audit(cfg, "F?", n=3, provider_id="mock", snapshot=snap, log=lambda m: None)
        assert rep.consistency == 100.0 and rep.unknown_rate == 100.0 and rep.core == []


class TestCliAndGui:
    def test_cli_dispatches_to_noise(self, demo, tmp_path) -> None:
        from portfolio.cli import _run_ask, build_parser
        args = build_parser().parse_args(["c.json", "--ask", "F?", "--noise", "3", "--views", "v.txt"])
        assert args.noise == 3 and args.views == Path("v.txt")
        (tmp_path / "views.txt").write_text("Sicht eins.\n\nSicht zwei.\n", encoding="utf-8")
        ns = argparse.Namespace(
            config=Path(demo["solution_alpha"]), ask="F?", own_view="", ask_snapshot=Path(demo["snapshot_now"]),
            since_snapshot=None, ask_output=None, ask_scope="metrics", narrate="mock", llm_lang="en",
            as_of=REF, target_ct=90, llm_model=None, llm_base_url=None, browser=False,
            noise=3, noise_variants=None, views=tmp_path / "views.txt", noise_output=tmp_path / "out.noise.md")
        _run_ask(ns)
        text = (tmp_path / "out.noise.md").read_text(encoding="utf-8")
        assert text.startswith("# Noise audit — ") and "Sicht zwei." in text and "**100.0 / 100**" in text

    def test_gui_texts(self) -> None:
        from portfolio.gui import _T
        for lang in ("de", "en", "ro", "pt", "fr"):
            assert "lbl_ask_repeats" in _T[lang] and "msg_noise_done" in _T[lang]
