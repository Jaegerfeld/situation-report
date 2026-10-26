# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       02.05.2026
# Geändert:       26.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Kommandozeileninterface für testdata_generator. Liest eine Workflow-Datei
#   und erzeugt synthetische Jira-Issue-JSON-Dateien mit konfigurierbarer
#   Anzahl an Issues, Durchlaufzeiten, Completion-Rate und Seed. Unterstützt
#   vier Flow-Muster (Triangle, Flat Triangle, Cluster, Batch) sowie lognormale
#   Cycle-Time-Steuerung. Die Ausgabe ist direkt mit transform_data verarbeitbar.
# =============================================================================

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from datetime import date
from pathlib import Path

from .generator import (
    PATTERN_BATCH,
    PATTERN_CLUSTER,
    PATTERN_FLAT_TRIANGLE,
    PATTERN_NONE,
    PATTERN_TRIANGLE,
    GeneratorConfig,
    generate,
)
from .workflow_parser import parse_workflow


def _parse_date(value: str) -> date:
    """
    Parse a date string in YYYY-MM-DD format for argparse.

    Raises:
        argparse.ArgumentTypeError: If the format is invalid.
    """
    try:
        return date.fromisoformat(value)
    except ValueError as err:
        raise argparse.ArgumentTypeError(
            f"Invalid date '{value}' — expected YYYY-MM-DD format."
        ) from err


def _parse_issue_types(values: list[str]) -> dict[str, float]:
    """
    Parse issue type weight specifications from CLI arguments.

    Args:
        values: List of 'TypeName:weight' strings, e.g. ['Feature:0.6', 'Bug:0.3'].

    Returns:
        Dict mapping type name to weight (not normalised; generator handles that).

    Raises:
        argparse.ArgumentTypeError: If any entry is malformed.
    """
    result: dict[str, float] = {}
    for entry in values:
        parts = entry.split(":", 1)
        if len(parts) != 2:
            raise argparse.ArgumentTypeError(
                f"Invalid issue-type entry '{entry}' — expected 'TypeName:weight' (e.g. Feature:0.6)."
            )
        type_name, weight_str = parts
        try:
            weight = float(weight_str)
        except ValueError as err:
            raise argparse.ArgumentTypeError(
                f"Invalid weight '{weight_str}' in '{entry}' — must be a number."
            ) from err
        if weight < 0:
            raise argparse.ArgumentTypeError(
                f"Weight must be non-negative, got {weight} in '{entry}'."
            )
        result[type_name] = weight
    return result


