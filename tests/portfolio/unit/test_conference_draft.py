# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       12.10.2026
# Geändert:       12.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Tests zu D8 (KI-Entwurf für die Konferenzmappe): fünf Contracts aus
#   denselben Registern wie die Mappe, ohne Personen; Entwürfe über den
#   Mock-Provider mit Audit-Zweck d8_conference; ein scheiternder Teil
#   fehlt, die anderen stehen; Entwurfsdatei; Platzierung in der Mappe
#   (Einleitung vor dem ersten Block, Absätze unter den Input-Überschriften,
#   fehlender Anker wird übersprungen); CLI-Schalter --conference-draft.
# =============================================================================

from __future__ import annotations

import json
from datetime import date
from unittest.mock import patch

import pytest

from portfolio.capability_config import Capability
from portfolio.conference_draft import (
    PARTS,
    PLACE_FILE,
    PLACE_INLINE,
    PLACES,
    PURPOSE,
    ConferenceDraft,
    conference_contracts,
    draft_conference,
    draft_to_markdown,
    insert_inline,
    part_title,
)
from portfolio.dependency_config import Dependency
from portfolio.flow_problems_config import FlowProblem
from portfolio.report_texts import t
from portfolio.risks_config import Risk
from portfolio.snapshot import Snapshot
from portfolio.solution_config import SolutionConfig
from portfolio.themes_config import Epic, StrategicTheme
from sources.base import SloRecord

TODAY = date(2026, 10, 12)


def _snapshot() -> Snapshot:
    return Snapshot(
        name="Demo Portfolio", kind="portfolio", as_of=TODAY,
        created="2026-10-12T12:00:00", target_ct=90,
        total={"label": "Demo Portfolio", "items": 100, "completed": 75, "open": 25,
               "median_ct": 8.44, "p85_ct": 18.0, "p95_ct": 30.0, "target_ct_pct": 95.0,
               "median_lt": 16.44},
        units=[{"label": "Solution Alpha", "items": 60, "completed": 50, "open": 10,
                "median_ct": 7.0, "p85_ct": 15.0, "p95_ct": 25.0, "target_ct_pct": 97.0,
                "median_lt": 14.0}],
        sources=[{"label": "ART Beta-3", "records": 20, "data_as_of": "2026-07-01",
                  "confidence": "low"}])


def _risk(rid: str, roam: str, owner: str) -> Risk:
    return Risk(risk_id=rid, title=f"Risk {rid}", roam=roam, impact="high", owner=owner)


def _dep(did: str, status: str, due: date | None) -> Dependency:
    return Dependency(dep_id=did, title=f"Dep {did}", from_art="ART A", to_art="ART B",
                      status=status, due=due)


@pytest.fixture
def contracts():
    cfg = SolutionConfig(name="Demo Portfolio", kind="portfolio",
                         conference_date=date(2026, 10, 30))
    flow = [("S", FlowProblem("FP-1", "Shared test environment", "open",
                              ["VS Sales", "VS Service"], source="RTE Sync",
                              owner="Team Platform", conferences=3)),
            ("S", FlowProblem("FP-2", "Release calendar", "resolved", ["VS Sales"],
                              owner="Team Release"))]
    risks = [("S", _risk("BR-2", "owned", "Max Mustermann")),
             ("S", _risk("AR-1", "resolved", "Erika Beispiel"))]
    deps = [("S", _dep("AD-1", "blocked", date(2026, 9, 1))),
            ("S", _dep("AD-2", "on_track", date(2026, 12, 1)))]
    caps = [("S", Capability(cap_id="C1", title="Order Capture", health="degraded",
                             arts=["ART A"]))]
    slos = [("S", SloRecord(service="Order Sync API", slo="p95 < 200 ms",
                            target_pct=99.9, sli_pct=99.5))]
    themes = ([("S", StrategicTheme("T1", "One Checkout")),
               ("S", StrategicTheme("T2", "Forgotten Theme"))],
              [("S", Epic("E1", "New Checkout", "ART A", "P1", theme="T1")),
               ("S", Epic("E2", "Zombie Epic", "ART B", "Y1", theme=""))])
    with patch("portfolio.snapshot.build_snapshot", return_value=_snapshot()), \
         patch("portfolio.aggregator._collect_flow_problems", return_value=flow), \
         patch("portfolio.aggregator._collect_risks", return_value=risks), \
         patch("portfolio.aggregator._collect_dependencies", return_value=deps), \
         patch("portfolio.aggregator._collect_capabilities", return_value=caps), \
         patch("portfolio.aggregator._collect_slo", return_value=slos), \
         patch("portfolio.aggregator._collect_themes", return_value=themes):
        yield conference_contracts(cfg, today=TODAY, log=lambda m: None)


