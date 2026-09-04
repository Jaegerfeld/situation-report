# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       04.09.2026
# Geändert:       04.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   D5 — Red-Team-Assistent: Premortem-/Annahmen-Angriffs-Fragen aus dem
#   Decision-/Assumption-Log (B4), als Rohmaterial für menschlich
#   moderierte Sessions. Die Zuordnung der KI-Denkschrift ist hart:
#   D5 liefert NUR Rohmaterial für das Urteil — kein Empfehlungs-Button.
#   Deshalb wird „nur Fragen“ hier MASCHINELL erzwungen: Der
#   Fragen-Wächter verwirft jede Ausgabe, deren Listenzeilen nicht als
#   Frage enden — zusätzlich zu Zahlen-Wächter, Art.-50-Banner und
#   Audit aus llm/narrate.py (purpose d5_red_team).
# =============================================================================

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .decision_config import KIND_ASSUMPTION, LogEntry

if TYPE_CHECKING:  # pragma: no cover - nur fuer Typen
    from .solution_config import SolutionConfig


def decision_log_to_markdown(entries: list[tuple[str, LogEntry]]) -> str:
    """
    The deterministic red-team contract: the decision/assumption log as
    Markdown (teams only — the log's owner fields ARE teams by rule).
    """
    lines = ["# Decision/Assumption Log - Red-Team Input"]
    for source, entry in entries:
        kind = ("assumption" if entry.kind == KIND_ASSUMPTION
                else "decision")
        line = (f"- [{source}] {entry.entry_id} ({kind}, {entry.status}): "
                f"{entry.title}")
        if entry.owner:
            line += f" — owner: {entry.owner}"
        if entry.logged_on:
            line += f" — logged {entry.logged_on.isoformat()}"
        if entry.review_by:
            line += f" — review by {entry.review_by.isoformat()}"
        if entry.supersedes:
            line += f" — supersedes {entry.supersedes}"
        lines.append(line)
    return "\n".join(lines)


class QuestionsOnlyError(RuntimeError):
    """Raised when a red-team draft contains non-question list lines."""

    def __init__(self, offending: list[str]) -> None:
        super().__init__(
            "Red-team draft discarded: it contains list lines that are "
            "not questions — D5 delivers raw material for judgement, "
            "never judgements. Offending line(s): "
            + " | ".join(offending[:3]))
        self.offending = offending


def enforce_questions(text: str) -> None:
    """
    The questions guard: every "- " list line must end with "?", and at
    least one question must exist. Headings/plain lines stay allowed
    (grouping per entry ID), statements-as-bullets are discarded.
    """
    bullets = [line.strip() for line in text.splitlines()
               if line.strip().startswith("- ")]
    offending = [b for b in bullets if not b.rstrip().endswith("?")]
    if offending or not bullets:
        raise QuestionsOnlyError(offending or ["<keine Fragen enthalten>"])


def run_red_team(
    config: SolutionConfig,
    output: Path,
    provider_id: str = "ollama",
    lang: str = "de",
    llm_model: str | None = None,
    log: Callable[[str], None] = print,
) -> Any:
    """
    Generate the red-team question draft for a config's decision log.

    Writes ``output`` (Markdown with the Art.-50 banner in ``lang``) and
    the operator evidence next to it; returns the Narration.

    Raises:
        ValueError:         The config references no decision log.
        NumbersGuardError:  Invented numbers — discarded (evidence kept).
        QuestionsOnlyError: Non-question output — discarded.
        RuntimeError:       Provider failures.
    """
    from llm.audit import AUDIT_FILENAME
    from llm.narrate import narrate
    from llm.prompts import red_team_system_prompt

    from .aggregator import _collect_decisions

    entries = _collect_decisions(config, log=log)
    if not entries:
        raise ValueError(
            "No decision/assumption log referenced — the red-team "
            "assistant needs the B4 register (config field 'decisions').")
    contract = decision_log_to_markdown(entries)
    log(f"Red-team questions via '{provider_id}' "
        f"({len(entries)} log entries) ...")
    narration = narrate(
        contract, provider_id=provider_id, lang=lang,
        config={"model": llm_model} if llm_model else None,
        audit_path=output.parent / AUDIT_FILENAME,
        system_prompt=red_team_system_prompt(lang),
        purpose="d5_red_team")
    # Zweiter, D5-spezifischer Wächter NACH den zentralen Wächtern:
    # nur Fragen verlassen das Werkzeug.
    enforce_questions(narration.text)
    output.write_text(
        f"> {narration.banner}\n\n{narration.text}\n", encoding="utf-8")
    log(f"Red-team question draft (for human moderation): {output}")
    return narration
