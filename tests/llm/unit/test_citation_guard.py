# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       14.10.2026
# Geändert:       14.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Tests des Zitat-Wächters (D3): Aussagen-Zerlegung (Listen, Sätze,
#   Überschriften, Unbekannt-Satz), Verstöße (unzitiert, unbekannter Pfad,
#   Zahl außerhalb der zitierten Fakten), Fakten-Zeilen aus dem Contract,
#   Einbindung in llm check für den Zweck d3_question, Prompt und Mock.
# =============================================================================

from __future__ import annotations

from datetime import datetime

from llm.check import check_answer, parse_bundle
from llm.export import build_bundle
from llm.guard import (
    UNKNOWN_ANSWERS,
    CitationGuardError,
    citation_violations,
    parse_fact_lines,
    statements,
)

CONTRACT = """# Question-Contract - Alpha (solution)
Question: Wie steht es um D-7?

# Fact index - Alpha (solution)
S1 = stand as of 2026-10-13

## Facts
- [S1/total.median_ct] median_ct = 39.0 d (as of 2026-10-13; Alpha)
- [S1/units(ART Alpha-2).open] open = 41 (as of 2026-10-13; Alpha)
- [S1/governance.dependencies(D-7).status] status = at_risk (as of 2026-10-13; Alpha)
- [S1/governance.dependencies(D-7).due] due = 2026-10-20 (as of 2026-10-13; Alpha)
"""
EVIDENCE = parse_fact_lines(CONTRACT)


class TestStatements:
    def test_lists_sentences_headings_and_unknown(self) -> None:
        text = ("## Antwort\n"
                "- D-7 ist gefährdet [S1/governance.dependencies(D-7).status].\n"
                "Der Median liegt bei 39 Tagen [S1/total.median_ct]. Alpha-2 hat 41 offene Items "
                "[S1/units(ART Alpha-2).open].\n"
                f"{UNKNOWN_ANSWERS['de']}\n\n")
        got = statements(text)
        assert len(got) == 3 and got[0].startswith("D-7 ist gefährdet")
        assert got[2].startswith("Alpha-2 hat 41")

    def test_fact_lines_parse_paths_with_parentheses(self) -> None:
        assert set(EVIDENCE) == {"S1/total.median_ct", "S1/units(ART Alpha-2).open",
                                 "S1/governance.dependencies(D-7).status",
                                 "S1/governance.dependencies(D-7).due"}
        assert "41" in EVIDENCE["S1/units(ART Alpha-2).open"]


class TestViolations:
    def test_cited_answer_passes(self) -> None:
        answer = ("D-7 steht auf at_risk [S1/governance.dependencies(D-7).status] und ist bis "
                  "2026-10-20 fällig [S1/governance.dependencies(D-7).due]. Der Median liegt bei "
                  "39 Tagen [S1/total.median_ct].")
        assert citation_violations(answer, EVIDENCE) == []

    def test_uncited_statement(self) -> None:
        got = citation_violations("D-7 ist gefährdet.", EVIDENCE)
        assert got == ["uncited: D-7 ist gefährdet."]

    def test_unknown_path(self) -> None:
        got = citation_violations("D-7 ist gefährdet [S1/governance.dependencies(D-9).status].", EVIDENCE)
        assert got == ["unknown path: S1/governance.dependencies(D-9).status"]

    def test_number_must_come_from_the_cited_fact_not_anywhere(self) -> None:
        # 41 exists in the contract, but not in the cited fact
        got = citation_violations("Der Median liegt bei 41 Tagen [S1/total.median_ct].", EVIDENCE)
        assert got == ["number not in cited facts: 41"]
        # numbers inside the path itself (IDs, dates) are allowed
        assert citation_violations("Fällig am 2026-10-20 [S1/governance.dependencies(D-7).due].",
                                   EVIDENCE) == []

    def test_unknown_answer_alone_passes_in_every_language(self) -> None:
        for sentence in UNKNOWN_ANSWERS.values():
            assert citation_violations(sentence, EVIDENCE) == []
        assert citation_violations("Zu Beta weiß ich nichts.", EVIDENCE) == ["uncited: Zu Beta weiß ich nichts."]

    def test_error_message_counts(self) -> None:
        err = CitationGuardError(["uncited: a", "uncited: b"])
        assert "2 violation(s)" in str(err) and err.violations == ["uncited: a", "uncited: b"]


class TestCheckIntegration:
    def _bundle(self, lang="de"):
        text = build_bundle("SYS [S1/ ...", CONTRACT, "d3_question", lang=lang,
                            stamp=datetime(2026, 10, 14, 10, 0))
        return parse_bundle(text)

    def test_check_rejects_uncited_and_accepts_cited(self) -> None:
        bundle = self._bundle()
        bad = check_answer("D-7 ist gefährdet und der Median liegt bei 39 Tagen.", bundle)
        assert not bad.passed and bad.violations[0].startswith("Zitat: uncited")
        good = check_answer("D-7 steht auf at_risk [S1/governance.dependencies(D-7).status].", bundle)
        assert good.passed

    def test_other_purposes_skip_the_citation_guard(self) -> None:
        text = build_bundle("S", CONTRACT, "d2_narration")
        assert check_answer("Median 39 Tage, 41 offen.", parse_bundle(text)).passed


class TestPromptAndMock:
    def test_prompt_versions_and_mock_answer(self) -> None:
        from llm.base import discover_providers
        from llm.prompts import question_system_prompt
        de, en = question_system_prompt("de"), question_system_prompt("en")
        assert "[S1/" in de and "[S1/" in en and UNKNOWN_ANSWERS["de"] in de
        assert "ZITIERPFLICHT" in de and "CITATION DUTY" in en
        mock = discover_providers()["mock"]
        assert mock.complete(de, "x", {"lang": "de"}).text == UNKNOWN_ANSWERS["de"]
        assert mock.complete(en, "x", {"lang": "en"}).text == UNKNOWN_ANSWERS["en"]
        assert "ATTRAPPE" in mock.complete("other prompt", "x", {"lang": "de"}).text
