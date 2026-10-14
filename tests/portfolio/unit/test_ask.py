# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       14.10.2026
# Geändert:       14.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Tests des Befragbaren Lagebilds (D3): Contract (Frage + Index), Mock
#   antwortet mit dem Unbekannt-Satz, zitierte Antwort besteht, unzitierte
#   oder falsch bezifferte Antwort wird verworfen (Nachweis guard_passed=
#   false), eigene Einschätzung geht nie ans Modell, Export-Provider schreibt
#   das Bündel, Datei-Format, CLI-Pfad, GUI-Texte und -Handler.
# =============================================================================

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from llm.audit import AUDIT_FILENAME
from llm.base import DEPLOYMENT_MOCK, LlmResult
from llm.guard import UNKNOWN_ANSWERS, CitationGuardError
from portfolio.ask import ask_question, ask_to_markdown, question_contract, run_ask
from portfolio.facts import build_fact_index
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


def _provider(text: str):
    """A provider returning a fixed answer, discoverable as 'fixed'."""
    class Fixed:
        provider_id = "fixed"
        deployment_class = DEPLOYMENT_MOCK
        default_model = "fixed-1"

        def complete(self, system, prompt, config):
            self.last_prompt = prompt
            return LlmResult(text=text, provider_id="fixed", model="fixed-1",
                             deployment_class=DEPLOYMENT_MOCK, endpoint="mock://fixed")
    return Fixed()


class TestContractAndMock:
    def test_contract_carries_question_and_index(self, alpha) -> None:
        cfg, snap = alpha
        idx = build_fact_index(snap)
        c = question_contract(idx, "Wie viele offene Items?")
        assert c.startswith(f"# Question-Contract - {snap.name} ({snap.kind})\nQuestion: Wie viele offene Items?")
        assert "- [S1/total.open]" in c

    def test_mock_answers_unknown_and_passes(self, alpha, tmp_path) -> None:
        cfg, snap = alpha
        res = ask_question(cfg, "Irgendwas?", provider_id="mock", lang="de", snapshot=snap,
                           audit_path=tmp_path / AUDIT_FILENAME, log=lambda m: None)
        assert res.answer == UNKNOWN_ANSWERS["de"] and "KI-formulierter Entwurf" in res.banner
        rec = json.loads((tmp_path / AUDIT_FILENAME).read_text(encoding="utf-8").splitlines()[-1])
        assert rec["purpose"] == "d3_question" and rec["guard_passed"] is True

    def test_empty_question_rejected(self, alpha) -> None:
        cfg, snap = alpha
        with pytest.raises(ValueError, match="empty"):
            ask_question(cfg, "   ", provider_id="mock", snapshot=snap, log=lambda m: None)


class TestGuards:
    def test_cited_answer_passes_and_own_view_never_reaches_the_model(self, alpha, tmp_path) -> None:
        cfg, snap = alpha
        idx = build_fact_index(snap)
        open_fact = idx.by_path["S1/total.open"]
        prov = _provider(f"Es sind {open_fact.value} Items offen [S1/total.open].")
        with patch("llm.narrate.discover_providers", return_value={"fixed": prov}):
            res = ask_question(cfg, "Wie viele offen?", provider_id="fixed", snapshot=snap,
                               own_view="Ich schätze 50.", audit_path=tmp_path / AUDIT_FILENAME,
                               log=lambda m: None)
        assert res.answer.endswith("[S1/total.open].") and res.own_view == "Ich schätze 50."
        assert "Ich schätze 50." not in prov.last_prompt and "Question: Wie viele offen?" in prov.last_prompt

    def test_uncited_or_misnumbered_answer_is_discarded_and_recorded(self, alpha, tmp_path) -> None:
        cfg, snap = alpha
        audit = tmp_path / AUDIT_FILENAME
        idx = build_fact_index(snap)
        # a number that IS in the contract (items) but not in the cited fact (open):
        # the plain numbers guard lets it through, the citation guard must not
        items = idx.by_path["S1/total.items"].value
        assert items != idx.by_path["S1/total.open"].value
        for text, marker in (("Es sind viele Items offen.", "uncited"),
                             (f"Es sind {items} Items offen [S1/total.open].", "number not in cited facts")):
            with patch("llm.narrate.discover_providers", return_value={"fixed": _provider(text)}):
                with pytest.raises(CitationGuardError) as exc:
                    ask_question(cfg, "Wie viele offen?", provider_id="fixed", snapshot=snap,
                                 audit_path=audit, log=lambda m: None)
            assert exc.value.violations[0].startswith(marker)
        records = [json.loads(line) for line in audit.read_text(encoding="utf-8").splitlines()]
        # narrate records its numbers-guard pass (first case), the citation guard its fail
        assert [r["guard_passed"] for r in records][-1] is False
        assert all(r["purpose"] == "d3_question" for r in records)

    def test_export_provider_writes_bundle_and_file(self, alpha, tmp_path) -> None:
        import llm.providers.export as export_provider
        cfg, snap = alpha
        with patch.object(export_provider, "copy_to_clipboard", lambda text: False):
            res = run_ask(cfg, "Was ist überfällig?", tmp_path / "q.ask.md", provider_id="export",
                          snapshot=snap, log=lambda m: None)
        assert res.exported and list(tmp_path.glob("prompt_d3_question_*.md"))
        assert "Kein Modell aufgerufen" in (tmp_path / "q.ask.md").read_text(encoding="utf-8")


