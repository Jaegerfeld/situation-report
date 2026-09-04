# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       04.09.2026
# Geändert:       04.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests der mehrsprachigen Ausleitung (D6): versionierter
#   Übersetzungs-Prompt je Haussprache, Banner in allen fünf Sprachen,
#   translate_text über den Wächter-Pfad (Zahlen-Invariante gilt auch
#   für Übersetzungen; Audit purpose d6_translation), das
#   llm-CLI-Subkommando (Dateien je Zielsprache) und die
#   portfolio-CLI-Integration (--translate auf Delta- und Report-Läufen,
#   Entwurf vs. deterministisches Briefing als Quelle).
# =============================================================================

from __future__ import annotations

import json
from datetime import date
from typing import Any
from unittest.mock import patch

import pytest

from llm.base import DEPLOYMENT_MOCK, LlmResult
from llm.guard import NumbersGuardError, ai_banner_text
from llm.prompts import TRANSLATION_LANGS, translation_system_prompt
from llm.translate import translate_text
from portfolio.snapshot import Snapshot, save_snapshot

_RESULT = LlmResult(text="x", provider_id="mock", model="mock-1",
                    deployment_class=DEPLOYMENT_MOCK)


class TestTranslationPromptAndBanners:
    def test_prompt_names_target_and_binds_numbers_and_names(self) -> None:
        for lang, name in TRANSLATION_LANGS.items():
            prompt = translation_system_prompt(lang)
            assert name in prompt and lang in prompt
            assert "unverändert" in prompt and "Eigennamen" in prompt
        with pytest.raises(ValueError, match="Unknown target language"):
            translation_system_prompt("es")

    def test_banner_exists_in_all_five_house_languages(self) -> None:
        markers = {"de": "ungeprüft", "en": "unreviewed",
                   "ro": "neverificată", "pt": "não revisto",
                   "fr": "non relu"}
        banners = set()
        for lang, marker in markers.items():
            banner = ai_banner_text(_RESULT, lang)
            assert marker in banner and "mock-1" in banner
            banners.add(banner)
        assert len(banners) == 5  # wirklich fünf verschiedene Texte


class TestTranslateText:
    def test_guarded_labeled_and_audited(self, tmp_path) -> None:
        audit = tmp_path / "llm_audit.jsonl"
        narration = translate_text("Quelle ohne Zahlenpaare.", "pt",
                                   provider_id="mock", audit_path=audit)
        assert "não revisto" in narration.banner  # Banner in der ZIELsprache
        record = json.loads(audit.read_text(encoding="utf-8"))
        assert record["purpose"] == "d6_translation"
        assert record["guard_passed"] is True

    def test_unknown_target_language_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="Unknown target language"):
            translate_text("text", "es", provider_id="mock")

    def test_numbers_invariant_holds_for_translations(self,
                                                      tmp_path) -> None:
        class BadTranslator:
            provider_id = "bad"
            deployment_class = DEPLOYMENT_MOCK
            default_model = "bad-1"

            def complete(self, system: str, prompt: str,
                         config: dict[str, Any]) -> LlmResult:
                return LlmResult(text="Traduction avec 9999 en trop.",
                                 provider_id="bad", model="bad-1",
                                 deployment_class=DEPLOYMENT_MOCK)

        audit = tmp_path / "llm_audit.jsonl"
        with patch("llm.narrate.discover_providers",
                   return_value={"bad": BadTranslator()}):
            with pytest.raises(NumbersGuardError, match="9999"):
                translate_text("Completed: 12 -> 34", "fr",
                               provider_id="bad", audit_path=audit)
        record = json.loads(audit.read_text(encoding="utf-8"))
        assert record["guard_passed"] is False

    def test_prompt_reaches_the_provider(self) -> None:
        seen: list[str] = []

        class Spy:
            provider_id = "spy"
            deployment_class = DEPLOYMENT_MOCK
            default_model = "spy-1"

            def complete(self, system: str, prompt: str,
                         config: dict[str, Any]) -> LlmResult:
                seen.append(system)
                return LlmResult(text="ok", provider_id="spy",
                                 model="spy-1",
                                 deployment_class=DEPLOYMENT_MOCK)

        with patch("llm.narrate.discover_providers",
                   return_value={"spy": Spy()}):
            translate_text("text", "ro", provider_id="spy")
        assert seen == [translation_system_prompt("ro")]


