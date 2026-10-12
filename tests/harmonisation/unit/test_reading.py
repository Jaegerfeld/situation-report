# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       12.10.2026
# Geändert:       12.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Tests der KI-Lesart (P3 Schritt 2): der Lesart-Contract trägt alle
#   Zahlen und keine Personen, der versionierte Prompt untersagt die
#   Empfehlung, der Entwurf landet gekennzeichnet direkt unter der Matrix,
#   der Audit-Eintrag trägt den Zweck p3_reading, das LLM sieht exakt den
#   Contract (Spy), der Zahlen-Wächter wird einmal wiederholt.
# =============================================================================

from __future__ import annotations

import json
from datetime import date
from unittest.mock import patch

import pytest

from harmonisation.examples import write_example
from harmonisation.model import load_workspace
from harmonisation.reading import (
    PURPOSE,
    attach_reading,
    insert_after_first_table,
    matrix_to_markdown,
    reading_markdown,
    reading_title,
)
from harmonisation.render import render_html


@pytest.fixture
def ws(tmp_path):
    write_example(tmp_path)
    return load_workspace(tmp_path)


class TestContract:
    def test_scores_decisions_and_no_assessment(self, ws) -> None:
        md = matrix_to_markdown(ws, today=date(2026, 10, 12))
        assert "## Order-to-Delivery (brands: Brand A, Brand B, Brand C)" in md
        assert "score 67.6" in md and "score 84.3" in md and "spread 21" in md
        assert "confidence low" in md and "confidence medium" in md
        assert "## Procure-to-Pay" in md and "no assessment" in md
        assert 'board decision: standardise (depth: "Prozess und Kernsystem' in md
        assert "board decision: open" in md          # p2p, h2r

    def test_owners_and_assessors_never_reach_the_contract(self, ws) -> None:
        md = matrix_to_markdown(ws)
        for person in ("Head of Logistics", "Head of Sales", "CPO", "CHRO",
                       "Logistik-Leitung", "IT-Architektur", "Vertriebs-Leitung"):
            assert person not in md

    def test_deterministic(self, ws) -> None:
        today = date(2026, 10, 12)
        assert matrix_to_markdown(ws, today) == matrix_to_markdown(ws, today)


class TestPrompt:
    def test_versioned_forbids_recommendation_and_pins_language(self) -> None:
        from llm.prompts import harmonisation_system_prompt
        de, en = harmonisation_system_prompt("de"), harmonisation_system_prompt("en")
        assert "KEINE Empfehlung" in de and "DEUTSCH" in de
        assert "NO recommendation" in en and "ENGLISH" in en
        assert "niemals Personen" in de and "never persons" in en
        assert harmonisation_system_prompt("fr") == de


class TestInsert:
    def test_lands_below_the_first_table(self) -> None:
        page = "<html><body><table><tr><td>1</td></tr></table><h2>x</h2><table></table></body></html>"
        out = insert_after_first_table(page, "<h2>DRAFT</h2>")
        assert out.index("DRAFT") < out.index("<h2>x</h2>")

    def test_falls_back_to_footer_then_end(self) -> None:
        assert insert_after_first_table("<body><footer>f</footer></body></html>", "D") \
            .index("D") < 7
        assert insert_after_first_table("<body></body></html>", "D").endswith("D</body></html>")
        assert insert_after_first_table("plain", "D") == "plainD"


class TestAttach:
    def test_end_to_end_with_mock(self, ws, tmp_path) -> None:
        page = render_html(ws, "en")
        audit = tmp_path / "llm_audit.jsonl"
        out, narration = attach_reading(page, matrix_to_markdown(ws), "mock", lang="en",
                                        audit_path=audit, log=lambda m: None)
        assert reading_title("en") in out and "AI-drafted" in out and "MOCK" in out
        assert out.index(reading_title("en")) > out.index("</table>")
        assert out.index(reading_title("en")) < out.index("Second reading")
        record = json.loads(audit.read_text(encoding="utf-8"))
        assert record["purpose"] == PURPOSE == "p3_reading"
        assert record["guard_passed"] is True
        md = reading_markdown(narration, reading_title("en"))
        assert md.startswith("# AI reading (draft)") and narration.banner in md

    def test_llm_sees_exactly_the_contract(self, ws) -> None:
        import llm.narrate as narrate_mod
        seen: list[str] = []
        original = narrate_mod.narrate

        def spy(source_text, **kwargs):
            seen.append(source_text)
            return original(source_text, **kwargs)

        contract = matrix_to_markdown(ws)
        with patch("llm.narrate.narrate", side_effect=spy):
            attach_reading("<html><body></body></html>", contract, "mock",
                           log=lambda m: None)
        assert seen == [contract]

    def test_numbers_guard_is_retried_once(self, ws) -> None:
        import llm.narrate as narrate_mod
        from llm.guard import NumbersGuardError
        calls: list[int] = []
        original = narrate_mod.narrate

        def flaky(source_text, **kwargs):
            calls.append(1)
            if len(calls) == 1:
                raise NumbersGuardError(["42"])
            return original(source_text, **kwargs)

        with patch("llm.narrate.narrate", side_effect=flaky):
            out, _ = attach_reading("<table></table>", matrix_to_markdown(ws), "mock",
                                    lang="en", log=lambda m: None)
        assert len(calls) == 2 and "MOCK" in out

    def test_unknown_provider_is_a_runtime_error(self, ws) -> None:
        with pytest.raises(RuntimeError):
            attach_reading("<table></table>", matrix_to_markdown(ws), "nope",
                           log=lambda m: None)

    def test_reading_title_per_language(self) -> None:
        assert reading_title("de") == "KI-Lesart (Entwurf)"
        assert reading_title("xx") == reading_title("en")
