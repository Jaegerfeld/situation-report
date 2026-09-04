# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       04.09.2026
# Geändert:       04.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests des Red-Team-Assistenten (D5): deterministischer
#   Log-Contract, der FRAGEN-Wächter („nur Rohmaterial für das Urteil,
#   nie Urteile“ — maschinell erzwungen), der versionierte Prompt und
#   run_red_team Ende-zu-Ende über den mock-Provider (Banner, Audit
#   purpose d5_red_team, Fehlerfall ohne Decision-Log).
# =============================================================================

from __future__ import annotations

import json
from datetime import date

import pytest

from portfolio.decision_config import (
    KIND_ASSUMPTION,
    KIND_DECISION,
    LogEntry,
)
from portfolio.red_team import (
    QuestionsOnlyError,
    decision_log_to_markdown,
    enforce_questions,
)


def _entries():
    return [
        ("Solution Alpha", LogEntry(
            entry_id="ADR-A1", kind=KIND_DECISION,
            title="Pool via custom stage map", status="accepted",
            owner="Plattform-Team", logged_on=date(2026, 5, 1),
            supersedes="ADR-A2")),
        ("Solution Beta", LogEntry(
            entry_id="AS-B1", kind=KIND_ASSUMPTION,
            title="Beta-3 heilt sich selbst", status="open",
            owner="Data-Team", review_by=date(2026, 8, 1))),
    ]


class TestContract:
    def test_lists_entries_with_ids_status_and_dates(self) -> None:
        md = decision_log_to_markdown(_entries())
        assert "[Solution Alpha] ADR-A1 (decision, accepted)" in md
        assert "supersedes ADR-A2" in md
        assert "[Solution Beta] AS-B1 (assumption, open)" in md
        assert "review by 2026-08-01" in md
        assert "owner: Data-Team" in md

    def test_deterministic(self) -> None:
        assert decision_log_to_markdown(_entries()) == \
            decision_log_to_markdown(_entries())


class TestQuestionsGuard:
    def test_pure_questions_pass(self) -> None:
        enforce_questions("## ADR-A1\n- Was kippt zuerst?\n"
                          "- Woran erkennt das Team das früh?\n")

    def test_statement_bullets_are_discarded(self) -> None:
        with pytest.raises(QuestionsOnlyError, match="not questions"):
            enforce_questions("## ADR-A1\n- Was kippt zuerst?\n"
                              "- Empfehlung: Entscheidung zurücknehmen.\n")

    def test_question_free_output_is_discarded(self) -> None:
        with pytest.raises(QuestionsOnlyError):
            enforce_questions("Alles bestens, keine Fragen.")


class TestPrompt:
    def test_versioned_language_specific_and_questions_only(self) -> None:
        from llm.prompts import red_team_system_prompt
        de = red_team_system_prompt("de")
        en = red_team_system_prompt("en")
        assert de != en
        assert "AUSSCHLIESSLICH Fragen" in de and "niemals Personen" in de
        assert "ONLY questions" in en and "never persons" in en
        assert "remortem" in de and "remortem" in en  # Premortem-Rahmung


class TestRunRedTeam:
    def _config_with_log(self, tmp_path):
        import dataclasses as dc

        from portfolio.decision_config import DecisionLog, save_decisions
        from portfolio.solution_config import (
            Member,
            SolutionConfig,
            load_solution_config,
            save_solution_config,
        )
        log_file = tmp_path / "registers" / "decisions.json"
        log_file.parent.mkdir()
        # supersedes ist referenzvalidiert — fuer das gespeicherte
        # Register die Kette kappen (der Contract-Test oben prueft sie
        # in-memory).
        save_decisions(log_file, DecisionLog(
            entries=[dc.replace(e, supersedes="")
                     for _, e in _entries()]))
        cfg_file = tmp_path / "solution.json"
        save_solution_config(cfg_file, SolutionConfig(
            name="Alpha", members=[Member(name="A", issue_times="a.xlsx")],
            decisions="registers/decisions.json"))
        return load_solution_config(cfg_file)

    def test_writes_labeled_questions_with_audit(self, tmp_path) -> None:
        from portfolio.red_team import run_red_team
        out = tmp_path / "fragen.md"
        narration = run_red_team(self._config_with_log(tmp_path), out,
                                 provider_id="mock", lang="en",
                                 log=lambda m: None)
        text = out.read_text(encoding="utf-8")
        assert "unreviewed" in text  # Banner in Zielsprache
        assert "?" in narration.text
        record = json.loads(
            (tmp_path / "llm_audit.jsonl").read_text(encoding="utf-8"))
        assert record["purpose"] == "d5_red_team"

    def test_without_decision_log_fails_with_hint(self, tmp_path) -> None:
        from portfolio.red_team import run_red_team
        from portfolio.solution_config import Member, SolutionConfig
        cfg = SolutionConfig(name="X",
                             members=[Member(name="A",
                                             issue_times="a.xlsx")])
        with pytest.raises(ValueError, match="decision/assumption log"):
            run_red_team(cfg, tmp_path / "fragen.md",
                         provider_id="mock", log=lambda m: None)

    def test_input_is_exactly_the_log_contract(self, tmp_path) -> None:
        import llm.narrate as narrate_mod
        from portfolio.red_team import run_red_team
        seen: list[str] = []
        original = narrate_mod.narrate

        def spy(source_text, **kwargs):
            seen.append(source_text)
            return original(source_text, **kwargs)

        cfg = self._config_with_log(tmp_path)
        from unittest.mock import patch
        with patch("llm.narrate.narrate", side_effect=spy):
            run_red_team(cfg, tmp_path / "fragen.md", provider_id="mock",
                         log=lambda m: None)
        from portfolio.aggregator import _collect_decisions
        assert seen == [decision_log_to_markdown(
            _collect_decisions(cfg, log=lambda m: None))]
