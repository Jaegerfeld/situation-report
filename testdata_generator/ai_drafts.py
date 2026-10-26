# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       26.10.2026
# Geändert:       26.10.2026
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

AI_DRAFTS_DIR = "ai_drafts"
PRACTICE_ANSWER = "uebung_antwort_falsch.md"
PRACTICE_README = "uebung_README.md"

#: Questions a trainer would ask the picture (D3), per language.
QUESTIONS: dict[str, list[str]] = {
    "de": [
        "Welche Solution braucht in dieser Woche die Aufmerksamkeit des Portfolios?",
        "Was hat sich seit dem letzten Stand bei den Abhängigkeiten geändert?",
        "Welche Annahme sollten wir vor der nächsten Konferenz prüfen?",
    ],
    "en": [
        "Which solution needs the portfolio's attention this week?",
        "What changed in the dependencies since the last stand?",
        "Which assumption should we check before the next conference?",
    ],
}

#: The practice answer: two numbers that are certainly not in any contract,
#: one real-looking citation path and one uncited claim.
_PRACTICE_TEXT = {
    "de": ("Der Durchsatz des Portfolios liegt bei 4711 Vorgängen [S1/total.items] und ist "
           "damit um 0815 Prozent gestiegen. Solution Alpha ist die beste im Konzern.\n"),
    "en": ("The portfolio's throughput stands at 4711 items [S1/total.items], up by 0815 "
           "percent. Solution Alpha is the best in the group.\n"),
}

_PRACTICE_README = {
    "de": """# Übung: Rückweg mit `llm check`

`{bundle}` ist ein exportiertes Prompt-Bündel (Export-Weg: Prompt in ein externes
Modell kopieren, Antwort zurückholen). `{answer}` ist eine Antwort, wie sie aus einem
Modell kommen könnte — mit zwei Zahlen, die nicht im Contract stehen (4711, 0815), und
einer Behauptung ohne Zitat.

Prüfen:

    python -m llm check {answer} --bundle {bundle}

Erwartung: der Zahlen-Wächter weist beide Zahlen zurück, der Zitat-Wächter die unbelegte
Behauptung; nichts wird als Entwurf abgelegt. Dann dieselbe Prüfung mit einer eigenen,
belegten Antwort versuchen.

Die anderen Dateien in diesem Ordner sind Mock-Entwürfe (kein Modell): Lagevortrag
(`{briefing}`) und drei Antworten (`frage_*.ask.md`), alle mit KI-Marker,
nicht freigegeben. Freigabe üben: `python -m llm approve <datei>`.
""",
    "en": """# Practice: the return path with `llm check`

`{bundle}` is an exported prompt bundle (export path: copy the prompt into an external
model, bring the answer back). `{answer}` is an answer as a model might give it — with two
numbers that are not in the contract (4711, 0815) and a claim without a citation.

Check it:

    python -m llm check {answer} --bundle {bundle}

Expected: the numbers guard rejects both numbers, the citation guard the unbacked claim;
nothing is stored as a draft. Then try the same check with your own, cited answer.

The other files in this folder are mock drafts (no model): the spoken briefing
(`{briefing}`) and three answers (`frage_*.ask.md`), all carrying the AI
marker, none approved. Practise approval: `python -m llm approve <file>`.
""",
}


def _lang_key(lang: str) -> str:
    return "de" if lang == "de" else "en"


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
    key = _lang_key(lang)
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
    for i, question in enumerate(QUESTIONS[key], start=1):
        res = run_ask(config, question, drafts_dir / f"frage_{i}.ask.md", provider_id="mock",
                      lang=lang, snapshot=now, prev_snapshot=prev, reference=reference, log=quiet)
        asks.append(res.written or drafts_dir / f"frage_{i}.ask.md")

    # Export path: a prompt bundle for the return path, plus a wrong practice answer.
    run_ask(config, QUESTIONS[key][0], drafts_dir / "uebung_frage.ask.md", provider_id="export",
            lang=lang, snapshot=now, prev_snapshot=prev, reference=reference, log=quiet)
    bundle = find_bundle(drafts_dir, "d3_question")
    practice = drafts_dir / PRACTICE_ANSWER
    practice.write_text(_PRACTICE_TEXT[key], encoding="utf-8")
    readme = drafts_dir / PRACTICE_README
    readme.write_text(_PRACTICE_README[key].format(
        bundle=f"{AI_DRAFTS_DIR}/{bundle.name}" if bundle else f"{AI_DRAFTS_DIR}/prompt_d3_question_*.md",
        answer=f"{AI_DRAFTS_DIR}/{PRACTICE_ANSWER}",
        briefing=f"{AI_DRAFTS_DIR}/{briefing_path.name}"), encoding="utf-8")

    log(f"  KI-Entwürfe (Mock): Lagevortrag, {len(asks)} Antworten, Prompt-Bündel, "
        f"Übungsantwort -> {AI_DRAFTS_DIR}/")
    return {"dir": drafts_dir, "onepager": page_path, "briefing": briefing_path, "asks": asks,
            "bundle": bundle, "practice_answer": practice, "practice_readme": readme,
            "audit": audit}
