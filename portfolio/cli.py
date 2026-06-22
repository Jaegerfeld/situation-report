# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       22.06.2026
# Geändert:       22.06.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Kommandozeileninterface für aggregierte Solution-/Portfolio-Reports
#   (Phase 1, Modus "pooled"). Liest eine Solution-Konfiguration, führt die
#   referenzierten ARTs zusammen und schreibt einen gepoolten HTML-Report mit
#   den datums-getriebenen Metriken Flow Velocity und Flow Time.
# =============================================================================

from __future__ import annotations

import argparse
import sys
import webbrowser
from collections.abc import Callable
from pathlib import Path

from build_reports.metrics.flow_time import CT_METHOD_A, CT_METHOD_B
from build_reports.terminology import GLOBAL, SAFE

from .aggregator import render_comparison_html, render_pooled_html
from .solution_config import MODE_COMPARISON, MODE_POOLED, load_solution_config


def run_solution_report(
    config_path: Path,
    output_html: Path | None = None,
    mode: str = MODE_POOLED,
    metrics: list[str] | None = None,
    terminology: str = SAFE,
    ct_method: str = CT_METHOD_A,
    target_ct: int = 90,
    pi_config: Path | None = None,
    open_browser: bool = False,
    log: Callable[[str], None] = print,
) -> str:
    """
    Execute the solution-report pipeline: load config → aggregate → render HTML.

    Args:
        config_path:  Path to the solution-config JSON.
        output_html:  If set, the combined HTML is written here.
        mode:         MODE_POOLED (solution as one system) or MODE_COMPARISON
                      (ARTs side by side).
        metrics:      Metric IDs to run. None = DEFAULT_METRICS.
        terminology:  SAFE or GLOBAL display mode.
        ct_method:    Cycle-time method for Flow Time.
        target_ct:    Target cycle time in days for the Flow Time header.
        pi_config:    Optional PI interval JSON for Flow Velocity.
        open_browser: If True, open the written report in the browser.
        log:          Progress callback.

    Returns:
        The combined HTML string (also written to output_html when given).
    """
    config = load_solution_config(config_path)
    log(f"Solution '{config.name}' ({config.kind}, {config.framework}) "
        f"with {len(config.members)} member(s) — mode: {mode}")

    render = render_comparison_html if mode == MODE_COMPARISON else render_pooled_html
    html = render(
        config,
        metrics=metrics,
        terminology=terminology,
        ct_method=ct_method,
        target_ct=target_ct,
        pi_config=pi_config,
        log=log,
    )
    if not html:
        return ""

    if output_html:
        output_html.parent.mkdir(parents=True, exist_ok=True)
        output_html.write_text(html, encoding="utf-8")
        log(f"Report written to: {output_html}")
        if open_browser:
            webbrowser.open(output_html.resolve().as_uri())

    return html


def main() -> None:
    """Entry point for the portfolio CLI."""
    parser = argparse.ArgumentParser(
        prog="python -m portfolio",
        description="Generate an aggregated (pooled) Large-Solution / Portfolio report.",
    )
    parser.add_argument("config", type=Path,
                        help="Path to the solution-config JSON file.")
    parser.add_argument("--output", type=Path, default=None, metavar="FILE",
                        help="Write the combined HTML report to this file.")
    parser.add_argument("--mode", choices=[MODE_POOLED, MODE_COMPARISON],
                        default=MODE_POOLED,
                        help=f"Aggregation mode (default: {MODE_POOLED}). "
                             f"pooled = solution as one system; "
                             f"comparison = ARTs side by side.")
    parser.add_argument("--metrics", nargs="+", metavar="ID", default=None,
                        help="Metric IDs to compute. Default depends on --mode "
                             "(pooled adds Flow Distribution; comparison also adds "
                             "the stage-dependent Flow Load).")
    parser.add_argument("--terminology", choices=[SAFE, GLOBAL], default=SAFE,
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

    args = parser.parse_args()

    html = run_solution_report(
        config_path=args.config,
        output_html=args.output,
        mode=args.mode,
        metrics=args.metrics,
        terminology=args.terminology,
        ct_method=args.ct_method,
        target_ct=args.target_ct,
        pi_config=args.pi_config,
        open_browser=args.browser,
    )
    if not html:
        print("ERROR: No report produced (no figures).", file=sys.stderr)
        sys.exit(1)
    if not args.output:
        print("Report rendered (no --output given, so nothing was written).")


if __name__ == "__main__":
    main()
