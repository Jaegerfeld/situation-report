# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       22.06.2026
# Geändert:       02.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Kommandozeileninterface für aggregierte Solution-/Portfolio-Reports in
#   beiden Modi: "pooled" (Solution als ein System) und "comparison" (Einheiten
#   nebeneinander). Liest eine Solution-Konfiguration, aggregiert die
#   referenzierten ARTs und schreibt HTML- und/oder PDF-Reports. Zusätzlich
#   D2: --snapshot friert den Report-Zustand als JSON ein, --delta vergleicht
#   zwei Snapshots zum Delta-Briefing („Was hat sich geändert?").
# =============================================================================

from __future__ import annotations

import argparse
import sys
import webbrowser
from collections.abc import Callable
from datetime import date
from pathlib import Path

from build_reports.metrics.flow_time import CT_METHOD_A, CT_METHOD_B
from build_reports.terminology import GLOBAL, SAFE

from .aggregator import render_comparison_html, render_pdf, render_pooled_html
from .solution_config import MODE_COMPARISON, MODE_POOLED, load_solution_config


def run_solution_report(
    config_path: Path,
    output_html: Path | None = None,
    output_pdf: Path | None = None,
    mode: str = MODE_POOLED,
    metrics: list[str] | None = None,
    terminology: str | None = None,
    ct_method: str = CT_METHOD_A,
    target_ct: int = 90,
    pi_config: Path | None = None,
    open_browser: bool = False,
    log: Callable[[str], None] = print,
) -> str:
    """
    Execute the solution-report pipeline: load config → aggregate → render.

    Args:
        config_path:  Path to the solution-config JSON.
        output_html:  If set, the combined HTML is written here.
        output_pdf:   If set, a multi-page PDF is written here.
        mode:         MODE_POOLED (solution as one system) or MODE_COMPARISON
                      (units side by side).
        metrics:      Metric IDs to run. None = mode default.
        terminology:  SAFE or GLOBAL display mode.
        ct_method:    Cycle-time method for Flow Time.
        target_ct:    Target cycle time in days for the Flow Time header.
        pi_config:    Optional PI interval JSON for Flow Velocity.
        open_browser: If True, open the written HTML report in the browser.
        log:          Progress callback.

    Returns:
        The combined HTML string (empty if HTML was not generated). PDF output,
        when requested, is written as a side effect.
    """
    config = load_solution_config(config_path)
    # The CLI --terminology overrides the config; otherwise the config's own
    # terminology is used.
    if terminology is None:
        terminology = config.terminology
    log(f"Solution '{config.name}' ({config.kind}, {config.framework}) "
        f"with {len(config.members)} member(s) — mode: {mode}")

    if output_pdf:
        render_pdf(
            config, output_pdf, mode=mode, metrics=metrics, terminology=terminology,
            ct_method=ct_method, target_ct=target_ct, pi_config=pi_config, log=log)

    # Generate HTML when explicitly requested, or when no other output was asked
    # for (so a bare run still produces the report string).
    html = ""
    if output_html or not output_pdf:
        render = render_comparison_html if mode == MODE_COMPARISON else render_pooled_html
        html = render(
            config, metrics=metrics, terminology=terminology, ct_method=ct_method,
            target_ct=target_ct, pi_config=pi_config, log=log)
        if html and output_html:
            output_html.parent.mkdir(parents=True, exist_ok=True)
            output_html.write_text(html, encoding="utf-8")
            log(f"Report written to: {output_html}")
            if open_browser:
                webbrowser.open(output_html.resolve().as_uri())

    return html


def run_delta_briefing(
    prev_path: Path,
    now_path: Path,
    output: Path | None = None,
    open_browser: bool = False,
    log: Callable[[str], None] = print,
) -> None:
    """
    Compare two snapshot files and emit the delta briefing (D2).

    Args:
        prev_path:    Earlier snapshot JSON.
        now_path:     Later snapshot JSON.
        output:       Destination file — ``*.md`` writes Markdown, any other
                      suffix writes the HTML page; None prints Markdown.
        open_browser: Open a written HTML file in the default browser.
        log:          Progress callback.
    """
    from .delta import compute_delta, delta_to_markdown, render_delta_html
    from .snapshot import load_snapshot

    delta = compute_delta(load_snapshot(prev_path), load_snapshot(now_path))
    if output is None:
        text = delta_to_markdown(delta)
        try:
            print(text)
        except UnicodeEncodeError:
            # Windows-Konsole mit Legacy-Codepage (cp1252): UTF-8 erzwingen.
            sys.stdout.buffer.write(text.encode("utf-8") + b"\n")
            sys.stdout.buffer.flush()
        return
    if output.suffix.lower() == ".md":
        output.write_text(delta_to_markdown(delta), encoding="utf-8")
    else:
        output.write_text(render_delta_html(delta), encoding="utf-8")
        if open_browser:
            webbrowser.open(output.resolve().as_uri())
    log(f"Delta briefing written: {output}")


