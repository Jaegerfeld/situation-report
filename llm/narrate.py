# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Orchestrierung einer Narration (D2 Teil 2): Provider auflösen →
#   versionierten Systemprompt anwenden → generieren → Zahlen-Wächter →
#   Betreiber-Nachweis schreiben → gekennzeichnetes Ergebnis zurückgeben.
#   Die Wächter sind hier verdrahtet, damit KEIN Aufrufer sie umgehen
#   kann, ohne dieses Modul zu meiden.
# =============================================================================

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .audit import append_audit
from .base import LlmResult, discover_providers
from .guard import NumbersGuardError, ai_banner_text, enforce_numbers
from .prompts import DEFAULT_LANG, narration_system_prompt


@dataclass
class Narration:
    """A guarded, labeled narration draft."""
    text: str
    banner: str
    result: LlmResult


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
    system = (system_prompt if system_prompt is not None
              else narration_system_prompt(lang))
    result = provider.complete(system, source_text, cfg)

    try:
        enforce_numbers(result.text, source_text)
    except NumbersGuardError:
        if audit_path is not None:
            append_audit(audit_path, result, source_text, purpose,
                         guard_passed=False)
        raise
    if audit_path is not None:
        append_audit(audit_path, result, source_text, purpose,
                     guard_passed=True)
    return Narration(text=result.text,
                     banner=ai_banner_text(result, lang), result=result)
