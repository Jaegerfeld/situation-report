# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       13.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Orchestrierung einer Narration (D2 Teil 2): Provider auflösen →
#   versionierten Systemprompt anwenden → generieren → Zahlen-Wächter →
#   Betreiber-Nachweis schreiben → gekennzeichnetes Ergebnis zurückgeben.
#   Die Wächter sind hier verdrahtet, damit KEIN Aufrufer sie umgehen
#   kann, ohne dieses Modul zu meiden. Seit 13.10.2026 kennt der Pfad den
#   Provider "export" (kein Modell, Prompt-Bündel in Datei und
#   Zwischenablage): Zweck und Ausgabeordner wandern in die Provider-Config,
#   der Zahlen-Wächter überspringt den Platzhalter, Banner und Nachweis
#   sagen, dass kein Modell lief.
# =============================================================================

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .audit import append_audit
from .base import DEPLOYMENT_EXPORT, LlmResult, discover_providers
from .guard import NumbersGuardError, ai_banner_text, enforce_numbers, instruction_smells
from .prompts import DEFAULT_LANG, narration_system_prompt


@dataclass
class Narration:
    """A guarded, labeled narration draft."""
    text: str
    banner: str
    result: LlmResult
    #: Contract lines that read like instructions (Leitplanke e) - a warning, not a verdict.
    warnings: list[str] = field(default_factory=list)


def narrate(
    source_text: str,
    provider_id: str = "ollama",
    lang: str = DEFAULT_LANG,
    config: dict[str, Any] | None = None,
    audit_path: Path | None = None,
    purpose: str = "d2_narration",
    system_prompt: str | None = None,
) -> Narration:
    """
    Generate the narration draft for a deterministic briefing text.

    Args:
        source_text: The deterministic input (e.g. delta_to_markdown()).
        provider_id: LLM backend ("ollama", "claude", "mock", ...).
        lang:        Narration language (default: de).
        config:      Provider config overrides (model, base_url, ...).
        audit_path:  Operator-evidence JSONL (None = no audit record).
        purpose:     Audit purpose tag.
        system_prompt: Versioned system prompt override (None = the D2
                     narration prompt). Guards and audit apply regardless
                     of the prompt — they are wired here, not per prompt.

    Returns:
        Narration with the mandatory AI banner.

    Raises:
        RuntimeError:      Unknown provider or provider failure.
        NumbersGuardError: The model invented numbers — text discarded
                           (an audit record with guard_passed=False is
                           still written).
    """
    providers = discover_providers()
    provider = providers.get(provider_id)
    if provider is None:
        raise RuntimeError(
            f"Unknown llm provider '{provider_id}' — known: "
            f"{', '.join(providers)}.")

    cfg = dict(config or {})
    cfg.setdefault("lang", lang)
    # The export provider needs to know what this call is and where the
    # output lives - every other provider ignores both keys.
    cfg.setdefault("purpose", purpose)
    if audit_path is not None:
        cfg.setdefault("export_dir", str(Path(audit_path).parent))
    # Leitplanke (e): free text that reads like an instruction is noted, not
    # removed - the contract stays data, the evidence records the count.
    smells = instruction_smells(source_text)
    cfg.setdefault("contract_warnings", len(smells))
    system = (system_prompt if system_prompt is not None
              else narration_system_prompt(lang))
    result = provider.complete(system, source_text, cfg)

    try:
        # An exported prompt carries no model text - the placeholder names a
        # file path, nothing a numbers guard could judge.
        if result.deployment_class != DEPLOYMENT_EXPORT:
            enforce_numbers(result.text, source_text)
    except NumbersGuardError:
        if audit_path is not None:
            append_audit(audit_path, result, source_text, purpose,
                         guard_passed=False, contract_warnings=len(smells))
        raise
    if audit_path is not None:
        append_audit(audit_path, result, source_text, purpose,
                     guard_passed=True, contract_warnings=len(smells))
    return Narration(text=result.text, banner=ai_banner_text(result, lang),
                     result=result, warnings=smells)
