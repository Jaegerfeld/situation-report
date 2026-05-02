# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       02.05.2026
# Geändert:       02.05.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Kommandozeileninterface für testdata_generator. Liest eine Workflow-Datei
#   und erzeugt synthetische Jira-Issue-JSON-Dateien mit konfigurierbarer
#   Anzahl an Issues, Durchlaufzeiten, Completion-Rate und Seed. Die Ausgabe
#   ist direkt mit transform_data verarbeitbar.
# =============================================================================

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from datetime import date
from pathlib import Path

from .generator import GeneratorConfig, generate
from .workflow_parser import parse_workflow


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
        except ValueError:
            raise argparse.ArgumentTypeError(
                f"Invalid weight '{weight_str}' in '{entry}' — must be a number."
            )
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
    log: Callable[[str], None] = print,
) -> None:
    """
    Execute the full generation pipeline: parse workflow → generate issues → write JSON.

    Called by both the CLI and the GUI. The log parameter accepts any callable
    that takes a single string — defaults to print for CLI use.

    Args:
        workflow:         Path to the workflow definition file (.txt).
        output:           Path for the output JSON file.
        project_key:      Jira project key for generated issues.
        issue_count:      Number of issues to generate.
        from_date:        Earliest creation date (default: 2025-01-01).
        to_date:          Latest transition date (default: 2025-12-31).
        issue_types:      Issue type name → relative weight mapping.
        completion_rate:  Fraction of issues that reach the closed stage (0.0–1.0).
        todo_rate:        Fraction of open issues that stay in a To Do stage (0.0–1.0).
        backflow_prob:    Probability of a backward transition at each step (0.0–1.0).
        seed:             Optional RNG seed for reproducible output.
        log:              Callable for progress messages.
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
    )

    log(f"Generating {issue_count} issues for project '{project_key}'…")
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


def main() -> None:
    """Entry point for CLI mode (called by __main__.py when args are present)."""
    parser = argparse.ArgumentParser(
        prog="python -m testdata_generator",
        description="Generate synthetic Jira issue data in REST API JSON format.",
    )
    parser.add_argument("--workflow", required=True, type=Path,
                        help="Workflow definition file (.txt) — defines stages and boundaries.")
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

    args = parser.parse_args()

    issue_types: dict[str, float] | None = None
    if args.issue_types:
        try:
            issue_types = _parse_issue_types(args.issue_types)
        except argparse.ArgumentTypeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
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
    )