def run_generate(
    workflow: Path,
    output: Path,
    project_key: str = "TEST",
    issue_count: int = 100,
    from_date: date | None = None,
    to_date: date | None = None,
    issue_types: dict[str, float] | None = None,
    completion_rate: float = 0.7,
    todo_rate: float = 0.15,
    backflow_prob: float = 0.1,
    seed: int | None = None,
    mean_cycle_days: float | None = None,
    std_cycle_days: float | None = None,
    pattern: str = PATTERN_NONE,
    pi_duration_weeks: int = 12,
    pattern_strength: float = 0.5,
    realism: float = 0.0,
    transition_profile: Path | None = None,
    log: Callable[[str], None] = print,
) -> None:
    """
    Execute the full generation pipeline: parse workflow → generate issues → write JSON.

    Called by both the CLI and the GUI. The log parameter accepts any callable
    that takes a single string — defaults to print for CLI use.

    Args:
        workflow:          Path to the workflow definition file (.txt).
        output:            Path for the output JSON file.
        project_key:       Jira project key for generated issues.
        issue_count:       Number of issues to generate.
        from_date:         Earliest creation date (default: 2025-01-01).
        to_date:           Latest transition date (default: 2025-12-31).
        issue_types:       Issue type name → relative weight mapping.
        completion_rate:   Fraction of issues that reach the closed stage (0.0–1.0).
        todo_rate:         Fraction of open issues that stay in a To Do stage (0.0–1.0).
        backflow_prob:     Probability of a backward transition at each step (0.0–1.0).
        seed:              Optional RNG seed for reproducible output.
        mean_cycle_days:   Target mean cycle time in days. None = use min/max dwell hours.
        std_cycle_days:    Std deviation of cycle time. None = 30 % of mean.
        pattern:           Flow pattern to simulate (none/triangle/flat_triangle/cluster/batch).
        pi_duration_weeks: PI cycle duration in weeks (cluster/batch patterns only).
        pattern_strength:  Pattern intensity 0.0–1.0 (0=subtle, 0.5=default, 1.0=strong).
        realism:           Untidiness of the stage paths 0.0–1.0 (0 = plain chain,
                           ~0.7 = like a real ART); see paths.py.
        transition_profile: Profile JSON learned from real transitions (learn.py);
                           path and dwell times then come from the data.
        log:               Callable for progress messages.
    """
    effective_from = from_date or date(2025, 1, 1)
    effective_to = to_date or date(2025, 12, 31)

    if effective_from > effective_to:
        log(f"ERROR: from_date ({effective_from}) is after to_date ({effective_to}).")
        return

    log(f"Parsing workflow: {workflow}")
    workflow_spec = parse_workflow(workflow)
    log(f"Stages: {', '.join(workflow_spec.stages)}")
    if workflow_spec.first_stage:
        log(f"First stage: {workflow_spec.first_stage}")
    if workflow_spec.closed_stage:
        log(f"Closed stage: {workflow_spec.closed_stage}")

    config = GeneratorConfig(
        project_key=project_key,
        issue_count=issue_count,
        from_date=effective_from,
        to_date=effective_to,
        issue_types=issue_types or {"Feature": 0.6, "Bug": 0.3, "Enabler": 0.1},
        completion_rate=completion_rate,
        todo_rate=todo_rate,
        backflow_prob=backflow_prob,
        seed=seed,
        mean_cycle_days=mean_cycle_days,
        std_cycle_days=std_cycle_days,
        pattern=pattern,
        pi_duration_weeks=pi_duration_weeks,
        pattern_strength=pattern_strength,
        realism=realism,
        transition_profile=str(transition_profile) if transition_profile else None,
    )

    log(f"Generating {issue_count} issues for project '{project_key}'…")
    if transition_profile:
        log(f"Transition profile: {transition_profile} (path and dwell from real data; "
            f"realism/backflow/completion/to-do knobs do not apply to the path)")
    elif realism > 0:
        log(f"Realism: {realism:.2f} (skips, cancels, parking, self-loops, reopening)")
    if pattern != PATTERN_NONE:
        log(f"Pattern: {pattern}" + (
            f"  (mean={mean_cycle_days}d, std={std_cycle_days}d)" if mean_cycle_days else ""
        ))
    data = generate(workflow_spec, config)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"Done. Output written to: {output}")
    log(f"  Total issues:  {data['total']}")

    done_count = sum(
        1 for issue in data["issues"]
        if issue["changelog"]["total"] > 0
        and issue["changelog"]["histories"][-1]["items"][0]["toString"]
        == (workflow_spec.closed_stage or workflow_spec.stages[-1])
    )
    open_count = data["total"] - done_count
    log(f"  Closed issues: {done_count}")
    log(f"  Open issues:   {open_count}")


