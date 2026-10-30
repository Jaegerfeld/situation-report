# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       26.10.2026
# Geändert:       30.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   KI-Entwürfe für den Demo-Datenraum (Beta, Entscheidung F3 vom
#   26.10.2026): nur mit Schalter, standardmäßig aus. Mit dem Mock-Provider
#   (kein Modell, keine Installation) entstehen in `ai_drafts/` ein
#   Einseiter mit Lagevortrag-Entwurf (M6), drei Antworten auf Fragen ans
#   Lagebild (D3), ein Prompt-Bündel (Export-Weg) und eine Übungsantwort
#   mit absichtlich falschen Zahlen — damit sich Marker (R3), Freigabe
#   (`llm approve`) und Rückweg (`llm check`) schulen lassen. Alle Entwürfe
#   tragen den KI-Marker und sind nicht freigegeben; der Nachweis landet in
#   `ai_drafts/llm_audit.jsonl`, getrennt von der Betreiber-Ebene.
#
#   Eingabe und Ergebnis bleiben getrennt: der Datenraum ist die Eingabe,
#   `ai_drafts/` ist das, was die Suite daraus macht — in einem eigenen
#   Ordner, damit niemand Erfundenes mit Erzeugtem verwechselt.
# =============================================================================

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

from .i18n import t as _t

AI_DRAFTS_DIR = "ai_drafts"
PRACTICE_ANSWER = "uebung_antwort_falsch.md"
PRACTICE_README = "uebung_README.md"

def questions(lang: str) -> list[str]:
    """The three questions a trainer would ask the picture (D3), in ``lang``."""
    return [_t("drafts.q1", lang), _t("drafts.q2", lang), _t("drafts.q3", lang)]


def write_ai_drafts(
    out: Path,
    paths: dict[str, Any],
    reference: date,
    lang: str = "de",
    log: Callable[[str], None] = print,
) -> dict[str, Any]:
    """
    Write the mock AI drafts of one portfolio data room into ``out/ai_drafts/``.

    Args:
        out:       The portfolio's data-room folder (holds portfolio.json).
        paths:     The build result of that portfolio (portfolio, snapshot_now,
                   snapshot_prev).
        reference: The room's reference date (the "now" stand).
        lang:      Draft language ("de"/"en"; others fall back to English texts
                   for the practice files, the drafts follow ``lang``).
        log:       Progress callback.

    Returns:
        {"dir", "onepager", "briefing", "asks": [...], "bundle", "practice_answer",
         "practice_readme", "audit"}.
    """
    from llm.audit import AUDIT_FILENAME
    from llm.check import find_bundle
    from portfolio.ask import run_ask
    from portfolio.briefing import write_briefing
    from portfolio.onepager import build_onepager, render_onepager_html
    from portfolio.snapshot import load_snapshot
    from portfolio.solution_config import load_solution_config

    quiet: Callable[[str], None] = lambda m: None
    drafts_dir = Path(out) / AI_DRAFTS_DIR
    drafts_dir.mkdir(parents=True, exist_ok=True)
    audit = drafts_dir / AUDIT_FILENAME

    config = load_solution_config(Path(paths["portfolio"]))
    now = load_snapshot(Path(paths["snapshot_now"]))
    prev = load_snapshot(Path(paths["snapshot_prev"]))

    # M6: one-pager plus the spoken-briefing draft (mock).
    page = build_onepager(config, lang=lang, prev_snapshot=prev, reference=reference, log=quiet)
    page_path = drafts_dir / "einseiter.html"
    page_path.write_text(render_onepager_html(page, lang), encoding="utf-8")
    briefing_path, _ = write_briefing(page, config, page_path, provider_id="mock", lang=lang,
                                      prev_snapshot=prev, audit_path=audit, log=quiet)

    # D3: three questions answered by the mock.
    asks: list[Path] = []
    for i, question in enumerate(questions(lang), start=1):
        res = run_ask(config, question, drafts_dir / f"frage_{i}.ask.md", provider_id="mock",
                      lang=lang, snapshot=now, prev_snapshot=prev, reference=reference, log=quiet)
        asks.append(res.written or drafts_dir / f"frage_{i}.ask.md")

    # Export path: a prompt bundle for the return path, plus a wrong practice answer.
    run_ask(config, questions(lang)[0], drafts_dir / "uebung_frage.ask.md", provider_id="export",
            lang=lang, snapshot=now, prev_snapshot=prev, reference=reference, log=quiet)
    bundle = find_bundle(drafts_dir, "d3_question")
    practice = drafts_dir / PRACTICE_ANSWER
    practice.write_text(_t("drafts.practice_text", lang), encoding="utf-8")
    readme = drafts_dir / PRACTICE_README
    readme.write_text(_t(
        "drafts.practice_readme", lang,
        bundle=f"{AI_DRAFTS_DIR}/{bundle.name}" if bundle else f"{AI_DRAFTS_DIR}/prompt_d3_question_*.md",
        answer=f"{AI_DRAFTS_DIR}/{PRACTICE_ANSWER}",
        briefing=f"{AI_DRAFTS_DIR}/{briefing_path.name}"), encoding="utf-8")

    log(_t("log.drafts", lang, n=len(asks)))
    return {"dir": drafts_dir, "onepager": page_path, "briefing": briefing_path, "asks": asks,
            "bundle": bundle, "practice_answer": practice, "practice_readme": readme,
            "audit": audit}
