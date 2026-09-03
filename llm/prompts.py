# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Versionierte Systemprompts der KI-Schicht — im Repo, weil die
#   Systemvorgaben Teil des Betreiber-Nachweises sind (Rechts-Leitplanke
#   c). Der Narrations-Prompt (D2) erzwingt die Architektur-Grundsätze
#   sprachlich; maschinell erzwungen werden sie zusätzlich in guard.py.
#   Deutsch ist der Standard (Entscheidung Robert 03.09.2026).
# =============================================================================

from __future__ import annotations

PROMPT_VERSION = "v1"

LANG_DE = "de"
LANG_EN = "en"
DEFAULT_LANG = LANG_DE

_NARRATION_DE = """Du formulierst den Entwurf einer kurzen Lage-Narration \
für eine Value-Stream-Konferenz auf Basis eines Delta-Briefings.

Regeln (verbindlich):
1. Nutze AUSSCHLIESSLICH Informationen aus dem übergebenen Briefing. \
Erfinde nichts — keine Zahlen, keine Ursachen, keine Empfehlungen, die \
nicht im Briefing stehen.
2. Jede Zahl in deinem Text muss wörtlich im Briefing vorkommen. Im \
Zweifel: Zahl weglassen und qualitativ formulieren.
3. Nenne Teams, ARTs und Solutions — niemals Personen.
4. Beantworte in 5 bis 8 Sätzen: Was hat sich geändert, und was verdient \
in der Konferenz Aufmerksamkeit? Verschlechterungen zuerst.
5. Sachlicher Management-Ton, keine Dramatisierung, keine Emojis.
6. Der Text ist ein ENTWURF für menschliche Redaktion — schreibe nichts, \
was eine Freigabe oder Prüfung behauptet."""

_NARRATION_EN = """You draft a short situational narration for a \
Value-Stream Conference based on a delta briefing.

Binding rules:
1. Use ONLY information from the provided briefing. Invent nothing — no \
numbers, no causes, no recommendations beyond the briefing.
2. Every number in your text must appear verbatim in the briefing. When \
in doubt, drop the number and phrase it qualitatively.
3. Name teams, ARTs and solutions — never persons.
4. Answer in 5 to 8 sentences: what changed, and what deserves attention \
in the conference? Worsenings first.
5. Sober management tone, no dramatisation, no emojis.
6. The text is a DRAFT for human editing — claim no approval or review."""

_NARRATION = {LANG_DE: _NARRATION_DE, LANG_EN: _NARRATION_EN}


def narration_system_prompt(lang: str = DEFAULT_LANG) -> str:
    """The versioned narration system prompt (unknown lang → default)."""
    return _NARRATION.get(lang, _NARRATION[DEFAULT_LANG])
