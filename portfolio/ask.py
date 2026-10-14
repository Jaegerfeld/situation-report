# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       14.10.2026
# Geändert:       14.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Befragbares Lagebild (Roadmap D3, Entscheidungen Robert 14.10.2026):
#   Eine Frage an EINEN Stand des Lagebilds. Der Stand wird zum Fakten-Index
#   (portfolio/facts.py), der Index ist der einzige Kontext des Modells, und
#   die Antwort muss jede Aussage mit einem Pfad-Zitat belegen — der
#   Zitat-Wächter (llm/guard.py) verwirft alles andere. „Dazu liegt im
#   Lagebild keine Angabe vor." ist die zulässige Unbekannt-Antwort.
#   Hygiene-Vorgabe (KI-Denkschrift Prinzip 7): die eigene Einschätzung des
#   Fragenden wird VOR der Antwort erfasst, steht in der Ausgabe neben ihr
#   und geht nie ans Modell. Keine Empfehlung, keine Bewertung — D3 erklärt
#   (Vorhersage/Feedback), es urteilt nicht. Läuft über llm.narrate: Zahlen-
#   Wächter, Banner, Betreiber-Nachweis (Zweck d3_question), Provider frei,
#   auch export (Rückweg llm check prüft dann die Zitate).
# =============================================================================

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from llm.audit import AUDIT_FILENAME, append_audit
from llm.base import DEPLOYMENT_EXPORT, LlmResult, provider_config
from llm.guard import CitationGuardError, citation_violations
from llm.narrate import narrate
from llm.prompts import question_system_prompt

from .facts import QUESTION_LIMIT, FactIndex, build_fact_index, sanitize_text
from .snapshot import Snapshot, build_snapshot
from .solution_config import SolutionConfig

PURPOSE = "d3_question"
ASK_SUFFIX = ".ask.md"

_T = {
    "de": {"title": "Frage an das Lagebild", "question": "Frage", "own": "Eigene Einschätzung (vor der Antwort)",
           "skipped": "— (übersprungen)", "answer": "Antwort (KI-Entwurf)", "stand": "Stand",
           "facts": "Fakten im Index", "digest": "Index-Prüfsumme (SHA-256)", "model": "Modell"},
    "en": {"title": "Question to the situational picture", "question": "Question",
           "own": "Own assessment (before the answer)", "skipped": "— (skipped)",
           "answer": "Answer (AI draft)", "stand": "Stand", "facts": "Facts in the index",
           "digest": "Index checksum (SHA-256)", "model": "Model"},
}


def _t(lang: str, key: str) -> str:
    return _T.get(lang, _T["en"])[key]


@dataclass
class AskResult:
    """One answered (or rejected) question with everything the file needs."""
    question: str
    own_view: str
    answer: str
    banner: str
    index: FactIndex
    result: LlmResult
    written: Path | None = None

    @property
    def exported(self) -> bool:
        return self.result.deployment_class == DEPLOYMENT_EXPORT


def question_contract(index: FactIndex, question: str) -> str:
    """The deterministic input: the question, then the whole fact index."""
    return (f"# Question-Contract - {index.name} ({index.kind})\n"
            f"Question: {question}\n\n{index.to_markdown()}\n")


def _harmonisation_workspaces(config: Any, log: Callable[[str], None]) -> list[tuple[str, Any]]:
    try:
        from .aggregator import _collect_harmonisation
        return _collect_harmonisation(config, log=log)
    except Exception:  # noqa: BLE001 - a bare/mocked config simply has no workspace
        return []


