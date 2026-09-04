# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Die Wächter der KI-Schicht — Grundsätze werden hier MASCHINELL
#   durchgesetzt, nicht dokumentiert:
#   - Zahlen-Wächter: „Das LLM textet, es rechnet nicht" — jede Zahl im
#     generierten Text muss aus dem Quelltext (dem deterministischen
#     Briefing) stammen, sonst wird der Text verworfen statt still
#     halluziniert.
#   - Kennzeichnung (Art. 50 KI-VO): Jede Narration trägt sichtbar den
#     Entwurfs-/KI-Hinweis mit Modell und Deployment-Klasse. Das
#     Werkzeug behauptet NIE eine Freigabe — die hebt erst der Mensch
#     auf, der den Entwurf redigiert und übernimmt.
# =============================================================================

from __future__ import annotations

import re

from .base import LlmResult
from .prompts import PROMPT_VERSION

#: Numbers incl. decimal comma/point and thousands separators (1.234,5).
_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)*")


def extract_numbers(text: str) -> set[str]:
    """
    All numbers of a text, normalised for comparison.

    Normalisation keeps only the digits (separators vary between the
    deterministic briefing and free-form prose: 99,5 vs 99.5 vs 99 %).
    Single digits are ignored — enumerations ("1.", "2 Sätze") are prose,
    not metrics, and would cause false alarms.
    """
    numbers = set()
    for match in _NUMBER_RE.findall(text):
        digits = re.sub(r"\D", "", match)
        if len(digits) >= 2:
            numbers.add(digits)
    return numbers


def verify_numbers(generated: str, source: str) -> list[str]:
    """
    The numbers guard: return every number in ``generated`` that does not
    occur in ``source`` (empty list = text passes).
    """
    allowed = extract_numbers(source)
    return sorted(extract_numbers(generated) - allowed)


class NumbersGuardError(RuntimeError):
    """Raised when a generated text invents numbers — the text is discarded."""

    def __init__(self, violations: list[str]) -> None:
        super().__init__(
            "Narration discarded: the model invented number(s) "
            f"{', '.join(violations)} that do not occur in the briefing. "
            "The LLM writes, it does not calculate — re-run, switch the "
            "model, or use the deterministic briefing as is.")
        self.violations = violations


def enforce_numbers(generated: str, source: str) -> None:
    """Raise NumbersGuardError when the generated text invents numbers."""
    violations = verify_numbers(generated, source)
    if violations:
        raise NumbersGuardError(violations)


#: Banner texts per house language ({meta} = model @ deployment, prompt).
_BANNERS = {
    "de": ("KI-formulierter Entwurf ({meta}) — ungeprüft; vor Verwendung "
           "durch einen Menschen redigieren und freigeben."),
    "en": ("AI-drafted ({meta}) — unreviewed draft; a human must edit "
           "and approve before use."),
    "ro": ("Schiță formulată de AI ({meta}) — neverificată; un om trebuie "
           "să o redacteze și să o aprobe înainte de utilizare."),
    "pt": ("Rascunho formulado por IA ({meta}) — não revisto; uma pessoa "
           "tem de o redigir e aprovar antes da utilização."),
    "fr": ("Brouillon formulé par IA ({meta}) — non relu ; une personne "
           "doit le réviser et l'approuver avant utilisation."),
}


def ai_banner_text(result: LlmResult, lang: str = "de") -> str:
    """
    The mandatory AI label for a draft (Art. 50 — always shown until a
    human edits and adopts it; the tool never claims approval). Covers
    the five house languages; unknown codes fall back to German.
    """
    meta = (f"{result.model} @ {result.deployment_class}, "
            f"Prompt {PROMPT_VERSION}")
    return _BANNERS.get(lang, _BANNERS["de"]).format(meta=meta)
