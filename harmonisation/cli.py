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
#   ohne eigene Daten zu sehen.
# =============================================================================

from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path

from .examples import write_example
from .model import LANGS, HarmonisationError, load_workspace
from .render import DEFAULT_LANG, render_html


def run_report(root: Path, output: Path, lang: str = DEFAULT_LANG) -> Path:
    """Load the workspace at ``root`` and write the matrix to ``output``."""
    ws = load_workspace(Path(root))
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_html(ws, lang), encoding="utf-8")
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m harmonisation",
        description="Harmonisation score: decision matrix from a workspace folder "
                    "(catalogue.json, processes.json, assessments/, decisions.json).")
    parser.add_argument("workspace", type=Path,
                        help="Workspace folder (or target folder with --example)")
    parser.add_argument("--output", type=Path, default=None,
                        help="HTML file to write (default: <workspace>/matrix.<lang>.html)")
    parser.add_argument("--lang", choices=LANGS, default=DEFAULT_LANG,
                        help="Report language (default: de)")
    parser.add_argument("--example", action="store_true",
                        help="Write the example workspace into the folder first")
    parser.add_argument("--browser", action="store_true",
                        help="Open the report in the default browser")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.example:
            for path in write_example(args.workspace):
                print(f"written: {path}")
        output = args.output or args.workspace / f"matrix.{args.lang}.html"
        path = run_report(args.workspace, output, args.lang)
    except HarmonisationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"report: {path}")
    if args.browser:
        webbrowser.open(path.resolve().as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())
