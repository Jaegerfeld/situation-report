import csv
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .processor import IssueRecord, fmt_dt
from .workflow import Workflow


def write_transitions(records: list[IssueRecord], output_path: Path) -> None:
    """
    Write Transitions CSV (semicolon-separated).
    One row per transition per issue, sorted by timestamp within each issue.

    Columns: Key;Transition;Timestamp
    """
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["Key", "Transition", "Timestamp"])
        for record in records:
            for t in record.transitions:
                writer.writerow([t.key, t.label, t.timestamp.strftime("%d.%m.%Y %H:%M:%S")])


def write_issue_times(records: list[IssueRecord], workflow: Workflow, output_path: Path) -> None:
    """
    Write IssueTimes CSV (comma-separated).
    One row per issue with time spent (in minutes) in each workflow stage.

    Columns: Project, Group, Key, Issuetype, Status, Created Date, Component,
             Category, First Date, Implementation Date, Closed Date,
             <stage columns...>, Resolution
    """
    stage_cols = workflow.stages
    header = (
        ["Project", "Group", "Key", "Issuetype", "Status", "Created Date",
         "Component", "Category", "First Date", "Implementation Date", "Closed Date"]
        + stage_cols
        + ["Resolution"]
    )
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for r in records:
            row = [
                r.project,
                "",                          # Group (not available in raw Jira data)
                r.key,
                r.issuetype,
                r.status,
                fmt_dt(r.created),
                r.component,
                "",                          # Category (not available in raw Jira data)
                fmt_dt(r.first_date),
                fmt_dt(r.inprogress_date),
                fmt_dt(r.closed_date),
            ] + [r.stage_minutes.get(s, 0) for s in stage_cols] + [r.resolution]
            writer.writerow(row)


def write_cfd(
    records: list[IssueRecord],
    workflow: Workflow,
    output_path: Path,
    reference_dt: datetime,
) -> None:
    """
    Write Cumulative Flow Diagram CSV (comma-separated).
    One row per calendar day from the earliest issue creation to reference_dt.
    Each stage column contains the count of issues in that stage on that day.

    An issue is counted in a stage on day D if:
    - It was created on or before D, AND
    - The most recent explicit transition on or before D maps to that stage.
      If no transitions exist yet, the initial stage (status at creation) is used.

    Columns: Day, <stage columns...>
    """
    if not records:
        return

    stage_cols = workflow.stages
    min_date = min(r.created.date() for r in records)
    max_date = reference_dt.date()

    def stage_at_day(record: IssueRecord, day: date) -> str | None:
        if record.created.date() > day:
            return None
        current = record.initial_stage
        for t in record.transitions[1:]:   # skip "Created" entry
            if t.timestamp.date() <= day:
                current = workflow.status_to_stage.get(t.label)
            else:
                break   # transitions are sorted; everything after is in the future
        return current

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Day"] + stage_cols)

        current_date = min_date
        while current_date <= max_date:
            counts: dict[str, int] = {s: 0 for s in stage_cols}
            for record in records:
                stage = stage_at_day(record, current_date)
                if stage and stage in counts:
                    counts[stage] += 1
            writer.writerow(
                [current_date.strftime("%d.%m.%Y")] + [counts[s] for s in stage_cols]
            )
            current_date += timedelta(days=1)
