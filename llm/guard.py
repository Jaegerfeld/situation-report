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
from collections.abc import Mapping

from .base import DEPLOYMENT_EXPORT, DEPLOYMENT_EXTERNAL_ANSWER, LlmResult
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


def question_violations(text: str) -> list[str]:
    """
    The questions guard (D5): every "- " list line must end with "?", and
    at least one question must exist. Returns the offending bullets (empty
    list = text passes); a text without any bullet yields one marker entry.
    Headings and plain lines stay allowed — they group the questions.
    """
    bullets = [line.strip() for line in text.splitlines()
               if line.strip().startswith("- ")]
    offending = [b for b in bullets if not b.rstrip().endswith("?")]
    if not bullets:
        return ["<keine Fragen enthalten>"]
    return offending


#: The one sentence a D3 answer may state without a citation (per language).
UNKNOWN_ANSWERS = {
    "de": "Dazu liegt im Lagebild keine Angabe vor.",
    "en": "The situational picture holds no information on that.",
    "ro": "Tabloul situației nu conține informații despre aceasta.",
    "pt": "O quadro de situação não contém informação sobre isso.",
    "fr": "Le tableau de situation ne contient aucune information à ce sujet.",
}
#: A citation: [S1/total.median_ct], [S0/...], [D/...], [H/...], [E/...] (one-pager
#: cells, M6) - keys use parentheses.
CITATION_RE = re.compile(r"\[((?:S0|S1|D|H|E)/[^\]\n]+)\]")
#: A fact line of the contract: "- [path] label = value (as of ...; source)".
FACT_LINE_RE = re.compile(r"^- \[([^\]\n]+)\] (.*)$", re.M)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-ZÄÖÜ„\"(\[])")
_BULLET_RE = re.compile(r"^(?:[-*•]|\d+[.)])\s+")


def parse_fact_lines(contract: str) -> dict[str, str]:
    """path -> evidence text (path + rest of the line) from a fact-index contract."""
    return {path: f"{path} {rest}" for path, rest in FACT_LINE_RE.findall(contract)}


def statements(text: str) -> list[str]:
    """
    The statements of an answer that must carry citations: list lines and
    sentences of prose. Headings, empty lines and the unknown-answer sentence
    are not statements.
    """
    out: list[str] = []
    unknown = set(UNKNOWN_ANSWERS.values())
    for raw in text.splitlines():
        line = _BULLET_RE.sub("", raw.strip())
        if not line or line.startswith("#"):
            continue
        for piece in _SENTENCE_SPLIT_RE.split(line):
            piece = piece.strip()
            if piece and CITATION_RE.sub("", piece).strip() not in unknown:
                out.append(piece)
    return out


def citation_violations(answer: str, evidence: Mapping[str, str]) -> list[str]:
    """
    The citation guard (D3): every statement cites at least one path that
    exists in the fact index, and every number of the statement occurs in
    the cited facts — not merely somewhere in the contract. Empty list = pass.
    """
    violations: list[str] = []
    for stmt in statements(answer):
        cited = CITATION_RE.findall(stmt)
        if not cited:
            violations.append(f"uncited: {stmt[:90]}")
            continue
        unknown = [c for c in cited if c not in evidence]
        violations += [f"unknown path: {c}" for c in unknown]
        allowed: set[str] = set()
        for c in cited:
            if c in evidence:
                allowed |= extract_numbers(evidence[c])
        loose = extract_numbers(CITATION_RE.sub("", stmt)) - allowed
        violations += [f"number not in cited facts: {n}" for n in sorted(loose)]
    return violations


class CitationGuardError(RuntimeError):
    """Raised when a D3 answer states something it does not cite - discarded."""

    def __init__(self, violations: list[str]) -> None:
        super().__init__(
            "Answer discarded: every statement must cite a fact path of the "
            "stand and every number must come from the cited facts. "
            f"{len(violations)} violation(s): " + " | ".join(violations[:4]))
        self.violations = violations


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


_EXPORT_BANNERS = {
    "de": ("Kein Modell aufgerufen — Prompt exportiert ({path}). Die Antwort eines "
           "externen Modells gilt als ungeprüfter KI-Entwurf und ist vor Verwendung "
           "durch einen Menschen zu redigieren und freizugeben."),
    "en": ("No model called — prompt exported ({path}). An external model's answer "
           "counts as an unreviewed AI draft; a human must edit and approve it before use."),
    "ro": ("Niciun model apelat — prompt exportat ({path}). Răspunsul unui model extern "
           "este o schiță AI neverificată; un om trebuie să o redacteze și să o aprobe."),
    "pt": ("Nenhum modelo chamado — prompt exportado ({path}). A resposta de um modelo "
           "externo é um rascunho de IA não revisto; uma pessoa tem de o redigir e aprovar."),
    "fr": ("Aucun modèle appelé — prompt exporté ({path}). La réponse d'un modèle externe "
           "est un brouillon IA non relu ; une personne doit le réviser et l'approuver."),
}


_EXTERNAL_ANSWER_BANNERS = {
    "de": ("Extern erzeugter KI-Entwurf (Modell laut Bediener: {model}; von llm check gegen "
           "den Contract geprüft) — inhaltlich ungeprüft; vor Verwendung durch einen Menschen "
           "redigieren und freigeben."),
    "en": ("Externally produced AI draft (model as stated by the operator: {model}; checked "
           "against the contract by llm check) — content unreviewed; a human must edit and "
           "approve before use."),
    "ro": ("Schiță AI produsă extern (model declarat de operator: {model}; verificată de llm "
           "check față de contract) — conținut neverificat; un om trebuie să o redacteze și "
           "să o aprobe."),
    "pt": ("Rascunho de IA produzido externamente (modelo indicado pelo operador: {model}; "
           "verificado pelo llm check contra o contrato) — conteúdo não revisto; uma pessoa "
           "tem de o redigir e aprovar."),
    "fr": ("Brouillon IA produit à l'extérieur (modèle indiqué par l'opérateur : {model} ; "
           "vérifié par llm check contre le contrat) — contenu non relu ; une personne doit "
           "le réviser et l'approuver."),
}


def ai_banner_text(result: LlmResult, lang: str = "de") -> str:
    """
    The mandatory AI label for a draft (Art. 50 — always shown until a
    human edits and adopts it; the tool never claims approval). Covers
    the five house languages; unknown codes fall back to German.
    """
    if result.deployment_class == DEPLOYMENT_EXPORT:
        return _EXPORT_BANNERS.get(lang, _EXPORT_BANNERS["de"]).format(
            path=result.endpoint or "-")
    if result.deployment_class == DEPLOYMENT_EXTERNAL_ANSWER:
        return _EXTERNAL_ANSWER_BANNERS.get(lang, _EXTERNAL_ANSWER_BANNERS["de"]).format(
            model=result.model or "-")
    meta = (f"{result.model} @ {result.deployment_class}, "
            f"Prompt {PROMPT_VERSION}")
    return _BANNERS.get(lang, _BANNERS["de"]).format(meta=meta)
