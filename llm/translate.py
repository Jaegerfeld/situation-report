# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       04.09.2026
# Geändert:       04.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   D6 — mehrsprachige Ausleitung: übersetzt einen Lagebild-Text
#   (KI-Entwurf ODER redigierten, freigegebenen Text) in eine der fünf
#   Haussprachen. Läuft vollständig über llm.narrate — damit gelten
#   Zahlen-Wächter (jede Zahl der Übersetzung muss wörtlich in der
#   Vorlage stehen — für Übersetzungen die perfekte Invariante),
#   Art.-50-Banner (in der ZIELsprache) und Betreiber-Nachweis
#   (purpose "d6_translation") unumgehbar auch hier.
# =============================================================================

from __future__ import annotations

from pathlib import Path
from typing import Any

from .narrate import Narration, narrate
from .prompts import TRANSLATION_LANGS, translation_system_prompt


def translate_text(
    source_text: str,
    target_lang: str,
    provider_id: str = "ollama",
    config: dict[str, Any] | None = None,
    audit_path: Path | None = None,
) -> Narration:
    """
    Translate a situational-report text into one house language (D6).

    Args:
        source_text: The text to translate (a labeled draft, or the
                     human-edited final wording).
        target_lang: Target language code (de/en/ro/pt/fr).
        provider_id: LLM backend ("ollama", "claude", "mock", ...).
        config:      Provider config overrides (model, base_url, ...).
        audit_path:  Operator-evidence JSONL (None = no audit record).

    Returns:
        Narration with text and the mandatory AI banner in the TARGET
        language.

    Raises:
        ValueError:        Unknown target language.
        RuntimeError:      Unknown provider or provider failure.
        NumbersGuardError: The translation changed or invented numbers —
                           discarded (evidence still written).
    """
    if target_lang not in TRANSLATION_LANGS:
        raise ValueError(
            f"Unknown target language '{target_lang}' — supported: "
            f"{', '.join(sorted(TRANSLATION_LANGS))}.")
    return narrate(
        source_text, provider_id=provider_id, lang=target_lang,
        config=config, audit_path=audit_path,
        system_prompt=translation_system_prompt(target_lang),
        purpose="d6_translation")