def ask_question(
    config: SolutionConfig | Any,
    question: str,
    provider_id: str = "ollama",
    lang: str = "de",
    own_view: str = "",
    snapshot: Snapshot | None = None,
    prev_snapshot: Snapshot | None = None,
    reference: date | None = None,
    target_ct: int = 90,
    scope: str = "all",
    audit_path: Path | None = None,
    llm_model: str | None = None,
    llm_base_url: str | None = None,
    log: Callable[[str], None] = print,
) -> AskResult:
    """
    Ask one question about one stand of the situational picture.

    Args:
        config:        Solution/portfolio config (used to build the stand and
                       to find harmonisation workspaces).
        question:      The question (free text, bounded; control chars removed).
        provider_id:   LLM backend; "export" writes the prompt bundle instead.
        lang:          Answer language (de/en; the banner knows five).
        own_view:      The asker's own assessment — kept out of the model.
        snapshot:      A saved stand to ask about (default: build live).
        prev_snapshot: Earlier stand → S0/… and D/… facts.
        reference:     as_of for a live stand (default today).
        scope:         Fact-index scope ("all", "metrics", "registers").
        audit_path:    Operator evidence (default: none).

    Raises:
        ValueError:         Empty question or unknown scope.
        NumbersGuardError:  A number outside the contract (from narrate).
        CitationGuardError: An uncited statement, an unknown path or a number
                            that the cited facts do not carry — answer discarded.
        RuntimeError:       Provider failure.
    """
    quiet: Callable[[str], None] = lambda m: None  # noqa: E731
    clean_question = sanitize_text(question, QUESTION_LIMIT)
    if not clean_question:
        raise ValueError("The question is empty.")
    snap = snapshot or build_snapshot(config, as_of=reference, target_ct=target_ct, log=quiet)
    harmonisation = _harmonisation_workspaces(config, quiet) if scope == "all" else []
    index = build_fact_index(snap, prev=prev_snapshot, harmonisation=harmonisation, scope=scope,
                             lang=lang)
    contract = question_contract(index, clean_question)
    log(f"Question to stand {index.as_of} via '{provider_id}' ({len(index)} facts) ...")
    narration = narrate(contract, provider_id=provider_id, lang=lang,
                        config=provider_config(llm_model, llm_base_url),
                        audit_path=audit_path, purpose=PURPOSE,
                        system_prompt=question_system_prompt(lang))
    if narration.result.deployment_class != DEPLOYMENT_EXPORT:
        violations = citation_violations(narration.text, index.evidence_map())
        if violations:
            if audit_path is not None:
                append_audit(audit_path, narration.result, contract, PURPOSE, guard_passed=False)
            raise CitationGuardError(violations)
    return AskResult(question=clean_question, own_view=sanitize_text(own_view, 2000),
                     answer=narration.text, banner=narration.banner, index=index,
                     result=narration.result)


def ask_to_markdown(res: AskResult, lang: str = "de") -> str:
    """The .ask.md file: question, own assessment, labelled answer, provenance."""
    key = "de" if lang == "de" else "en"
    own_hash = hashlib.sha256(res.own_view.encode("utf-8")).hexdigest()[:16] if res.own_view else "-"
    lines = [f"# {_t(key, 'title')} — {res.index.name} ({res.index.as_of})", "",
             f"**{_t(key, 'question')}:** {res.question}", "",
             f"**{_t(key, 'own')}:** {res.own_view or _t(key, 'skipped')}", "",
             f"> {res.banner}", "",
             f"## {_t(key, 'answer')}", "", res.answer.strip(), "", "---",
             f"{_t(key, 'stand')}: S1 = {res.index.as_of}"
             + (f", S0 = {res.index.prev_as_of}" if res.index.prev_as_of else "")
             + f" · {_t(key, 'facts')}: {len(res.index)} · {_t(key, 'digest')}: {res.index.digest()}"
             + f" · {_t(key, 'model')}: {res.result.model} @ {res.result.deployment_class}"
             + f" · own-view hash: {own_hash}", ""]
    return "\n".join(lines)


def run_ask(
    config: SolutionConfig | Any,
    question: str,
    output: Path,
    provider_id: str = "ollama",
    lang: str = "de",
    own_view: str = "",
    snapshot: Snapshot | None = None,
    prev_snapshot: Snapshot | None = None,
    reference: date | None = None,
    target_ct: int = 90,
    scope: str = "all",
    llm_model: str | None = None,
    llm_base_url: str | None = None,
    log: Callable[[str], None] = print,
) -> AskResult:
    """Ask, then write the .ask.md next to ``output`` with the audit beside it."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    res = ask_question(config, question, provider_id=provider_id, lang=lang, own_view=own_view,
                       snapshot=snapshot, prev_snapshot=prev_snapshot, reference=reference,
                       target_ct=target_ct, scope=scope, audit_path=output.parent / AUDIT_FILENAME,
                       llm_model=llm_model, llm_base_url=llm_base_url, log=log)
    output.write_text(ask_to_markdown(res, lang), encoding="utf-8")
    res.written = output
    log(f"Answer written (draft for human review): {output}")
    return res
