"""
transform_data CLI

Usage:
    python -m transform_data.transform <json_file> <workflow_file> [options]

Example:
    python -m transform_data.transform transform_data/ART_A.json transform_data/workflow_ART_A.txt
    python -m transform_data.transform transform_data/ART_A.json transform_data/workflow_ART_A.txt --output-dir out/ --prefix ART_A
"""

import argparse
from datetime import datetime, timezone
from pathlib import Path

from .workflow import parse_workflow
from .processor import process_issues
from .writers import write_transitions, write_issue_times, write_cfd


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Transform Jira JSON export into stage-time metrics CSVs."
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

    workflow = parse_workflow(args.workflow_file)
    reference_dt = datetime.now(tz=timezone.utc)
    records = process_issues(args.json_file, workflow, reference_dt)

    output_dir = args.output_dir or args.json_file.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = args.prefix or args.json_file.stem

    transitions_path = output_dir / f"{prefix}_Transitions.csv"
    issue_times_path = output_dir / f"{prefix}_IssueTimes.csv"
    cfd_path = output_dir / f"{prefix}_CFD.csv"

    write_transitions(records, transitions_path)
    write_issue_times(records, workflow, issue_times_path)
    write_cfd(records, workflow, cfd_path, reference_dt)

    print(f"Processed {len(records)} issues")
    print(f"  {transitions_path}")
    print(f"  {issue_times_path}")
    print(f"  {cfd_path}")


if __name__ == "__main__":
    main()