def run_learn(source: Path, output: Path | None = None, workflow: Path | None = None,
              log: Callable[[str], None] = print) -> Path | None:
    """
    Learn a transition profile from a real transitions file (XLSX/CSV).

    With ``workflow`` the profile is restricted to that workflow's stages.
    Returns the written profile path, or None on a clean error (logged).
    """
    from .learn import LearnError, learn_profile, save_profile

    stages = parse_workflow(workflow).stages if workflow else None
    try:
        profile = learn_profile(source, stages=stages)
    except LearnError as exc:
        log(f"ERROR: {exc}")
        return None
    target = output or source.with_name(f"{source.stem}_profile.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    save_profile(target, profile)
    log(f"Profile written to: {target}")
    log(f"  Issues:      {profile.issues}")
    log(f"  Transitions: {profile.transitions}")
    log(f"  Stages:      {', '.join(profile.stages)}")
    log("  Contains counts and hours only - no keys, no texts, no dates.")
    return target


def run_continue(
    source: Path,
    workflow: Path,
    to_date: date,
    output: Path | None = None,
    new_issue_count: int | None = None,
    rate_per_day: float | None = None,
    seed: int | None = None,
    realism: float | None = None,
    transition_profile: Path | None = None,
    log: Callable[[str], None] = print,
) -> Path | None:
    """
    Continue an earlier extract to ``to_date`` and write the second extract.

    The knobs come from the file's generator record; ``realism`` overrides
    that one knob when given (a data set made before 0.38.0 carries 0).
    Returns the written path, or None on a clean error (logged).
    """
    from .continuation import ContinuationError, config_from_meta, continue_generation, read_meta

    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log(f"ERROR: cannot read {source}: {exc}")
        return None
    workflow_spec = parse_workflow(workflow)
    config = None
    meta = read_meta(data)
    if meta is not None and (realism is not None or transition_profile is not None):
        config = config_from_meta(meta)
        if realism is not None:
            config.realism = realism
        if transition_profile is not None:
            config.transition_profile = str(transition_profile)
    log(f"Continuing {source.name}: last cut "
        f"{meta['to_date'] if meta else '(from the youngest timestamp)'} -> {to_date}")
    try:
        result = continue_generation(
            data, workflow_spec, to_date, config=config,
            new_issue_count=new_issue_count, rate_per_day=rate_per_day, seed=seed)
    except ContinuationError as exc:
        log(f"ERROR: {exc}")
        return None
    target = output or source.with_name(f"{source.stem}_{to_date.isoformat()}.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    before = len(data.get("issues", []))
    moved = sum(
        1 for old, new in zip(data["issues"], result["issues"][:before])
        if len(new["changelog"]["histories"]) > len(old["changelog"]["histories"]))
    log(f"Done. Output written to: {target}")
    log(f"  Issues before:   {before}")
    log(f"  Moved on:        {moved}")
    log(f"  New issues:      {len(result['issues']) - before}")
    return target


def _run_scenario(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    """--scenario portfolio: resolve the structure, print the estimate, build."""
    import json as _json

    from .scenario import build_portfolio_scenario
    from .structure import estimate, resolve_structure, structure_from_arts_spec
    out_dir = args.output if args.output else Path("demo_portfolio")
    art_profiles = None
    if args.art_profiles is not None:
        art_profiles = _json.loads(
            args.art_profiles.read_text(encoding="utf-8"))
    if args.structure is not None and args.arts is not None:
        parser.error("--structure and --arts exclude each other.")
    try:
        structure = (structure_from_arts_spec(args.arts) if args.arts is not None
                     else resolve_structure(args.structure))
    except (ValueError, OSError) as exc:
        parser.error(f"structure: {exc}")
    from .scenario import MAX_STANDS, MIN_STANDS
    from .story import SUGGESTED_STANDS, TEMPLATE_STANDARD, parse_switches
    template = args.story or TEMPLATE_STANDARD
    try:
        switches = parse_switches(args.event)
    except ValueError as exc:
        parser.error(str(exc))
    stands = SUGGESTED_STANDS[template] if args.stands is None else args.stands
    if not MIN_STANDS <= stands <= MAX_STANDS:
        parser.error(f"--stands must be {MIN_STANDS}..{MAX_STANDS}, got {stands}.")
    est = estimate(structure, stands=stands, scale=args.scale)
    switch_text = ", ".join(f"{k}={'on' if v else 'off'}" for k, v in switches.items())
    print(f"Struktur: {structure.describe()} — {est.jira_exports} Jira-Exporte, "
          f"{est.workbooks} Arbeitsmappen, {est.registers} Register, "
          f"{est.stands} Stände, {est.deltas} Delta-Briefings; Geschichte: {template}"
          + (f", Schalter {switch_text}" if switch_text else ""))
    if est.warn:
        print(f"WARNUNG: grosse Struktur ({est.warn_reason}) — Erzeugung dauert "
              f"entsprechend.", file=sys.stderr)
    build_portfolio_scenario(
        Path(out_dir), seed=args.seed if args.seed is not None else 42,
        scale=args.scale, art_profiles=art_profiles, structure=structure,
        stands=stands, template=template, switches=switches)


def main() -> None:
    """Entry point for CLI mode (called by __main__.py when args are present)."""
    parser = argparse.ArgumentParser(
        prog="python -m testdata_generator",
        description="Generate synthetic Jira issue data in REST API JSON format.",
    )
    parser.add_argument("--workflow", type=Path, default=None,
                        help="Workflow definition file (.txt) — defines stages and boundaries. "
                             "Required unless --scenario is used.")
    parser.add_argument("--scenario", choices=["portfolio"], default=None,
                        help="Generate a complete demo data room instead of a single "
                             "project: 'portfolio' builds every ART of the structure "
                             "(default 2 solutions x 3 ARTs) with "
                             "IssueTimes/CFD/Transitions, solution/portfolio configs "
                             "(stage_map per solution), registers, snapshots, "
                             "structure.json/story.json and a PI config into --output.")
    parser.add_argument("--structure", default=None, metavar="TEMPLATE|FILE",
                        help="With --scenario: the data-room structure — a template "
                             "name (small = 1 solution x 2 ARTs, standard = 2 x 3, "
                             "large = 5 portfolios) or a structure.json (portfolios "
                             "-> solutions -> ARTs, workflow per solution). "
                             "Default: standard.")
    parser.add_argument("--story", default=None,
                        choices=["calm", "standard", "escalation", "recovery"],
                        help="With --scenario: the story template — calm (no turning "
                             "points, suggests 3 stands), standard (the demo story: "
                             "turning points with the last stand), escalation (pressure "
                             "rises stand by stand), recovery (starts bad, heals). "
                             "Default: standard.")
    parser.add_argument("--event", action="append", default=None, metavar="ID=on|off",
                        help="With --scenario: switch one story event on or off, e.g. "
                             "--event E3=off --event E9=on (ids E1-E10, see story.json). "
                             "Repeatable; an event whose prerequisite is off stays off "
                             "with a notice.")
    parser.add_argument("--stands", type=int, default=None, metavar="N",
                        help="With --scenario: number of stands in the series "
                             "(2-12, default 6), two weeks apart, the last one on "
                             "the reference date; every consecutive pair gets a "
                             "rendered delta briefing under deltas/.")
    parser.add_argument("--arts", default=None, metavar="N[,N...]",
                        help="With --scenario: one portfolio from ART counts per "
                             "solution, e.g. '3,4s,1' = three solutions with 3, 4 "
                             "and 1 ARTs; a trailing 's' gives that solution its own "
                             "stage map. Not combinable with --structure.")
    parser.add_argument("--scale", choices=["s", "m", "l"], default="m",
                        help="With --scenario: register volume per solution. "
                             "s = story anchors only, m = realistic demo "
                             "(default), l = stress test (dense heatmap, "
                             "full roadmap matrix). Story anchors are "
                             "identical at every scale.")
    parser.add_argument("--art-profiles", type=Path, default=None,
                        dest="art_profiles", metavar="FILE.json",
                        help="With --scenario: per-ART generator overrides "
                             "as JSON, e.g. {\"Alpha-1\": "
                             "{\"mean_cycle_days\": 30, \"std_cycle_days\": "
                             "12, \"pattern\": \"cluster\", "
                             "\"pattern_strength\": 80}}. Fields: "
                             "issue_count, mean_cycle_days, std_cycle_days, "
                             "completion_rate, todo_rate, backflow_prob, "
                             "pattern (none|triangle|flat_triangle|cluster|"
                             "batch), pattern_strength (0-100), "
                             "pi_duration_weeks. Overrides win in both "
                             "delta stands; everything else keeps its "
                             "story value.")
    parser.add_argument("--output", type=Path, default=None,
                        help="Output JSON file path (default: <project>_generated.json).")
    parser.add_argument("--project", default="TEST", dest="project_key",
                        help="Jira project key for generated issues (default: TEST).")
    parser.add_argument("--issues", type=int, default=100, dest="issue_count",
                        help="Number of issues to generate (default: 100).")
    parser.add_argument("--from-date", type=_parse_date, default=None,
                        help="Earliest creation date YYYY-MM-DD (default: 2025-01-01).")
    parser.add_argument("--to-date", type=_parse_date, default=None,
                        help="Latest transition date YYYY-MM-DD (default: 2025-12-31).")
    parser.add_argument("--issue-types", nargs="+", default=None,
                        help="Issue types with weights, e.g. Feature:0.6 Bug:0.3.")
    parser.add_argument("--completion-rate", type=float, default=0.7,
                        help="Fraction of issues reaching the closed stage (default: 0.7).")
    parser.add_argument("--todo-rate", type=float, default=0.15,
                        help="Fraction of open issues that stay in a To Do stage (default: 0.15).")
    parser.add_argument("--backflow-prob", type=float, default=0.1,
                        help="Probability of a backward transition at each step (default: 0.1).")
    parser.add_argument("--seed", type=int, default=None,
                        help="RNG seed for reproducible output (optional).")
    parser.add_argument("--mean-cycle-days", type=float, default=None,
                        help="Target mean cycle time in days (lognormal). "
                             "If omitted, min/max dwell hours are used instead.")
    parser.add_argument("--std-cycle-days", type=float, default=None,
                        help="Standard deviation of cycle time in days (default: 30 %% of mean).")
    parser.add_argument("--pattern", default=PATTERN_NONE,
                        choices=[PATTERN_NONE, PATTERN_TRIANGLE, PATTERN_FLAT_TRIANGLE,
                                 PATTERN_CLUSTER, PATTERN_BATCH],
                        help="Flow pattern to simulate (default: none). "
                             "triangle/flat_triangle require --mean-cycle-days.")
    parser.add_argument("--pi-duration-weeks", type=int, default=12,
                        help="PI cycle duration in weeks for cluster/batch patterns (default: 12).")
    parser.add_argument("--pattern-strength", type=int, default=50,
                        choices=range(0, 101), metavar="0-100",
                        help="Pattern intensity 0–100 (0=subtle, 50=default, 100=strong).")
    parser.add_argument("--continue", type=Path, default=None, dest="continue_from",
                        metavar="OLD.json",
                        help="Continue an earlier extract (0.39.0) - or, with "
                             "--scenario portfolio, a whole demo data room FOLDER in "
                             "place (0.40.0: raw extracts, IssueTimes/CFD/Transitions, "
                             "configs, PI config; snapshot_now becomes snapshot_prev). "
                             "Single file: keep its past "
                             "byte for byte, let open issues move on after its cut "
                             "and add new issues up to --to-date, as a second manual "
                             "extract would show. Needs --workflow; knobs come from "
                             "the file's generator record. Output defaults to "
                             "OLD_<to-date>.json; --issues sets the number of NEW "
                             "issues (default: the earlier rate), --rate-per-day "
                             "an alternative rate.")
    parser.add_argument("--rate-per-day", type=float, default=None, dest="rate_per_day",
                        help="With --continue: new issues per day (default: the "
                             "rate of the earlier window).")
    parser.add_argument("--learn-from", type=Path, default=None, dest="learn_from",
                        metavar="TRANSITIONS.xlsx",
                        help="Learn a transition profile from a real transitions file "
                             "(XLSX or CSV from transform_data) and stop (0.41.0). "
                             "Writes <name>_profile.json (or --output); with "
                             "--workflow restricted to that workflow's stages. The "
                             "profile holds counts and hours only.")
    parser.add_argument("--transition-profile", type=Path, default=None,
                        dest="transition_profile", metavar="PROFILE.json",
                        help="Generate (or continue) with a learned profile: stage paths "
                             "and dwell times follow the real data; realism, backflow, "
                             "completion and to-do knobs do not apply to the path.")
    parser.add_argument("--realism", type=int, default=0,
                        help="Untidiness of the stage paths 0-100: 0 = plain chain "
                             "(default, as before 0.38.0), about 70 = like a real ART "
                             "(skips, cancels, parking, self-loops, reopening).")

    args = parser.parse_args()

    if args.scenario == "portfolio" and args.continue_from is not None:
        # 0.40.0: continue the whole data room in place (snapshots rotate)
        from .scenario_continue import ScenarioContinuationError, continue_portfolio_scenario
        if args.to_date is None:
            parser.error("--scenario portfolio --continue needs --to-date (the new reference).")
        try:
            continue_portfolio_scenario(Path(args.continue_from), args.to_date)
        except ScenarioContinuationError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            sys.exit(1)
        return

    if args.scenario == "portfolio":
        _run_scenario(args, parser)
        return

    if args.learn_from is not None:
        written = run_learn(args.learn_from, output=args.output, workflow=args.workflow)
        sys.exit(0 if written else 1)

    if args.workflow is None:
        parser.error("--workflow is required (unless --scenario is used).")

    if args.continue_from is not None:
        if args.to_date is None:
            parser.error("--continue needs --to-date (the new cut).")
        # --issues keeps its CLI default of 100; only an explicit value counts here
        explicit_issues = args.issue_count if "--issues" in sys.argv else None
        explicit_realism = (args.realism / 100.0) if "--realism" in sys.argv else None
        written = run_continue(
            args.continue_from, args.workflow, args.to_date, output=args.output,
            new_issue_count=explicit_issues, rate_per_day=args.rate_per_day,
            seed=args.seed, realism=explicit_realism,
            transition_profile=args.transition_profile)
        sys.exit(0 if written else 1)

    issue_types: dict[str, float] | None = None
    if args.issue_types:
        try:
            issue_types = _parse_issue_types(args.issue_types)
        except argparse.ArgumentTypeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            sys.exit(1)

    if args.pattern != PATTERN_NONE and args.mean_cycle_days is None:
        print(
            f"ERROR: --pattern {args.pattern} requires --mean-cycle-days to be set.",
            file=sys.stderr,
        )
        sys.exit(1)

    output = args.output or Path(f"{args.project_key}_generated.json")

    run_generate(
        workflow=args.workflow,
        output=output,
        project_key=args.project_key,
        issue_count=args.issue_count,
        from_date=args.from_date,
        to_date=args.to_date,
        issue_types=issue_types,
        completion_rate=args.completion_rate,
        todo_rate=args.todo_rate,
        backflow_prob=args.backflow_prob,
        seed=args.seed,
        mean_cycle_days=args.mean_cycle_days,
        std_cycle_days=args.std_cycle_days,
        pattern=args.pattern,
        pi_duration_weeks=args.pi_duration_weeks,
        pattern_strength=args.pattern_strength / 100.0,
        transition_profile=args.transition_profile,
        realism=max(0, min(100, args.realism)) / 100.0,
    )


if __name__ == "__main__":
    main()
