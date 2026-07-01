# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       01.07.2026
# Geändert:       01.07.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Kommandozeileninterface für den Monte-Carlo-Forecast. Lädt eine
#   IssueTimes-Datei (optional CFD), bildet daraus die Tagesdurchsatz-Verteilung
#   über ein History-Fenster und erzeugt einen HTML-Report mit Kapazitäts-
#   (how_many) und optionalem Termin-Forecast (when_done, inkl. Scope-Wachstum).
# =============================================================================

from __future__ import annotations

import argparse
import random
import sys
import webbrowser
from collections.abc import Callable
from datetime import date, datetime, timedelta
from html import escape
from pathlib import Path

from build_reports.loader import load_report_data

from .charts import (
    combined_html,
    how_many_figure,
    scope_confidence_figure,
    when_done_figure,
)
from .forecast import (
    HowManyForecast,
    WhenDoneForecast,
    how_many,
    probability_at_least,
    when_done,
)
from .throughput import default_history_window, to_sample


def _stats_html(
    start: date,
    end: date,
    days_observed: int,
    mean_per_day: float,
    fc_hm: HowManyForecast,
    fc_wd: WhenDoneForecast | None,
    prob: float | None = None,
    target_date: date | None = None,
    backlog: int | None = None,
) -> str:
    """Baue den Kennzahlen-Block (HTML) über den Diagrammen."""
    rows = [
        f"<tr><th>History window</th><td>{start.isoformat()} … {end.isoformat()} "
        f"(exclusive), {days_observed} days</td></tr>",
        f"<tr><th>Mean throughput</th><td>{mean_per_day:.2f} items/day</td></tr>",
        f"<tr><th>Horizon</th><td>{fc_hm.horizon_days} days · {fc_hm.runs} runs</td></tr>",
    ]
    if prob is not None and backlog is not None:
        when = f" by {target_date.isoformat()}" if target_date is not None else ""
        rows.insert(0, f"<tr><th>Scope confidence</th>"
                       f"<td>P(≥ {backlog} items{when}) = {prob:.0%}</td></tr>")
    hm = "  ".join(f"{c}%≥{n}" for c, n in sorted(fc_hm.percentiles.items(), reverse=True))
    rows.append(f"<tr><th>Items by date (conf.)</th><td>{escape(hm)}</td></tr>")
    if fc_wd is not None:
        parts = []
        for c in sorted(fc_wd.percentiles, reverse=True):
            days = fc_wd.percentiles[c]
            if days is None:
                parts.append(f"{c}%: ≥ cap")
                continue
            label = f"{c}%≤{days}d"
            if c in fc_wd.dates:
                label += f" ({fc_wd.dates[c].isoformat()})"
            parts.append(label)
        wd = "  ".join(parts) or "no run completed"
        rows.append(
            f"<tr><th>Finish {fc_wd.backlog} items (conf.)</th><td>{escape(wd)}</td></tr>"
        )
    return "<table class='stats'>" + "".join(rows) + "</table>"