class TestLlmCliTranslate:
    def test_writes_one_file_per_language(self, tmp_path, capsys) -> None:
        from llm.cli import main
        source = tmp_path / "final.md"
        source.write_text("Freigegebener Text ohne Zahlenpaare.",
                          encoding="utf-8")
        assert main(["translate", str(source), "--to", "en", "fr",
                     "--llm", "mock"]) == 0
        for lang, marker in (("en", "unreviewed"), ("fr", "non relu")):
            out = source.with_suffix(f".md.{lang}.md")
            assert marker in out.read_text(encoding="utf-8")
        lines = (tmp_path / "llm_audit.jsonl").read_text(
            encoding="utf-8").splitlines()
        assert len(lines) == 2
        assert all(json.loads(li)["purpose"] == "d6_translation"
                   for li in lines)

    def test_missing_file_fails_cleanly(self, tmp_path, capsys) -> None:
        from llm.cli import main
        assert main(["translate", str(tmp_path / "fehlt.md"),
                     "--to", "en", "--llm", "mock"]) == 1
        assert "ERROR" in capsys.readouterr().err


class TestPortfolioTranslateFlag:
    def _snaps(self, tmp_path):
        def snap(as_of, completed):
            return Snapshot(
                name="Demo", kind="portfolio", as_of=as_of,
                created="2026-08-30T12:00:00", target_ct=90,
                total={"label": "Demo", "items": 100,
                       "completed": completed, "open": 100 - completed,
                       "median_ct": 8.4, "p85_ct": 18.0, "p95_ct": 30.0,
                       "target_ct_pct": 95.0, "median_lt": 16.4,
                       "p85_lt": 39.0},
                units=[], sources=[],
                governance={"risks": [], "dependencies": [], "nfr": [],
                            "runway": [], "capabilities": [],
                            "decisions": []})
        prev_p = tmp_path / "prev.json"
        now_p = tmp_path / "now.json"
        save_snapshot(prev_p, snap(date(2026, 8, 16), 60))
        save_snapshot(now_p, snap(date(2026, 8, 30), 75))
        return prev_p, now_p

    def test_translates_the_draft_when_narrated(self, tmp_path) -> None:
        from portfolio.cli import run_delta_briefing
        prev_p, now_p = self._snaps(tmp_path)
        out = tmp_path / "delta.md"
        run_delta_briefing(prev_p, now_p, output=out, narrate_with="mock",
                           translate_langs=["en", "ro"],
                           log=lambda m: None)
        en = out.with_suffix(".md.narration.en.md")
        ro = out.with_suffix(".md.narration.ro.md")
        assert "unreviewed" in en.read_text(encoding="utf-8")
        assert "neverificată" in ro.read_text(encoding="utf-8")
        purposes = [json.loads(li)["purpose"] for li in
                    (tmp_path / "llm_audit.jsonl").read_text(
                        encoding="utf-8").splitlines()]
        assert purposes == ["d2_narration", "d6_translation",
                            "d6_translation"]

    def test_translates_the_deterministic_briefing_without_narration(
            self, tmp_path) -> None:
        # Ohne --narrate ist der Übersetzungs-Provider "ollama"
        # (lokal-zuerst); hier per Discovery-Patch auf die Attrappe
        # umgelenkt, damit der Test ohne laufendes Ollama läuft.
        from llm.providers.mock import PROVIDER as MOCK
        from portfolio.cli import run_delta_briefing
        prev_p, now_p = self._snaps(tmp_path)
        out = tmp_path / "delta.md"
        with patch("llm.narrate.discover_providers",
                   return_value={"ollama": MOCK}):
            run_delta_briefing(prev_p, now_p, output=out,
                               translate_langs=["fr"], log=lambda m: None)
        fr = out.with_suffix(".md.fr.md")
        assert "non relu" in fr.read_text(encoding="utf-8")
        assert not out.with_suffix(".md.narration.fr.md").exists()
