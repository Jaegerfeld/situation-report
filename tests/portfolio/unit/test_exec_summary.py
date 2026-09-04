# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       04.09.2026
# Geändert:       04.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests der LLM-Executive-Summary (D1): der deterministische
#   Summary-Contract (Kennzahlen + Konfidenz + Governance-Kopfzahlen,
#   strukturell OHNE Personen/Owner), das Einfügen unter der
#   Management-Summary-Tabelle (mit Fallback), der versionierte
#   Exec-Summary-Prompt, die system_prompt-Weiche in llm.narrate und
#   attach_exec_summary Ende-zu-Ende über den mock-Provider.
# =============================================================================

from __future__ import annotations

import json
from datetime import date
from typing import Any
from unittest.mock import patch

from portfolio.exec_summary import (
    attach_exec_summary,
    insert_after_summary,
    summary_to_markdown,
)
from portfolio.snapshot import Snapshot

AS_OF = date(2026, 8, 30)


def _snapshot() -> Snapshot:
    return Snapshot(
        name="Demo Portfolio", kind="portfolio", as_of=AS_OF,
        created="2026-08-30T12:00:00", target_ct=90,
        total={"label": "Demo Portfolio", "items": 100, "completed": 75,
               "open": 25, "median_ct": 8.44, "p85_ct": 18.0,
               "p95_ct": 30.0, "target_ct_pct": 95.0, "median_lt": 16.44,
               "p85_lt": 39.0},
        units=[{"label": "Solution Alpha", "items": 60, "completed": 50,
                "open": 10, "median_ct": 7.0, "p85_ct": 15.0,
                "p95_ct": 25.0, "target_ct_pct": 97.0, "median_lt": 14.0,
                "p85_lt": 30.0}],
        sources=[{"label": "ART Beta-3", "records": 20,
                  "data_as_of": "2026-07-01", "confidence": "low"}],
        governance={
            "risks": [
                {"id": "BR-2", "roam": "owned", "owner": "Security-Gilde"},
                {"id": "AR-1", "roam": "resolved", "owner": "Max Mustermann"},
            ],
            "dependencies": [{"id": "AD-1", "status": "blocked"}],
            "slo": [{"service": "Order Sync API"}],
        })


class TestSummaryContract:
    def test_contains_metrics_confidence_and_head_counts(self) -> None:
        md = summary_to_markdown(_snapshot())
        assert "Demo Portfolio (portfolio)" in md
        assert "As of 2026-08-30" in md and "90 days" in md
        assert "completed 75" in md and "median CT 8.4 d" in md
        assert "Solution Alpha" in md and "target-CT share 97.0 %" in md
        assert "ART Beta-3: low" in md
        assert "risks: 2 (owned 1, resolved 1)" in md
        assert "dependencies: 1 (blocked 1)" in md
        assert "slo: 1 services" in md

    def test_owners_never_reach_the_contract(self) -> None:
        # Aggregat-Grenze strukturell: Owner-Felder tauchen nicht auf —
        # selbst wenn ein Register (fehlerhaft) einen Personennamen trägt.
        md = summary_to_markdown(_snapshot())
        assert "Max Mustermann" not in md
        assert "Security-Gilde" not in md

    def test_deterministic(self) -> None:
        assert summary_to_markdown(_snapshot()) == summary_to_markdown(
            _snapshot())


class TestInsertAfterSummary:
    def test_lands_directly_below_the_summary_table(self) -> None:
        page = ("<html><body><h2>Management Summary</h2>"
                "<table><tr><td>1</td></tr></table>"
                "<h2>Data Quality</h2><table></table></body></html>")
        out = insert_after_summary(page, "<h2>X</h2>")
        assert out.index("<h2>X</h2>") == page.index("<h2>Data Quality")
        assert out.count("<h2>X</h2>") == 1

    def test_falls_back_to_page_end_without_anchor(self) -> None:
        out = insert_after_summary("<html><body>foo</body></html>",
                                   "<h2>X</h2>")
        assert out.endswith("<h2>X</h2></body></html>")
        assert insert_after_summary("nur text", "<h2>X</h2>").endswith(
            "<h2>X</h2>")


class TestExecSummaryPrompt:
    def test_versioned_language_specific_and_binding(self) -> None:
        from llm.prompts import exec_summary_system_prompt
        de = exec_summary_system_prompt("de")
        en = exec_summary_system_prompt("en")
        assert de != en
        assert "niemals Personen" in de and "Contract" in de
        assert "never persons" in en and "verbatim" in en
        assert exec_summary_system_prompt("fr") == de


class TestSystemPromptSwitchInNarrate:
    def test_custom_prompt_reaches_the_provider(self) -> None:
        from llm.base import DEPLOYMENT_MOCK, LlmResult
        from llm.narrate import narrate

        seen: list[str] = []

        class Spy:
            provider_id = "spy"
            deployment_class = DEPLOYMENT_MOCK
            default_model = "spy-1"

            def complete(self, system: str, prompt: str,
                         config: dict[str, Any]) -> LlmResult:
                seen.append(system)
                return LlmResult(text="Nur Text ohne Ziffernpaare.",
                                 provider_id="spy", model="spy-1",
                                 deployment_class=DEPLOYMENT_MOCK)

        with patch("llm.narrate.discover_providers",
                   return_value={"spy": Spy()}):
            narrate("quelle", provider_id="spy",
                    system_prompt="MEIN PROMPT")
            narrate("quelle", provider_id="spy")
        from llm.prompts import narration_system_prompt
        assert seen[0] == "MEIN PROMPT"
        assert seen[1] == narration_system_prompt("de")


class TestAttachExecSummary:
    def test_end_to_end_with_mock(self, tmp_path) -> None:
        page = ("<html><body><h2>Management Summary</h2>"
                "<table><tr><td>1</td></tr></table></body></html>")
        audit = tmp_path / "llm_audit.jsonl"
        with patch("portfolio.exec_summary.build_snapshot",
                   return_value=_snapshot()) as builder:
            out, narration = attach_exec_summary(
                page, config=object(), provider_id="mock", lang="en",
                audit_path=audit, log=lambda m: None)
        assert builder.called
        assert "Executive Summary (Entwurf)" in out
        assert "MOCK" in out and "AI-drafted" in out
        assert out.index("Executive Summary") > out.index("</table>")
        record = json.loads(audit.read_text(encoding="utf-8"))
        assert record["purpose"] == "d1_exec_summary"
        assert record["guard_passed"] is True
        assert "MOCK" in narration.text

    def test_input_is_exactly_the_summary_contract(self, tmp_path) -> None:
        # Aggregat-Leitplanke: das LLM sieht AUSSCHLIESSLICH den Contract.
        import llm.narrate as narrate_mod
        seen: list[str] = []
        original = narrate_mod.narrate

        def spy(source_text, **kwargs):
            seen.append(source_text)
            return original(source_text, **kwargs)

        with patch("portfolio.exec_summary.build_snapshot",
                   return_value=_snapshot()):
            with patch("llm.narrate.narrate", side_effect=spy):
                attach_exec_summary(
                    "<html><body></body></html>", config=object(),
                    provider_id="mock", log=lambda m: None)
        assert seen == [summary_to_markdown(_snapshot())]
