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


def _canonical(number: str) -> str:
    """
    Canonical form of one number token for comparison.

    Separators vary between the deterministic input and free-form prose
    (99,5 vs 99.5 vs 99 %), so they are dropped. Insignificant trailing
    zeros of a decimal fraction are dropped too: a contract saying
    "median CT 39.0 d" and a draft saying "39 Tage" state the SAME
    number, and flagging that as invented was a false alarm (field
    report 04.09.2026 — five rejected drafts in a row on a portfolio
    whose metrics happened to be whole numbers).

    A last group of exactly three digits is read as a thousands
    separator (1.234 → 1234), anything else as a decimal fraction
    (39.0 → 39, 103.5 → 1035).
    """
    groups = re.split(r"[.,]", number)
    if len(groups) == 1:
        return groups[0]
    if len(groups[-1]) == 3:  # Tausendertrenner
        return "".join(groups)
    integer, fraction = "".join(groups[:-1]), groups[-1].rstrip("0")
    return integer + fraction


def extract_numbers(text: str) -> set[str]:
    """
    All numbers of a text, normalised for comparison (see _canonical).

    Single digits are ignored — enumerations ("1.", "2 Sätze") are prose,
    not metrics, and would cause false alarms.
    """
    numbers = set()
    for match in _NUMBER_RE.findall(text):
        canonical = _canonical(match)
        if len(canonical) >= 2:
            numbers.add(canonical)
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
