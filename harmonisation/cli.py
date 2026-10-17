# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       12.10.2026
# Geändert:       12.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Kommandozeile des Harmonisierungs-Scores: einen Arbeitsbereich laden
#   und die Entscheider-Matrix als HTML schreiben; mit --example einen
#   Beispiel-Arbeitsbereich anlegen, um das Format und die Oberfläche
#   ohne eigene Daten zu sehen. Seit Schritt 2 (12.10.2026): --since bzw.
#   --delta schreiben statt der Matrix die Veränderung zweier Stände, und
#   --narrate hängt an Matrix oder Veränderung die gekennzeichnete KI-Lesart
#   (Entwurf) an — mit separater .reading.md zum Redigieren und dem
#   Betreiber-Nachweis llm_audit.jsonl neben der Ausgabe. Scheitert die KI,
#   bleibt die deterministische Seite stehen; der Rückgabewert sagt es.
# =============================================================================

from __future__ import annotations

import argparse
import sys
import webbrowser
from collections.abc import Callable
from datetime import date
from pathlib import Path

from .delta import compute_delta, delta_to_markdown, filter_as_of
from .examples import write_example
from .model import LANGS, HarmonisationError, Workspace, load_workspace
from .reading import attach_reading, matrix_to_markdown, reading_markdown, reading_title
from .render import DEFAULT_LANG, render_delta_html, render_html

#: Exit code when the deterministic page was written but the AI draft failed.
EXIT_NO_DRAFT = 3


def _attach(html: str, contract: str, output: Path, lang: str, narrate_with: str,
            llm_model: str | None, llm_base_url: str | None,
            log: Callable[[str], None]) -> tuple[str, bool]:
    """Add the labeled reading; on failure keep the page and say so."""
    from llm.audit import AUDIT_FILENAME
    from llm.guard import NumbersGuardError

    try:
        html, narration = attach_reading(
            html, contract, provider_id=narrate_with, lang=lang,
            llm_model=llm_model, llm_base_url=llm_base_url,
            audit_path=output.parent / AUDIT_FILENAME, log=log)
    except (RuntimeError, NumbersGuardError) as exc:
        log(f"WARNING: AI reading skipped - {exc}")
        return html, False
    draft = output.with_name(output.stem + ".reading.md")
    draft.write_text(reading_markdown(narration, reading_title(lang), lang), encoding="utf-8")
    log(f"draft: {draft}")
    return html, True


def run_report(root: Path, output: Path, lang: str = DEFAULT_LANG,
               narrate_with: str | None = None, llm_model: str | None = None,
               llm_base_url: str | None = None,
               log: Callable[[str], None] = print) -> tuple[Path, bool]:
    """
    Load the workspace at ``root`` and write the matrix to ``output``.

    Returns the path and whether everything asked for was produced (False
    only when an AI reading was requested and failed; the page exists
    regardless).
    """
    ws = load_workspace(Path(root))
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    html = render_html(ws, lang)
    complete = True
    if narrate_with:
        html, complete = _attach(html, matrix_to_markdown(ws), output, lang, narrate_with,
                                 llm_model, llm_base_url, log)
    output.write_text(html, encoding="utf-8")
    return output, complete


def run_delta(root: Path, output: Path, lang: str = DEFAULT_LANG,
              since: date | None = None, prev_root: Path | None = None,
              narrate_with: str | None = None, llm_model: str | None = None,
              llm_base_url: str | None = None,
              log: Callable[[str], None] = print) -> tuple[Path, bool]:
    """
    Write the change between an earlier state and the workspace at ``root``.

    The earlier state is the same workspace as of ``since`` (assessments
    are dated) or a second workspace folder ``prev_root``; exactly one of
    the two must be given.
    """
    if (since is None) == (prev_root is None):
        raise HarmonisationError("delta needs exactly one of --since DATE or --delta FOLDER")
    now = load_workspace(Path(root))
    if since is not None:
        prev: Workspace = filter_as_of(now, since)
        label_prev = since.isoformat()
    else:
        prev = load_workspace(Path(prev_root))  # type: ignore[arg-type]
        label_prev = Path(prev_root).name  # type: ignore[arg-type]
    delta = compute_delta(prev, now, label_prev, date.today().isoformat())
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    html = render_delta_html(delta, now, lang)
    complete = True
    if narrate_with:
        html, complete = _attach(html, delta_to_markdown(delta, now), output, lang,
                                 narrate_with, llm_model, llm_base_url, log)
    output.write_text(html, encoding="utf-8")
    return output, complete


def _parse_day(text: str) -> date:
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{text!r} is not YYYY-MM-DD") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m harmonisation",
        description="Harmonisation score: decision matrix from a workspace folder "
                    "(catalogue.json, processes.json, assessments/, decisions.json); "
                    "with --since or --delta the change between two states instead.")
    parser.add_argument("workspace", type=Path,
                        help="Workspace folder (or target folder with --example)")
    parser.add_argument("--output", type=Path, default=None,
                        help="HTML file to write (default: <workspace>/matrix.<lang>.html, "
                             "for a delta <workspace>/delta.<lang>.html)")
    parser.add_argument("--lang", choices=LANGS, default=DEFAULT_LANG,
                        help="Report language (default: de)")
    parser.add_argument("--example", action="store_true",
                        help="Write the example workspace into the folder first")
    parser.add_argument("--browser", action="store_true",
                        help="Open the report in the default browser")
    state = parser.add_mutually_exclusive_group()
    state.add_argument("--since", type=_parse_day, default=None, metavar="DATE",
                       help="Change since this date (YYYY-MM-DD): the workspace as it stood "
                            "then versus now - assessments are dated")
    state.add_argument("--delta", type=Path, default=None, metavar="FOLDER", dest="prev_root",
                       help="Change against a second workspace folder (the earlier state)")
    parser.add_argument("--narrate", nargs="?", const="ollama", default=None,
                        metavar="PROVIDER",
                        help="Add the AI reading (draft) below the matrix or the change "
                             "table via this llm provider (default when given: ollama). "
                             "Labeled as a draft, numbers guarded, separate "
                             "<output>.reading.md to edit, llm_audit.jsonl next to the output.")
    parser.add_argument("--llm-model", default=None, dest="llm_model",
                        help="Model override for --narrate (default: the provider's)")
    parser.add_argument("--llm-base-url", default=None, dest="llm_base_url",
                        help="Backend address override for --narrate (ollama)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    delta_mode = args.since is not None or args.prev_root is not None
    try:
        if args.example:
            for path in write_example(args.workspace):
                print(f"written: {path}")
        if delta_mode:
            output = args.output or args.workspace / f"delta.{args.lang}.html"
            path, complete = run_delta(
                args.workspace, output, args.lang, since=args.since,
                prev_root=args.prev_root, narrate_with=args.narrate,
                llm_model=args.llm_model, llm_base_url=args.llm_base_url)
            print(f"delta: {path}")
        else:
            output = args.output or args.workspace / f"matrix.{args.lang}.html"
            path, complete = run_report(
                args.workspace, output, args.lang, narrate_with=args.narrate,
                llm_model=args.llm_model, llm_base_url=args.llm_base_url)
            print(f"report: {path}")
    except HarmonisationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.browser:
        webbrowser.open(path.resolve().as_uri())
    return 0 if complete else EXIT_NO_DRAFT


if __name__ == "__main__":
    sys.exit(main())
