# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests des KI-Frameworks selbst: Auto-Discovery (eine Datei =
#   ein Provider), versionierte Prompts, der Zahlen-Wächter („das LLM
#   textet, es rechnet nicht"), die Pflicht-Kennzeichnung (Art. 50) und
#   der Betreiber-Nachweis (JSONL, NUR Hashes — nie Volltexte, nie
#   Schlüssel).
# =============================================================================

from __future__ import annotations

import hashlib
import json

import pytest

from llm.audit import append_audit
from llm.base import (
    DEPLOYMENT_EXTERNAL,
    DEPLOYMENT_LOCAL,
    DEPLOYMENT_MOCK,
    LlmResult,
    discover_providers,
)
from llm.guard import (
    NumbersGuardError,
    ai_banner_text,
    enforce_numbers,
    extract_numbers,
    verify_numbers,
)
from llm.prompts import PROMPT_VERSION, narration_system_prompt

_RESULT = LlmResult(text="Beispieltext.", provider_id="mock",
                    model="mock-1", deployment_class=DEPLOYMENT_MOCK,
                    duration_s=1.234)


class TestDiscovery:
    def test_ships_ollama_claude_and_mock(self) -> None:
        providers = discover_providers()
        assert set(providers) >= {"ollama", "claude", "mock"}
        for provider_id, provider in providers.items():
            assert provider.provider_id == provider_id

    def test_deployment_classes_and_defaults(self) -> None:
        providers = discover_providers()
        assert providers["ollama"].deployment_class == DEPLOYMENT_LOCAL
        assert providers["ollama"].default_model == "mistral-nemo"
        assert providers["claude"].deployment_class == DEPLOYMENT_EXTERNAL
        assert providers["claude"].default_model == "claude-sonnet-5"
        assert providers["mock"].deployment_class == DEPLOYMENT_MOCK


class TestPrompts:
    def test_versioned_and_language_specific(self) -> None:
        de = narration_system_prompt("de")
        en = narration_system_prompt("en")
        assert de != en
        assert "Zahl" in de and "niemals Personen" in de
        assert "verbatim" in en and "never persons" in en
        # Unbekannte Sprache fällt auf den Standard (Deutsch) zurück.
        assert narration_system_prompt("fr") == de
        assert PROMPT_VERSION == "v1"


class TestNumbersGuard:
    def test_extract_normalises_separators(self) -> None:
        assert extract_numbers("99,5 % vs 99.5 und 1.234,5") == {
            "995", "12345"}

    def test_single_digits_are_prose_not_metrics(self) -> None:
        assert extract_numbers("1. Punkt, 2 Saetze, Team 7") == set()

    def test_verify_flags_only_invented_numbers(self) -> None:
        source = "Completed: 12 -> 34; CFR 38 %"
        assert verify_numbers("34 Items fertig, CFR bei 38.", source) == []
        assert verify_numbers("Wir schafften 500 Items.", source) == ["500"]

    def test_enforce_raises_with_violations(self) -> None:
        with pytest.raises(NumbersGuardError, match="invented number"):
            enforce_numbers("Es sind 77 offen.", "Completed: 12")
        try:
            enforce_numbers("Es sind 77 offen.", "Completed: 12")
        except NumbersGuardError as exc:
            assert exc.violations == ["77"]


class TestAiBanner:
    def test_names_model_deployment_and_prompt_version(self) -> None:
        for lang, marker in (("de", "ungeprüft"), ("en", "unreviewed")):
            banner = ai_banner_text(_RESULT, lang)
            assert "mock-1" in banner
            assert DEPLOYMENT_MOCK in banner
            assert PROMPT_VERSION in banner
            assert marker in banner

    def test_never_claims_approval(self) -> None:
        for lang in ("de", "en"):
            banner = ai_banner_text(_RESULT, lang).lower()
            assert "freigegeben" not in banner
            assert "approved" not in banner


class TestAudit:
    def test_record_holds_hashes_never_texts(self, tmp_path) -> None:
        path = tmp_path / "audit" / "llm_audit.jsonl"
        append_audit(path, _RESULT, "GEHEIMES BRIEFING 42",
                     purpose="d2_narration", guard_passed=True)
        raw = path.read_text(encoding="utf-8")
        assert "GEHEIMES BRIEFING" not in raw
        assert "Beispieltext" not in raw
        record = json.loads(raw)
        assert record["purpose"] == "d2_narration"
        assert record["provider"] == "mock"
        assert record["model"] == "mock-1"
        assert record["deployment_class"] == DEPLOYMENT_MOCK
        assert record["prompt_version"] == PROMPT_VERSION
        assert record["guard_passed"] is True
        assert record["duration_s"] == 1.23
        assert record["input_sha256"] == hashlib.sha256(
            b"GEHEIMES BRIEFING 42").hexdigest()
        assert record["output_sha256"] == hashlib.sha256(
            b"Beispieltext.").hexdigest()

    def test_appends_one_line_per_call(self, tmp_path) -> None:
        path = tmp_path / "llm_audit.jsonl"
        append_audit(path, _RESULT, "a", purpose="p", guard_passed=True)
        append_audit(path, _RESULT, "b", purpose="p", guard_passed=False)
        lines = path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        assert json.loads(lines[1])["guard_passed"] is False


class TestOutputLanguageIsPinned:
    """Praxisbefund 04.09.2026 (mistral-nemo am Demo-Portfolio): der
    Contract/das Briefing ist englisch beschriftet — ohne explizite
    Regel antwortete das Modell trotz --llm-lang de auf Englisch.
    Jeder Prompt fixiert die Ausgabesprache jetzt selbst."""

    def test_every_prompt_family_pins_its_language(self) -> None:
        from llm.prompts import (
            exec_summary_system_prompt,
            narration_system_prompt,
            red_team_system_prompt,
        )
        for prompt in (narration_system_prompt, exec_summary_system_prompt,
                       red_team_system_prompt):
            assert "DEUTSCH" in prompt("de"), prompt.__name__
            assert "ENGLISH" in prompt("en"), prompt.__name__

    def test_translation_prompt_names_the_target_language(self) -> None:
        from llm.prompts import TRANSLATION_LANGS, translation_system_prompt
        for code, name in TRANSLATION_LANGS.items():
            assert name in translation_system_prompt(code)
