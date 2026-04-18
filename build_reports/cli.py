# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       15.04.2026
# Geändert:       18.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Kommandozeileninterface für build_reports. Liest IssueTimes- und CFD-XLSX,
#   wendet optionale Filter an, berechnet die gewählten Metriken und exportiert
#   die Ergebnisse als PDF oder öffnet sie im Browser. Unterstützt SAFe- und
#   Global-Terminologie sowie Auswahl einzelner oder aller Metriken.
# =============================================================================

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from datetime import date
from pathlib import Path

import plotly.io as pio

from .export import export_pdf, write_report_excel, write_zero_day_excel
from .filters import FilterConfig, apply_filters
from .loader import load_report_data
from .metrics import all_metrics, get_metric
from .metrics.flow_time import CT_METHOD_A, CT_METHOD_B, FlowTimeMetric
from .metrics.flow_velocity import FlowVelocityMetric
from .terminology import GLOBAL, SAFE


def _parse_date(value: str) -> date:
    """
    Parse a date string in YYYY-MM-DD format for argparse.

    Args:
        value: Date string from the command line.

    Returns:
        Parsed date object.

    Raises:
        argparse.ArgumentTypeError: If the format is invalid.
    """
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid date '{value}' — expected YYYY-MM-DD format."
        )


def run_reports(
    issue_times: Path,
    cfd: Path | None = None,
    metrics: list[str] | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    projects: list[str] | None = None,
    issuetypes: list[str] | None = None,
    terminology: str = SAFE,
    ct_method: str = CT_METHOD_A,
    pi_config: Path | None = None,
    output_pdf: Path | None = None,
    open_browser: bool = False,
    log: Callable[[str], None] = print,
) -> None:
    """
    Execute the full build_reports pipeline: load → filter → compute → output.

    Called by both the CLI (main) and the GUI. The log parameter accepts
    any callable that takes a single string — defaults to print for CLI use.

    Args:
        issue_times:  Path to IssueTimes.xlsx (required).
        cfd:          Path to CFD.xlsx (optional, needed for CFD metric).
        metrics:      List of metric IDs to run. None or empty = all metrics.
        from_date:    Filter: include only issues closed on or after this date.
        to_date:      Filter: include only issues closed on or before this date.
        projects:     Filter: restrict to these project keys (empty = all).
        issuetypes:   Filter: restrict to these issue types (empty = all).
        terminology:  Display mode — SAFE or GLOBAL.
        ct_method:    Cycle time calculation method: CT_METHOD_A (date diff)
                      or CT_METHOD_B (sum of stage minutes).
        pi_config:    Path to a JSON PI interval config file (optional).
                      If None, quarterly intervals are used for Flow Velocity.
        output_pdf:   If set, export all figures to this PDF file.
        open_browser: If True, open each figure in the default browser.
        log:          Callable for progress/warning output.
    """
    log(f"Loading data from {issue_times.name} ...")
    data = load_report_data(issue_times, cfd)
    log(f"  {len(data.issues)} issues, {len(data.cfd)} CFD days, "
        f"{len(data.stages)} stages loaded.")

    cfg = FilterConfig(
        from_date=from_date,
        to_date=to_date,
        projects=projects or [],
        issuetypes=issuetypes or [],
    )
    data = apply_filters(data, cfg)
    log(f"  After filters: {len(data.issues)} issues, {len(data.cfd)} CFD days.")

    # Resolve which metrics to run
    if metrics:
        plugins = []
        for mid in metrics:
            try:
                plugins.append(get_metric(mid))
            except KeyError:
                log(f"WARNING: Unknown metric '{mid}' — skipped.")
    else:
        plugins = all_metrics()

    # Configure per-plugin settings
    for plugin in plugins:
        if isinstance(plugin, FlowTimeMetric):
            plugin.ct_method = ct_method
        if isinstance(plugin, FlowVelocityMetric):
            plugin.pi_config_path = str(pi_config) if pi_config else ""

    all_figures = []
    all_results = []
    for plugin in plugins:
        log(f"Computing {plugin.metric_id} ...")
        result = plugin.compute(data, terminology)
        all_results.append(result)
        for w in result.warnings:
            log(f"  WARNING: {w}")
        figures = plugin.render(result, terminology)
        log(f"  → {len(figures)} figure(s)")
        all_figures.extend(figures)

    # Collect zero-day records from all metrics (deduplicated by key)
    seen_keys: set[str] = set()
    zero_day_records = []
    for result in all_results:
        for rec in result.stats.get("zero_day_records", []):
            if rec.key not in seen_keys:
                seen_keys.add(rec.key)
                zero_day_records.append(rec)

    if not all_figures:
        log("No figures produced — nothing to export.")
        return

    if output_pdf:
        log(f"Exporting {len(all_figures)} figure(s) to {output_pdf} ...")
        export_pdf(all_figures, output_pdf)
        log(f"  Saved: {output_pdf}")
        xlsx_path = output_pdf.with_suffix(".xlsx")
        write_report_excel(data.issues, data.stages, xlsx_path)
        log(f"  Saved: {xlsx_path}")
        if zero_day_records:
            xlsx_path = output_pdf.parent / (output_pdf.stem + "_zero_day_issues.xlsx")
            write_zero_day_excel(zero_day_records, xlsx_path)
            log(f"  {len(zero_day_records)} Zero-Day Issue(s) exportiert: {xlsx_path.name}")

    if open_browser:
        for fig in all_figures:
            pio.show(fig)

    if not output_pdf and not open_browser:
        log("No output specified — use --pdf or --browser to view results.")