class TestFileAndCli:
    def test_markdown_shows_question_own_view_banner_answer_and_provenance(self, alpha, tmp_path) -> None:
        cfg, snap = alpha
        res = run_ask(cfg, "Frage?", tmp_path / "out" / "a.ask.md", provider_id="mock", snapshot=snap,
                      own_view="Meine Sicht.", log=lambda m: None)
        text = res.written.read_text(encoding="utf-8")
        assert text.startswith(f"# Frage an das Lagebild — {snap.name} (2026-10-13)")
        assert "**Frage:** Frage?" in text and "**Eigene Einschätzung (vor der Antwort):** Meine Sicht." in text
        assert "> KI-formulierter Entwurf" in text and UNKNOWN_ANSWERS["de"] in text
        assert "Index-Prüfsumme (SHA-256): " + res.index.digest() in text
        skipped = ask_to_markdown(run_ask(cfg, "F?", tmp_path / "b.ask.md", provider_id="mock",
                                          snapshot=snap, log=lambda m: None), "en")
        assert "**Own assessment (before the answer):** — (skipped)" in skipped

    def test_cli_run_ask_default_output_and_prev(self, demo, tmp_path) -> None:
        from portfolio.cli import _run_ask
        args = argparse.Namespace(
            config=Path(demo["solution_alpha"]), ask="Was hat sich geändert?", own_view="",
            ask_snapshot=Path(demo["snapshot_now"]), since_snapshot=Path(demo["snapshot_prev"]),
            ask_output=tmp_path / "cli.ask.md", ask_scope="metrics", narrate="mock", llm_lang="en",
            as_of=REF, target_ct=90, llm_model=None, llm_base_url=None, browser=False)
        _run_ask(args)
        text = (tmp_path / "cli.ask.md").read_text(encoding="utf-8")
        assert "S1 = 2026-10-13, S0 = 2026-09-29" in text and UNKNOWN_ANSWERS["en"] in text

    def test_cli_exit_3_when_discarded(self, demo, tmp_path) -> None:
        from portfolio.cli import _run_ask
        args = argparse.Namespace(
            config=Path(demo["solution_alpha"]), ask="F?", own_view="", ask_snapshot=Path(demo["snapshot_now"]),
            since_snapshot=None, ask_output=tmp_path / "x.ask.md", ask_scope="all", narrate="fixed",
            llm_lang="de", as_of=REF, target_ct=90, llm_model=None, llm_base_url=None, browser=False)
        with patch("llm.narrate.discover_providers", return_value={"fixed": _provider("Keine Zitate.")}):
            with pytest.raises(SystemExit) as exc:
                _run_ask(args)
        assert exc.value.code == 3 and not (tmp_path / "x.ask.md").exists()

    def test_parser_knows_the_flags(self) -> None:
        from portfolio.cli import build_parser
        args = build_parser().parse_args(["c.json", "--ask", "F?", "--own-view", "x", "--ask-scope", "registers"])
        assert args.ask == "F?" and args.own_view == "x" and args.ask_scope == "registers"


class TestGuiWiring:
    def test_texts_and_handler(self) -> None:
        from portfolio.gui import _T, SolutionManagerApp
        for lang in ("de", "en", "ro", "pt", "fr"):
            for key in ("btn_ask", "dlg_ask_title", "lbl_ask_question", "chk_ask_hygiene", "lbl_ask_own_view",
                        "btn_ask_run", "dlg_save_ask", "msg_ask_running", "msg_ask_done", "msg_ask_rejected",
                        "msg_ask_error", "msg_ask_empty"):
                assert key in _T[lang], (lang, key)
        assert callable(SolutionManagerApp._ask_dialog)