def main() -> None:
    """Entry point for the portfolio CLI."""
    parser = argparse.ArgumentParser(
        prog="python -m portfolio",
        description="Generate an aggregated (pooled) Large-Solution / Portfolio report.",
    )
    parser.add_argument("config", type=Path, nargs="?", default=None,
                        help="Path to the solution-config JSON file "
                             "(not needed with --delta).")
    parser.add_argument("--output", type=Path, default=None, metavar="FILE",
                        help="Write the combined HTML report to this file.")
    parser.add_argument("--pdf", type=Path, default=None, metavar="FILE",
                        help="Write a multi-page PDF report to this file.")
    parser.add_argument("--mode", choices=[MODE_POOLED, MODE_COMPARISON],
                        default=MODE_POOLED,
                        help=f"Aggregation mode (default: {MODE_POOLED}). "
                             f"pooled = solution as one system; "
                             f"comparison = ARTs side by side.")
    parser.add_argument("--metrics", nargs="+", metavar="ID", default=None,
                        help="Metric IDs to compute. Default depends on --mode "
                             "(pooled adds Flow Distribution; comparison also adds "
                             "the stage-dependent Flow Load).")
    parser.add_argument("--terminology", choices=[SAFE, GLOBAL], default=None,
                        help=f"Terminology mode (default: {SAFE}).")
    parser.add_argument("--ct-method", choices=[CT_METHOD_A, CT_METHOD_B],
                        default=CT_METHOD_A, dest="ct_method",
                        help="Cycle time method: A=date diff, B=sum of stage minutes.")
    parser.add_argument("--target-ct", type=int, default=90, dest="target_ct",
                        metavar="DAYS", help="Cycle time target in days (default: 90).")
    parser.add_argument("--pi-config", type=Path, default=None, dest="pi_config",
                        metavar="FILE", help="JSON PI interval config for Flow Velocity.")
    parser.add_argument("--browser", action="store_true",
                        help="Open the written report in the default browser.")
    parser.add_argument("--snapshot", type=Path, default=None, metavar="FILE",
                        help="Freeze the report state (metrics, quality, "
                             "governance) into this snapshot JSON (D2). "
                             "Without --output/--pdf, only the snapshot is "
                             "written.")
    parser.add_argument("--as-of", type=date.fromisoformat, default=None,
                        dest="as_of", metavar="YYYY-MM-DD",
                        help="Observation date recorded in the snapshot "
                             "(default: today).")
    parser.add_argument("--delta", nargs=2, type=Path, default=None,
                        metavar=("PREV", "NOW"),
                        help="Compare two snapshot files and write the delta "
                             "briefing: --output *.md = Markdown, --output "
                             "otherwise = HTML, no --output = Markdown to "
                             "stdout. Needs no config.")
    parser.add_argument("--conference", type=Path, default=None,
                        metavar="FILE",
                        help="Write the Value-Stream-Conference pre-read "
                             "(Konferenzmappe, B6) to this HTML file: the "
                             "conference inputs in meeting order, printable.")
    parser.add_argument("--conference-date", type=date.fromisoformat,
                        default=None, dest="conference_date",
                        metavar="YYYY-MM-DD",
                        help="Conference date shown in the pre-read header "
                             "(default: today).")

    args = parser.parse_args()

    if args.delta:
        run_delta_briefing(args.delta[0], args.delta[1],
                           output=args.output, open_browser=args.browser)
        return
    if args.config is None:
        parser.error("config is required (except with --delta).")

    if args.snapshot:
        from .snapshot import write_snapshot_for_config
        write_snapshot_for_config(
            args.config, args.snapshot,
            as_of=args.as_of, target_ct=args.target_ct)
        if not args.output and not args.pdf and not args.conference:
            return

    if args.conference:
        from .aggregator import render_conference_html
        html_doc = render_conference_html(
            load_solution_config(args.config),
            conference_date=args.conference_date)
        args.conference.write_text(html_doc, encoding="utf-8")
        print(f"Conference pre-read written: {args.conference}")
        if args.browser:
            webbrowser.open(args.conference.resolve().as_uri())
        if not args.output and not args.pdf:
            return

    html = run_solution_report(
        config_path=args.config,
        output_html=args.output,
        output_pdf=args.pdf,
        mode=args.mode,
        metrics=args.metrics,
        terminology=args.terminology,
        ct_method=args.ct_method,
        target_ct=args.target_ct,
        pi_config=args.pi_config,
        open_browser=args.browser,
    )
    if not html and not args.pdf:
        print("ERROR: No report produced (no figures).", file=sys.stderr)
        sys.exit(1)
    if not args.output and not args.pdf:
        print("Report rendered (no --output/--pdf given, so nothing was written).")


if __name__ == "__main__":
    main()
