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
from typing import Any

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


def narration_html_section(narration: Any,
                           title: str = "Narration (Entwurf)") -> str:
    """
    The labeled draft block for a report page: mandatory AI banner
    (Art. 50 labeling) plus the draft text. Shared by CLI and GUI — and
    by every draft kind (D2 narration, D1 executive summary) — so the
    labeling can never diverge between paths.
    """
    import html as _html

    return (f"<h2>{_html.escape(title)}</h2>"
            "<p style='background:#fff3cd;border:1px solid #d0a900;"
            "padding:6px 10px;font-weight:600'>🤖 "
            f"{_html.escape(narration.banner)}</p>"
            f"<p>{_html.escape(narration.text)}</p>")


def run_delta_briefing(
    prev_path: Path,
    now_path: Path,
    output: Path | None = None,
    open_browser: bool = False,
    narrate_with: str | None = None,
    llm_model: str | None = None,
    llm_lang: str = "de",
    log: Callable[[str], None] = print,
) -> None:
    """
    Compare two snapshot files and emit the delta briefing (D2).

    With ``narrate_with`` set, an AI-drafted narration section is added
    (D2 part 2): the provider only ever sees the deterministic Markdown,
    the numbers guard discards inventions, the mandatory AI banner marks
    the text as an unreviewed draft, and an operator-evidence record is
    appended to llm_audit.jsonl next to the output. Without it, behaviour
    is exactly the deterministic briefing (clean degradation).

    Args:
        prev_path:    Earlier snapshot JSON.
        now_path:     Later snapshot JSON.
        output:       Destination file — ``*.md`` writes Markdown, any other
                      suffix writes the HTML page; None prints Markdown.
        open_browser: Open a written HTML file in the default browser.
        narrate_with: LLM provider id ("ollama", "claude", "mock") or None.
        llm_model:    Model override (None = provider default).
        llm_lang:     Narration language (default: de).
        log:          Progress callback.
    """
    from .delta import compute_delta, delta_to_markdown, render_delta_html
    from .snapshot import load_snapshot

    delta = compute_delta(load_snapshot(prev_path), load_snapshot(now_path))
    delta_md = delta_to_markdown(delta)

    narration = None
    if narrate_with:
        from llm.audit import AUDIT_FILENAME
        from llm.narrate import narrate

        audit_path = ((output.parent if output else Path.cwd())
                      / AUDIT_FILENAME)
        log(f"Narration draft via '{narrate_with}' ...")
        narration = narrate(delta_md, provider_id=narrate_with,
                            lang=llm_lang,
                            config={"model": llm_model} if llm_model else None,
                            audit_path=audit_path)
        log(f"  audit: {audit_path}")

    def _md_with_narration() -> str:
        if narration is None:
            return delta_md
        return (delta_md + "\n\n## Narration (Entwurf)\n"
                f"> {narration.banner}\n\n{narration.text}\n")

    if output is None:
        text = _md_with_narration()
        try:
            print(text)
        except UnicodeEncodeError:
            # Windows-Konsole mit Legacy-Codepage (cp1252): UTF-8 erzwingen.
            sys.stdout.buffer.write(text.encode("utf-8") + b"\n")
            sys.stdout.buffer.flush()
        return
    if output.suffix.lower() == ".md":
        output.write_text(_md_with_narration(), encoding="utf-8")
    else:
        html_doc = render_delta_html(delta)
        if narration is not None:
            html_doc = html_doc.replace(
                "</body></html>",
                narration_html_section(narration) + "</body></html>", 1)
        output.write_text(html_doc, encoding="utf-8")
        if open_browser:
            webbrowser.open(output.resolve().as_uri())
    if narration is not None and output is not None:
        draft = output.with_suffix(output.suffix + ".narration.md")
        draft.write_text(
            f"> {narration.banner}\n\n{narration.text}\n", encoding="utf-8")
        log(f"Narration draft (for human editing): {draft}")
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
    parser.add_argument("--narrate", nargs="?", const="ollama", default=None,
                        metavar="PROVIDER",
                        help="Add an AI-drafted section: with --delta the "
                             "narration (D2 part 2), on a report run with "
                             "an HTML --output the executive summary (D1) "
                             "below the Management-Summary table (plus a "
                             "separate <output>.exec_summary.md draft). "
                             "Optional provider id (default: ollama; also: "
                             "claude, mock). Drafts are always labeled as "
                             "unreviewed; operator evidence goes to "
                             "llm_audit.jsonl next to the output.")
    parser.add_argument("--llm-model", default=None, dest="llm_model",
                        metavar="MODEL",
                        help="Model override for --narrate (default: the "
                             "provider's default, e.g. mistral-nemo / "
                             "claude-sonnet-5).")
    parser.add_argument("--llm-lang", default="de", dest="llm_lang",
                        choices=["de", "en"],
                        help="Narration language (default: de).")

    args = parser.parse_args()

    if args.delta:
        run_delta_briefing(args.delta[0], args.delta[1],
                           output=args.output, open_browser=args.browser,
                           narrate_with=args.narrate,
                           llm_model=args.llm_model, llm_lang=args.llm_lang)
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

    narrate_report = bool(
        args.narrate and args.output
        and args.output.suffix.lower() != ".pdf")
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
        open_browser=args.browser and not narrate_report,
    )
    if not html and not args.pdf:
        print("ERROR: No report produced (no figures).", file=sys.stderr)
        sys.exit(1)
    if args.narrate and not narrate_report:
        print("Hint: --narrate on a report run needs an HTML --output; "
              "no executive summary was drafted.")
    if html and narrate_report:
        from llm.audit import AUDIT_FILENAME

        from .exec_summary import attach_exec_summary

        audit_path = args.output.parent / AUDIT_FILENAME
        html, narration = attach_exec_summary(
            html, load_solution_config(args.config), args.narrate,
            lang=args.llm_lang, llm_model=args.llm_model,
            audit_path=audit_path, as_of=args.as_of,
            target_ct=args.target_ct)
        args.output.write_text(html, encoding="utf-8")
        draft = args.output.with_suffix(
            args.output.suffix + ".exec_summary.md")
        draft.write_text(f"> {narration.banner}\n\n{narration.text}\n",
                         encoding="utf-8")
        print(f"Executive-summary draft (for human editing): {draft}")
        print(f"  audit: {audit_path}")
        if args.browser:
            webbrowser.open(args.output.resolve().as_uri())
    if not args.output and not args.pdf:
        print("Report rendered (no --output/--pdf given, so nothing was written).")


if __name__ == "__main__":
    main()