def run_simulation(
    issue_times: Path,
    *,
    cfd: Path | None = None,
    history_days: int = 180,
    history_end: date | None = None,
    horizon_days: int = 84,
    backlog: int | None = None,
    runs: int = 25000,
    split_rate: float = 0.0,
    seed: int | None = None,
    output_html: Path | None = None,
    open_browser: bool = False,
    log: Callable[[str], None] = print,
) -> str:
    """
    Führe den Forecast aus: Daten laden → Verteilung → Simulation → HTML.

    Args:
        issue_times:  Pfad zur IssueTimes.xlsx (Pflicht).
        cfd:          Optionaler Pfad zur CFD.xlsx.
        history_days: Länge des History-Fensters in Tagen.
        history_end:  Exklusives Enddatum des Fensters (None = heute).
        horizon_days: Vorhersagehorizont für den Kapazitäts-Forecast.
        backlog:      Wenn gesetzt, zusätzlich Termin-Forecast für diese Item-Zahl.
        runs:         Anzahl Monte-Carlo-Läufe.
        split_rate:   Erwartete neue Items je abgeschlossenem Item (Scope-Wachstum).
        seed:         Seed für Reproduzierbarkeit (None = nicht-deterministisch).
        output_html:  Wenn gesetzt, wird der HTML-Report hierhin geschrieben.
        open_browser: Wenn True, geschriebenen Report im Browser öffnen.
        log:          Fortschritts-Callback.

    Returns:
        Der HTML-Report als String (leer, wenn keine Durchsatzdaten vorliegen).
    """
    data = load_report_data(issue_times, cfd_path=cfd)
    start, end = default_history_window(data, days=history_days, reference=history_end)
    sample = to_sample(data, start, end)
    log(f"History {start} … {end} (excl.) — {sample.days_observed} days, "
        f"mean {sample.mean_per_day:.2f} items/day")

    if sample.is_empty:
        log("WARNING: no throughput in the history window — nothing to simulate.")
        return ""

    rng = random.Random(seed)
    fc_hm = how_many(sample, horizon_days, runs, rng=rng)

    fc_wd: WhenDoneForecast | None = None
    prob: float | None = None
    target_date: date | None = None
    if backlog is not None:
        # "Schaffen wir den Scope bis zum Horizont?" — derselbe Lauf, kein Re-Sim.
        prob = probability_at_least(fc_hm, backlog)
        target_date = date.today() + timedelta(days=horizon_days)
        log(f"Scope confidence: P(>= {backlog} items by {target_date}) = {prob:.0%}")
        figures = [
            scope_confidence_figure(prob, backlog, target_date),
            how_many_figure(fc_hm, target=backlog),
        ]
        fc_wd = when_done(sample, backlog, runs, rng=rng, split_rate=split_rate,
                          start_date=date.today())
        figures.append(when_done_figure(fc_wd))
        if fc_wd.not_completed:
            log(f"NOTE: {fc_wd.not_completed}/{runs} runs did not finish within the cap.")
    else:
        figures = [how_many_figure(fc_hm)]

    intro = _stats_html(start, end, sample.days_observed, sample.mean_per_day,
                        fc_hm, fc_wd, prob, target_date, backlog)
    html = combined_html(figures, intro)

    if output_html:
        output_html.parent.mkdir(parents=True, exist_ok=True)
        output_html.write_text(html, encoding="utf-8")
        log(f"Report written to: {output_html}")
        if open_browser:
            webbrowser.open(output_html.resolve().as_uri())

    return html


def _parse_date(value: str) -> date:
    """argparse-Typ: ISO-Datum (YYYY-MM-DD)."""
    return datetime.strptime(value, "%Y-%m-%d").date()


def main() -> None:
    """Einstiegspunkt für das simulate-CLI."""
    parser = argparse.ArgumentParser(
        prog="python -m simulate",
        description="Throughput-based Monte-Carlo forecast (how many / when done).",
    )
    parser.add_argument("issue_times", type=Path,
                        help="Path to the IssueTimes.xlsx file.")
    parser.add_argument("--cfd", type=Path, default=None, metavar="FILE",
                        help="Optional CFD.xlsx path.")
    parser.add_argument("--history-days", type=int, default=180, dest="history_days",
                        metavar="N", help="History window length in days (default: 180).")
    parser.add_argument("--history-end", type=_parse_date, default=None, dest="history_end",
                        metavar="YYYY-MM-DD",
                        help="Exclusive end of the history window (default: today).")
    parser.add_argument("--horizon", type=int, default=84, dest="horizon_days",
                        metavar="DAYS", help="Forecast horizon in days (default: 84).")
    parser.add_argument("--backlog", type=int, default=None, metavar="N",
                        help="If set, also forecast when N items will be done.")
    parser.add_argument("--runs", type=int, default=25000, metavar="N",
                        help="Monte-Carlo runs (default: 25000).")
    parser.add_argument("--split-rate", type=float, default=0.0, dest="split_rate",
                        metavar="R",
                        help="Expected new items per completed item (scope growth).")
    parser.add_argument("--seed", type=int, default=None,
                        help="Seed for reproducible runs.")
    parser.add_argument("--output", type=Path, default=None, metavar="FILE",
                        help="Write the HTML report to this file.")
    parser.add_argument("--browser", action="store_true",
                        help="Open the written report in the default browser.")

    args = parser.parse_args()

    html = run_simulation(
        issue_times=args.issue_times,
        cfd=args.cfd,
        history_days=args.history_days,
        history_end=args.history_end,
        horizon_days=args.horizon_days,
        backlog=args.backlog,
        runs=args.runs,
        split_rate=args.split_rate,
        seed=args.seed,
        output_html=args.output,
        open_browser=args.browser,
    )
    if not html:
        print("ERROR: No report produced (no throughput data).", file=sys.stderr)
        sys.exit(1)
    if not args.output:
        print("Report rendered (no --output given, so nothing was written).")


if __name__ == "__main__":
    main()