class TestContracts:
    def test_five_parts_in_page_order(self, contracts) -> None:
        assert tuple(contracts) == PARTS == ("intro", "input1", "input2", "input3", "input4")
        for text in contracts.values():
            assert text.startswith("# Conference pre-read contract - Demo Portfolio")
            assert "## Part:" in text

    def test_conference_date_and_lead_time(self, contracts) -> None:
        assert "Conference date: 2026-10-30 (18 days from 2026-10-12)." in contracts["intro"]

    def test_inputs_carry_their_registers(self, contracts) -> None:
        assert "median CT 8.4 d" in contracts["input1"] and "ART Beta-3: low" in contracts["input1"]
        in2 = contracts["input2"]
        assert "flow problems: 2 (open 1, resolved 1)" in in2
        assert "unresolved for 3 or more conferences: 1" in in2
        assert "Shared test environment (conferences 3" in in2
        assert "cross-value-stream problems: 1" in in2
        assert "ROAM risks: 2 (owned 1, resolved 1)" in in2
        assert "dependencies overdue: 1" in in2
        in3 = contracts["input3"]
        assert "capabilities: 1 (degraded 1)" in in3 and "Order Capture: degraded" in in3
        assert "Order Sync API: target 99.9 %, current 99.5 %" in in3
        in4 = contracts["input4"]
        assert "strategic themes: 2, without any epic: 1" in in4
        assert "epics without a strategic theme: 1" in in4 and "Zombie Epic (ART B, Y1)" in in4

    def test_intro_summarises_all_four(self, contracts) -> None:
        intro = contracts["intro"]
        for heading in ("### Current data", "### Impediment backlog",
                        "### Business objectives", "### Roadmap"):
            assert heading in intro
        assert "sources with low confidence: 1 of 1" in intro

    def test_persons_never_reach_a_contract(self, contracts) -> None:
        text = "\n".join(contracts.values())
        for person in ("Max Mustermann", "Erika Beispiel", "RTE Sync", "Team Platform",
                       "Team Release"):
            assert person not in text

    def test_deterministic(self, contracts) -> None:
        assert contracts == dict(contracts)


class TestDraft:
    def test_every_part_drafted_with_mock_and_audited(self, contracts, tmp_path) -> None:
        audit = tmp_path / "llm_audit.jsonl"
        draft = draft_conference(contracts, "mock", lang="en", audit_path=audit,
                                 log=lambda m: None)
        assert set(draft.parts) == set(PARTS) and not draft.failures
        records = [json.loads(line) for line in audit.read_text(encoding="utf-8").splitlines()]
        assert len(records) == 5 and {r["purpose"] for r in records} == {PURPOSE}
        assert PURPOSE == "d8_conference"

    def test_llm_sees_exactly_the_contracts(self, contracts) -> None:
        import llm.narrate as narrate_mod
        seen: list[str] = []
        original = narrate_mod.narrate

        def spy(source_text, **kwargs):
            seen.append(source_text)
            return original(source_text, **kwargs)

        with patch("llm.narrate.narrate", side_effect=spy):
            draft_conference(contracts, "mock", log=lambda m: None)
        assert seen == [contracts[p] for p in PARTS]

    def test_failing_part_is_named_the_rest_stands(self, contracts) -> None:
        import llm.narrate as narrate_mod
        original = narrate_mod.narrate

        def flaky(source_text, **kwargs):
            if "Input 3" in source_text:
                raise RuntimeError("backend gone")
            return original(source_text, **kwargs)

        with patch("llm.narrate.narrate", side_effect=flaky):
            draft = draft_conference(contracts, "mock", lang="en", log=lambda m: None)
        assert set(draft.parts) == {"intro", "input1", "input2", "input4"}
        assert draft.failures == {"input3": "backend gone"}

    def test_numbers_guard_retried_once_then_recorded(self, contracts) -> None:
        from llm.guard import NumbersGuardError
        calls: list[str] = []

        def always_bad(source_text, **kwargs):
            calls.append(source_text)
            raise NumbersGuardError(["42"])

        with patch("llm.narrate.narrate", side_effect=always_bad):
            draft = draft_conference({"intro": contracts["intro"]}, "mock",
                                     log=lambda m: None)
        assert len(calls) == 2 and draft.empty and "intro" in draft.failures

    def test_unknown_provider_fails_every_part(self, contracts) -> None:
        draft = draft_conference(contracts, "nope", log=lambda m: None)
        assert draft.empty and set(draft.failures) == set(PARTS)


