# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       09.04.2026
# Geändert:       14.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Einstiegspunkt für die Kommandozeilennutzung von transform_data.
#   Orchestriert die gesamte Transformationspipeline: Einlesen der Workflow-
#   Definition, Verarbeitung des Jira-JSON-Exports und Ausgabe der drei
#   XLSX-Dateien (Transitions, IssueTimes, CFD). Gibt Warnungen aus, wenn
#   Jira-Status nicht in der Workflow-Datei gemappt sind oder Marker-Stages
#   fehlen.
# =============================================================================

"""
transform_data CLI

Usage:
    python -m transform_data.transform <json_file> <workflow_file> [options]
    python -m transform_data                                          (GUI)

Example:
    python -m transform_data.transform transform_data/ART_A.json transform_data/workflow_ART_A.txt
    python -m transform_data.transform transform_data/ART_A.json transform_data/workflow_ART_A.txt --output-dir out/ --prefix ART_A
"""

import argparse
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from .workflow import parse_workflow
from .processor import process_issues
from .writers import write_transitions, write_issue_times, write_cfd


def run_transform(
    json_file: Path,
    workflow_file: Path,
    output_dir: Path | None = None,
    prefix: str | None = None,
    log: Callable[[str], None] = print,
) -> None:
    """
    Execute the full transformation pipeline.

    Called by both the CLI (main) and the GUI. The log parameter accepts
    any callable that takes a single string — defaults to print for CLI use.
    """
    workflow = parse_workflow(workflow_file)

    if workflow.first_stage is None:
        log("WARNUNG: Kein <First>-Marker in der Workflow-Datei — First Date wird nicht berechnet.")
    if workflow.closed_stage is None:
        log("WARNUNG: Kein <Closed>-Marker in der Workflow-Datei — Closed Date wird nicht berechnet.")

    reference_dt = datetime.now(tz=timezone.utc)
    records, unmapped = process_issues(json_file, workflow, reference_dt)

    if unmapped:
        log(f"WARNUNG: {len(unmapped)} Status in den Daten nicht in der Workflow-Datei gemappt:")
        for s in sorted(unmapped):
            log(f"  - {s}")
        log("  > Zeit dieser Status wird der letzten bekannten Stage zugerechnet.")

    resolved_output_dir = output_dir or json_file.parent
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    resolved_prefix = prefix or json_file.stem

    transitions_path = resolved_output_dir / f"{resolved_prefix}_Transitions.xlsx"
    issue_times_path = resolved_output_dir / f"{resolved_prefix}_IssueTimes.xlsx"
    cfd_path = resolved_output_dir / f"{resolved_prefix}_CFD.xlsx"

    write_transitions(records, transitions_path)
    write_issue_times(records, workflow, issue_times_path)
    write_cfd(records, workflow, cfd_path, reference_dt)

    log(f"Processed {len(records)} issues")
    log(f"  {transitions_path}")
    log(f"  {issue_times_path}")
    log(f"  {cfd_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Transform Jira JSON export into stage-time metrics XLSXs."
    )
    parser.add_argument("json_file", type=Path, help="Jira JSON export file")
    parser.add_argument("workflow_file", type=Path, help="Workflow definition file")
    parser.add_argument(
        "--output-dir", type=Path, default=None,
        help="Output directory (default: same directory as json_file)"
    )
    parser.add_argument(
        "--prefix", type=str, default=None,
        help="Output file prefix (default: stem of json_file)"
    )
    args = parser.parse_args()
    run_transform(args.json_file, args.workflow_file, args.output_dir, args.prefix)


if __name__ == "__main__":
    main()