def main() -> None:
    """
    Entry point for the build_reports CLI.

    Parses command-line arguments and delegates to run_reports().
    """
    available_ids = [p.metric_id for p in all_metrics()]

    parser = argparse.ArgumentParser(
        prog="python -m build_reports.cli",
        description="Generate flow metrics reports from transform_data XLSX output.",
    )
    parser.add_argument("issue_times", type=Path,
                        help="Path to IssueTimes.xlsx")
    parser.add_argument("--cfd", type=Path, default=None,
                        help="Path to CFD.xlsx (required for CFD metric)")
    parser.add_argument("--metrics", nargs="+", metavar="ID",
                        choices=available_ids, default=None,
                        help=f"Metrics to compute (default: all). "
                             f"Available: {', '.join(available_ids)}")
    parser.add_argument("--from-date", type=_parse_date, default=None,
                        metavar="YYYY-MM-DD",
                        help="Include only issues closed on or after this date")
    parser.add_argument("--to-date", type=_parse_date, default=None,
                        metavar="YYYY-MM-DD",
                        help="Include only issues closed on or before this date")
    parser.add_argument("--projects", nargs="+", default=None,
                        metavar="KEY",
                        help="Restrict to these project keys")
    parser.add_argument("--issuetypes", nargs="+", default=None,
                        metavar="TYPE",
                        help="Restrict to these issue types")
    parser.add_argument("--terminology", choices=[SAFE, GLOBAL], default=SAFE,
                        help=f"Terminology mode (default: {SAFE})")
    parser.add_argument("--ct-method", choices=[CT_METHOD_A, CT_METHOD_B],
                        default=CT_METHOD_A, dest="ct_method",
                        help="Cycle time method: A=date diff, B=sum of stage minutes "
                             f"(default: {CT_METHOD_A})")
    parser.add_argument("--pi-config", type=Path, default=None,
                        metavar="FILE", dest="pi_config",
                        help="JSON file defining custom PI intervals for Flow Velocity "
                             "(default: quarterly intervals)")
    parser.add_argument("--pdf", type=Path, default=None,
                        metavar="FILE",
                        help="Export all figures to this PDF file")
    parser.add_argument("--browser", action="store_true",
                        help="Open figures in the default browser")

    args = parser.parse_args()

    run_reports(
        issue_times=args.issue_times,
        cfd=args.cfd,
        metrics=args.metrics,
        from_date=args.from_date,
        to_date=args.to_date,
        projects=args.projects,
        issuetypes=args.issuetypes,
        terminology=args.terminology,
        ct_method=args.ct_method,
        pi_config=args.pi_config,
        output_pdf=args.pdf,
        open_browser=args.browser,
    )


if __name__ == "__main__":
    main()
