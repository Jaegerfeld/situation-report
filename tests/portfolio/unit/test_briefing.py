# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       15.10.2026
# Geändert:       15.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Tests des Lagevortrag-Entwurfs (M6): Einseiter-Zellen als zitierbare
#   Fakten E/…, Contract (Zellen + Fakten-Index), Zitat-Wächter kennt E/,
#   Mock antwortet den Unbekannt-Satz, zitierter Entwurf besteht, unzitierter
#   und erfundene Zahl werden verworfen (Einseiter steht), Datei mit
#   Leitplanke „Entwurf ≠ Vortrag“, CLI --onepager --narrate schreibt die
#   Datei und lässt die Seite byte-gleich, Kata ohne Entwurf, llm check
#   prüft die Zwecke d4_anomaly und m6_briefing auf Zitate.
# =============================================================================

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from llm.base import DEPLOYMENT_MOCK, LlmResult
from llm.check import CITATION_PURPOSES
from llm.guard import UNKNOWN_ANSWERS, citation_violations
from llm.prompts import briefing_system_prompt
from portfolio.briefing import (
    PURPOSE,
    Briefing,
    briefing_contract,
    briefing_path,
    briefing_to_markdown,
    draft_briefing,
    page_facts,
)
from portfolio.facts import build_fact_index
from portfolio.onepager import DIMENSIONS, build_onepager
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
    cfg = load_solution_config(demo["portfolio"])
    prev = load_snapshot(demo["snapshot_prev"])
    op = build_onepager(cfg, "de", prev_snapshot=prev, reference=REF, log=lambda m: None)
    return cfg, prev, op


class _Spy:
    """A provider that answers from a list, so the guards can be exercised."""
    provider_id = "spy"; deployment_class = DEPLOYMENT_MOCK; default_model = "spy-1"

    def __init__(self, answers: list[str]) -> None:
        self._answers = iter(answers)

    def complete(self, system, prompt, config):
        return LlmResult(text=next(self._answers), provider_id="spy", model="spy-1",
                         deployment_class=DEPLOYMENT_MOCK)


class TestFactsAndContract:
    def test_page_facts_cover_bluf_meta_cells_and_decisions(self, alpha) -> None:
        _, _, op = alpha
        facts = page_facts(op, "de")
        by = {f.path: f for f in facts}
        assert by["E/bluf"].value.endswith(".") and by["E/meta"].value.startswith(op.name)
        assert len(facts) == 2 + len(DIMENSIONS) * 4            # bluf, meta, 3 questions + decide per row
        assert "Vergleichsstand" not in by["E/flow.q2"].value    # column 2 is filled from the delta
        assert "confidence" in by["E/flow.q1"].label and by["E/flow.q1"].value
        assert all(f.source == "onepager" and f.as_of == REF.isoformat() for f in facts)

    def test_without_earlier_state_column_two_says_so(self, demo) -> None:
        cfg = load_solution_config(demo["solution_alpha"])
        op = build_onepager(cfg, "de", reference=REF, log=lambda m: None)
        by = {f.path: f for f in page_facts(op, "de")}
        assert by["E/flow.q2"].value == "kein Vergleichsstand — Spalte leer"
        assert by["E/bluf"].value.startswith("1 Wecker ausgelöst") and "DP-A1" in by["E/flow.decide"].value

    def test_contract_has_cells_then_index_and_guard_knows_e_paths(self, alpha, demo) -> None:
        _, prev, op = alpha
        index = build_fact_index(load_snapshot(demo["snapshot_now"]), prev=prev)
        contract = briefing_contract(op, page_facts(op, "de"), index)
        assert contract.startswith("# Briefing-Contract - ")
        assert contract.index("## One-pager") < contract.index("- [E/bluf]") < contract.index("# Fact index")
        assert citation_violations("Ein Wecker ist ausgelöst [E/bluf].", {"E/bluf": "1 Wecker ausgelöst"}) == []
        assert citation_violations("Ein Wecker ist ausgelöst [X/bluf].", {"E/bluf": "1"})

    def test_prompt_is_versioned_and_cites(self) -> None:
        de, en = briefing_system_prompt("de"), briefing_system_prompt("en")
        assert "ZITIERPFLICHT" in de and "[S1/" in de and "ENTWURF" in de
        assert "CITATION DUTY" in en and "[E/bluf]" in en
        assert briefing_system_prompt("xx") == de
        assert set(CITATION_PURPOSES) >= {"d3_question", "d4_anomaly", "m6_briefing"}