class TestOutputs:
    def test_markdown_file_lists_parts_and_failures(self, contracts) -> None:
        draft = draft_conference(contracts, "mock", lang="de", log=lambda m: None)
        draft.failures["input4"] = "backend gone"
        del draft.parts["input4"]
        md = draft_to_markdown(draft, "de")
        assert md.startswith("# Konferenzmappe — KI-Entwürfe zum Redigieren")
        assert "## KI-Entwurf · Einleitung" in md
        assert "## KI-Entwurf · Input 2 · Impediment-Backlog & Governance" in md
        assert "ATTRAPPE" in md and "KI-formulierter Entwurf" in md
        assert "Input 4 · Integrierte Roadmap & Strategic Themes: kein Entwurf: backend gone" in md

    def test_part_titles_follow_the_language(self) -> None:
        assert part_title("intro", "en") == "AI draft · Introduction"
        assert part_title("input1", "fr") == "Brouillon IA · " + t("vsc.input1", "fr")

    def test_inline_places_intro_first_and_parts_under_headings(self, contracts) -> None:
        draft = draft_conference(contracts, "mock", lang="de", log=lambda m: None)
        page = ("<html><body><h1 style='font-size:1.5rem'>Mappe</h1><div>legend</div>"
                "<h1 style='font-size:1.25rem;x'>Input 1 · Aktuelle Daten</h1><p>d</p>"
                "<h1 style='font-size:1.25rem;x'>Input 2 · Impediment-Backlog &amp; Governance</h1><p>e</p>"
                "<h1 style='font-size:1.25rem;x'>Input 4 · Integrierte Roadmap &amp; Strategic Themes</h1>"
                "</body></html>")
        out = insert_inline(page, draft, "de")
        assert out.index("KI-Entwurf · Einleitung") < out.index("Input 1 · Aktuelle Daten")
        assert out.index("KI-Entwurf · Einleitung") > out.index("legend")
        i1 = out.index("Input 1 · Aktuelle Daten</h1>")
        assert out.index("KI-Entwurf · Input 1", i1) < out.index("<p>d</p>")
        assert "KI-Entwurf · Input 3" not in out            # kein Block, kein Anker
        assert out.count('class="sr-ai-draft"') == 4
        assert "KI-formulierter Entwurf" in out              # Banner reist mit

    def test_inline_without_anchors_appends_intro_only(self, contracts) -> None:
        draft = draft_conference(contracts, "mock", log=lambda m: None)
        out = insert_inline("<html><body></body></html>", draft, "de")
        assert out.count('class="sr-ai-draft"') == 1 and "KI-Entwurf · Einleitung" in out

    def test_empty_draft_leaves_the_page_untouched(self) -> None:
        page = "<html><body><h1 style='font-size:1.25rem'>x</h1></body></html>"
        assert insert_inline(page, ConferenceDraft(), "de") == page

    def test_places(self) -> None:
        assert PLACES == (PLACE_FILE, PLACE_INLINE) == ("file", "inline")


class TestPrompt:
    def test_versioned_binding_and_language_pinned(self) -> None:
        from llm.prompts import conference_system_prompt
        de, en = conference_system_prompt("de"), conference_system_prompt("en")
        assert "niemals Personen" in de and "DEUTSCH" in de and "ENTWURF" in de
        assert "never persons" in en and "ENGLISH" in en and "DRAFT" in en
        assert conference_system_prompt("pt") == de
