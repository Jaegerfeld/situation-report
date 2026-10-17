# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       12.10.2026
# Geändert:       12.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   KI-Lesart der Entscheider-Matrix (P3 Schritt 2, nach dem D1-Muster):
#   der deterministische Lesart-Contract — je Prozess und Dimension Score,
#   Zahl der Bewertungen, beantwortete Fragen, Konfidenz, Spanne, dazu die
#   Entscheidung des Boards — als Markdown-Eingabe für die KI-Schicht, und
#   das Einfügen des gekennzeichneten Entwurfs DIREKT UNTER der Matrix.
#   Zahlen entstehen ausschließlich in score.py; das LLM formuliert nur
#   (Zahlen-Wächter, Art.-50-Banner und Audit kommen unumgehbar aus
#   llm/narrate.py). Der Contract nennt Prozesse, Dimensionen und Marken —
#   nie Personen: Owner und Befragte tauchen in ihm gar nicht auf. Der
#   Prompt untersagt zusätzlich jede Empfehlung, was harmonisiert wird.
# =============================================================================

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

from .model import DECISION_OPEN, Workspace
from .score import matrix

#: Audit purpose tag of every harmonisation reading (matrix and delta).
PURPOSE = "p3_reading"

#: Section titles of the labeled draft, per house language.
_TITLES = {
    "de": "KI-Lesart (Entwurf)",
    "en": "AI reading (draft)",
    "ro": "Lectură AI (schiță)",
    "pt": "Leitura por IA (rascunho)",
    "fr": "Lecture IA (brouillon)",
}


def reading_title(lang: str) -> str:
    return _TITLES.get(lang, _TITLES["en"])


def _num(value: float | None) -> str:
    return "none" if value is None else f"{value:g}"


def matrix_to_markdown(ws: Workspace, today: date | None = None) -> str:
    """
    The deterministic reading contract (the only input the LLM sees).

    Processes with their brands, per dimension the cell summary, and the
    board's decision. Owners and assessors are deliberately absent.
    """
    today = today or date.today()
    cells = matrix(ws)
    lines = [
        f"# Harmonisation reading contract - {ws.catalogue.name}",
        f"As of {today.isoformat()}. Scores are 0-100 per dimension (mean of the answered "
        f"questions, median over several assessments); confidence is the share of documented "
        f"answers (high/medium/low); spread is highest minus lowest assessment.",
        "",
    ]
    from llm.guard import text_as_data
    for p in ws.processes:
        # Leitplanke (e): process names, brands and the board's depth are data, never instructions
        brands = f" (brands: {', '.join(text_as_data(b, 60) for b in p.brands)})" if p.brands else ""
        lines.append(f"## {text_as_data(p.name, 120)}{brands}")
        for d in ws.catalogue.dimensions:
            c = cells[p.id][d.id]
            if c.score is None:
                lines.append(f"- {d.label('en')}: no assessment")
                continue
            spread = f", spread {c.spread:g}" if c.spread is not None else ""
            lines.append(
                f"- {d.label('en')}: score {c.score:g}, {c.assessments} assessment(s), "
                f"{c.answered}/{c.total} answered, confidence {c.confidence}{spread}")
        dec = ws.decisions.get(p.id)
        if dec is None or (dec.decision == DECISION_OPEN and not dec.depth):
            lines.append("- board decision: open")
        else:
            text = f"- board decision: {dec.decision}"
            if dec.depth:
                text += f' (depth: "{text_as_data(dec.depth)}")'
            if dec.day:
                text += f" on {dec.day.isoformat()}"
            lines.append(text)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def reading_html_section(narration: Any, title: str) -> str:
    """
    The labeled draft block: mandatory AI banner (Art. 50) plus the text —
    the same markup as the portfolio drafts, so the labeling reads alike
    across modules.
    """
    from llm.guard import ai_html_section
    return ai_html_section(narration, PURPOSE, title)


def insert_after_first_table(html_doc: str, section_html: str) -> str:
    """
    Place the draft directly below the first table (the matrix or the
    change table). Falls back to just above the footer, then to the end —
    a page variant without a table must never lose the draft.
    """
    end = html_doc.find("</table>")
    if end != -1:
        end += len("</table>")
        return html_doc[:end] + section_html + html_doc[end:]
    if "<footer>" in html_doc:
        return html_doc.replace("<footer>", section_html + "<footer>", 1)
    if "</body></html>" in html_doc:
        return html_doc.replace("</body></html>", section_html + "</body></html>", 1)
    return html_doc + section_html


def attach_reading(
    html_doc: str,
    contract: str,
    provider_id: str,
    lang: str = "de",
    llm_model: str | None = None,
    llm_base_url: str | None = None,
    audit_path: Path | None = None,
    attempts: int = 2,
    log: Callable[[str], None] = print,
) -> tuple[str, Any]:
    """
    Draft the reading of ``contract`` and insert it below the first table.

    Shared by CLI and GUI so the labeling can never diverge. Returns the
    page with the labeled draft plus the Narration (for the separate
    ``.reading.md`` editing file). A numbers-guard rejection is retried
    once by default; every attempt is written to the operator evidence.

    Raises:
        RuntimeError:      Unknown provider or provider failure.
        NumbersGuardError: Every attempt invented numbers.
    """
    from llm.base import provider_config
    from llm.guard import NumbersGuardError
    from llm.narrate import narrate
    from llm.prompts import harmonisation_system_prompt

    for attempt in range(1, max(1, attempts) + 1):
        log(f"AI reading via '{provider_id}' (attempt {attempt}) ...")
        try:
            narration = narrate(
                contract, provider_id=provider_id, lang=lang,
                config=provider_config(llm_model, llm_base_url),
                audit_path=audit_path,
                system_prompt=harmonisation_system_prompt(lang),
                purpose=PURPOSE)
        except NumbersGuardError:
            if attempt >= max(1, attempts):
                raise
            log("  numbers guard rejected the draft - retrying once")
            continue
        from llm.guard import add_ai_meta
        section = reading_html_section(narration, reading_title(lang))
        return add_ai_meta(insert_after_first_table(html_doc, section)), narration
    raise AssertionError("unreachable")  # pragma: no cover


def reading_markdown(narration: Any, title: str, lang: str = "de") -> str:
    """The editing file: title, machine-readable marker, banner, then the draft."""
    from llm.guard import draft_markdown
    return f"# {title}\n\n{draft_markdown(narration, PURPOSE, lang)}"