class TestDraft:
    def test_mock_answers_unknown_and_audits(self, alpha, tmp_path) -> None:
        cfg, prev, op = alpha
        b = draft_briefing(op, cfg, provider_id="mock", prev_snapshot=prev,
                           audit_path=tmp_path / "a.jsonl", log=lambda m: None)
        assert b.ok and b.text == UNKNOWN_ANSWERS["de"] and "mock" in b.banner
        assert b.page_facts == 18 and b.index_facts > 50 and len(b.digest) == 64
        record = json.loads((tmp_path / "a.jsonl").read_text(encoding="utf-8"))
        assert record["purpose"] == PURPOSE == "m6_briefing" and record["guard_passed"] is True

    def test_cited_passes_uncited_and_invented_number_discarded(self, alpha, tmp_path) -> None:
        cfg, prev, op = alpha
        spy = _Spy(["Ein Wecker ist ausgelöst [E/bluf]. Dazu liegt im Lagebild keine Angabe vor.",
                    "Das Team ist überlastet und braucht Entlastung.",
                    "Es sind 987654 Vorgänge offen [E/bluf]."])
        with patch("llm.narrate.discover_providers", return_value={"spy": spy}):
            good = draft_briefing(op, cfg, provider_id="spy", prev_snapshot=prev,
                                  audit_path=tmp_path / "a.jsonl", log=lambda m: None)
            bad = draft_briefing(op, cfg, provider_id="spy", prev_snapshot=prev,
                                 audit_path=tmp_path / "a.jsonl", log=lambda m: None)
            num = draft_briefing(op, cfg, provider_id="spy", prev_snapshot=prev,
                                 audit_path=tmp_path / "a.jsonl", log=lambda m: None)
        assert good.ok and good.text.startswith("Ein Wecker") and "KI-formulierter" in good.banner
        assert not bad.ok and bad.text == "" and bad.rejected.startswith("citation guard: uncited")
        assert not num.ok and "987654" in num.rejected
        flags = [json.loads(line)["guard_passed"]
                 for line in (tmp_path / "a.jsonl").read_text(encoding="utf-8").splitlines()]
        assert flags == [True, True, False, False]

    def test_markdown_carries_the_guardrail_and_the_basis(self, alpha) -> None:
        _, _, op = alpha
        ok = Briefing(text="Satz [E/bluf].", banner="B", model="m", deployment_class="mock",
                      contract="c", page_facts=18, index_facts=70)
        md = briefing_to_markdown(ok, op, Path("x/alpha.html"), "de")
        assert md.startswith("# Lagevortrag — Entwurf (M6)") and "Entwurf — nicht der Vortrag" in md
        assert "> B" in md and "Satz [E/bluf]." in md
        assert "Einseiter `alpha.html`" in md and "Vergleichsstand: " in md and "Prüfsumme" in md
        rej = Briefing(rejected="citation guard: uncited", contract="c")
        md2 = briefing_to_markdown(rej, op, "alpha.html", "en")
        assert "Draft discarded: citation guard: uncited" in md2 and "stands unchanged" in md2 and "> " not in md2
        assert briefing_path("out/p.html", "de").name == "p.html.vortrag.md"
        assert briefing_path("out/p.html", "en").name == "p.html.briefing.md"


class TestCli:
    def _ns(self, demo, out: Path, **kw) -> argparse.Namespace:
        base = dict(config=Path(demo["portfolio"]), onepager=out, since_snapshot=Path(demo["snapshot_prev"]),
                    kata=False, as_of=REF, target_ct=90, lang="de", llm_lang="de", narrate=None,
                    llm_model=None, llm_base_url=None, browser=False)
        base.update(kw)
        return argparse.Namespace(**base)

    def test_narrate_writes_the_briefing_and_leaves_the_page_untouched(self, demo, tmp_path, capsys) -> None:
        from portfolio.cli import _run_onepager, build_parser
        ns = build_parser().parse_args(["c.json", "--onepager", "p.html", "--narrate", "mock"])
        assert ns.narrate == "mock" and ns.onepager == Path("p.html")
        _run_onepager(self._ns(demo, tmp_path / "plain.html"))
        _run_onepager(self._ns(demo, tmp_path / "ai.html", narrate="mock"))
        assert (tmp_path / "plain.html").read_bytes() == (tmp_path / "ai.html").read_bytes()
        md = (tmp_path / "ai.html.vortrag.md").read_text(encoding="utf-8")
        assert UNKNOWN_ANSWERS["de"] in md and "Entwurf — nicht der Vortrag" in md
        assert not (tmp_path / "plain.html.vortrag.md").exists()
        assert (tmp_path / "llm_audit.jsonl").is_file()
        assert "Briefing draft (for human editing)" in capsys.readouterr().out

    def test_kata_never_gets_a_briefing(self, demo, tmp_path) -> None:
        from portfolio.cli import _run_onepager
        _run_onepager(self._ns(demo, tmp_path / "kata.html", kata=True, narrate="mock"))
        assert (tmp_path / "kata.html").is_file() and not list(tmp_path.glob("*.md"))
