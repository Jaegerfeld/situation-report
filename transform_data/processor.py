# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       09.04.2026
# Geändert:       22.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Liest einen Jira-JSON-Export und berechnet für jedes Issue die Verweildauer
#   (in Minuten) in jeder Workflow-Stage. Nicht gemappte Status werden erkannt
#   und gemeldet; ihre Zeit wird der letzten bekannten Stage zugerechnet
#   (Carry-forward). Liefert außerdem die Meilenstein-Zeitstempel First Date,
#   Implementation Date und Closed Date sowie die vollständige Transitions-
#   Historie je Issue. Wird eine Milestone-Stage übersprungen, gilt der erste
#   Eintritt in eine spätere Stage (aber vor Closed) als Fallback-Datum.
# =============================================================================

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path

from .workflow import Workflow

DT_OUT = "%d.%m.%Y %H:%M:%S"


def _parse_dt(s: str) -> datetime:
    """Parse Jira ISO datetime: 2025-11-30T16:49:19.000+0100"""
    m = re.match(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\.\d+([+-]\d{2}):?(\d{2})", s)
    if not m:
        raise ValueError(f"Cannot parse datetime: {s!r}")
    base, tz_h, tz_m = m.groups()
    sign = 1 if tz_h[0] == "+" else -1
    offset = timedelta(hours=int(tz_h[1:]), minutes=int(tz_m)) * sign
    dt = datetime.strptime(base, "%Y-%m-%dT%H:%M:%S")
    return dt.replace(tzinfo=timezone(offset))


def fmt_dt(dt: datetime | None) -> str:
    return dt.strftime(DT_OUT) if dt else ""


@dataclass
class Transition:
    key: str
    label: str          # "Created" or canonical stage name (raw status if unmapped)
    timestamp: datetime


@dataclass
class IssueRecord:
    project: str
    key: str
    issuetype: str
    status: str          # current Jira status name
    created: datetime
    component: str
    first_date: datetime | None
    inprogress_date: datetime | None
    closed_date: datetime | None
    stage_minutes: dict[str, int]  # canonical stage -> minutes
    resolution: str
    initial_stage: str | None      # stage before any transition (for CFD)
    transitions: list[Transition]  # sorted by timestamp; first entry is always "Created"


def process_issues(
    json_path: Path,
    workflow: Workflow,
    reference_dt: datetime | None = None,
) -> tuple[list[IssueRecord], set[str]]:
    """
    Parse Jira JSON export and compute per-issue stage times.

    Returns a tuple of:
    - list of IssueRecord objects
    - set of Jira status names that appear in the data but are not mapped
      in the workflow definition

    Stage time rules:
    - Time from issue creation to first transition is attributed to the initial stage.
    - When a transition targets an unmapped status, time continues to accumulate
      in the last known stage (carry-forward).
    - The current (last known) stage accumulates time up to reference_dt.
    - Issues with no transitions have all-zero stage times.
    """
    if reference_dt is None:
        reference_dt = datetime.now(tz=timezone.utc)

    data = json.loads(json_path.read_text(encoding="utf-8"))
    records: list[IssueRecord] = []
    unmapped_statuses: set[str] = set()

    for issue in data["issues"]:
        key = issue["key"]
        fields = issue["fields"]
        project = fields["project"]["key"]
        issuetype = fields["issuetype"]["name"]
        current_status = fields["status"]["name"]
        created = _parse_dt(fields["created"])

        components = [c["name"] for c in fields.get("components", [])]
        component = ",".join(components)

        res = fields.get("resolution") or ""
        resolution = res.get("name", "") if isinstance(res, dict) else str(res)

        # Collect all status transitions from changelog
        raw: list[tuple[str, str, datetime]] = []  # (fromString, toString, timestamp)
        for history in issue.get("changelog", {}).get("histories", []):
            ts = _parse_dt(history["created"])
            for item in history["items"]:
                if item["field"] == "status":
                    raw.append((item["fromString"], item["toString"], ts))
        raw.sort(key=lambda x: x[2])

        # Collect unmapped statuses for this issue
        initial_status = raw[0][0] if raw else current_status
        if initial_status not in workflow.status_to_stage:
            unmapped_statuses.add(initial_status)
        for _, to_s, _ in raw:
            if to_s not in workflow.status_to_stage:
                unmapped_statuses.add(to_s)

        # Initial stage for CFD: the status the issue had before its first transition.
        # If unmapped, fall back to the first stage in the workflow.
        initial_stage = workflow.status_to_stage.get(initial_status) or (
            workflow.stages[0] if workflow.stages else None
        )

        # Build sorted transition list (for Transitions sheet and CFD)
        transitions: list[Transition] = [Transition(key, "Created", created)]
        for _, to_status, ts in raw:
            label = workflow.status_to_stage.get(to_status, to_status)
            transitions.append(Transition(key, label, ts))

        # Map each raw transition to (canonical_stage | None, timestamp)
        mapped: list[tuple[str | None, datetime]] = [
            (workflow.status_to_stage.get(to_s), ts) for _, to_s, ts in raw
        ]

        # Compute cumulative minutes per stage using carry-forward for unmapped statuses:
        # when a transition targets an unmapped status, time keeps accumulating in the
        # last known stage rather than being lost.
        stage_minutes: dict[str, int] = {s: 0 for s in workflow.stages}
        first_date: datetime | None = None
        inprogress_date: datetime | None = None
        closed_date: datetime | None = None

        # Pre-transition period: creation → first explicit transition, attributed to
        # the initial stage (carry-forward applies here too via initial_stage fallback).
        current_stage: str | None = initial_stage
        if mapped and current_stage:
            pre_duration = max(0, int((mapped[0][1] - created).total_seconds() / 60))
            stage_minutes[current_stage] += pre_duration

        for i, (stage, entry_ts) in enumerate(mapped):
            exit_ts = mapped[i + 1][1] if i + 1 < len(mapped) else reference_dt
            duration = max(0, int((exit_ts - entry_ts).total_seconds() / 60))

            if stage is None:
                # Unmapped: carry forward time to the last known stage
                if current_stage:
                    stage_minutes[current_stage] += duration
            else:
                # Mapped: accumulate in this stage and advance the pointer
                stage_minutes[stage] += duration
                current_stage = stage

                if stage == workflow.first_stage and first_date is None:
                    first_date = entry_ts
                if stage == workflow.inprogress_stage and inprogress_date is None:
                    inprogress_date = entry_ts
                if stage == workflow.closed_stage:
                    closed_date = entry_ts  # letzter Eintritt zählt

        # Compute stage indices for milestone fallbacks once, reused below.
        first_idx = (
            workflow.stages.index(workflow.first_stage)
            if workflow.first_stage is not None else -1
        )
        inprog_idx = (
            workflow.stages.index(workflow.inprogress_stage)
            if workflow.inprogress_stage is not None else -1
        )
        closed_idx = (
            workflow.stages.index(workflow.closed_stage)
            if workflow.closed_stage is not None else len(workflow.stages)
        )

        # Fallback: First stage was skipped — use the earliest entry in a stage
        # that lies chronologically after First (and before Closed) in workflow order.
        if first_date is None and first_idx >= 0:
            for stage, entry_ts in mapped:
                if stage is not None:
                    s_idx = workflow.stages.index(stage)
                    if first_idx < s_idx < closed_idx:
                        first_date = entry_ts
                        break

        # Fallback: InProgress stage was skipped (but development occurred) — use
        # the earliest entry in a stage after InProgress (and before Closed).
        if first_date is not None and inprogress_date is None and inprog_idx >= 0:
            for stage, entry_ts in mapped:
                if stage is not None:
                    s_idx = workflow.stages.index(stage)
                    if inprog_idx < s_idx < closed_idx:
                        inprogress_date = entry_ts
                        break

        # Fallback: development started but Closed stage was skipped — use the first
        # stage that comes after the Closed stage in workflow order.
        if first_date is not None and closed_date is None and workflow.closed_stage is not None:
            for stage, entry_ts in mapped:
                if stage is not None and workflow.stages.index(stage) > closed_idx:
                    closed_date = entry_ts
                    break

        # Guard: if the issue's current status maps to a stage before Closed,
        # the issue has been reopened and is not closed — clear the closed_date.
        if closed_date is not None and workflow.closed_stage is not None:
            current_mapped = workflow.status_to_stage.get(current_status)
            if current_mapped is not None and workflow.stages.index(current_mapped) < closed_idx:
                closed_date = None

        # Guard: no Closed Date without First Date. Issues that jumped directly
        # from To Do to Closed without ever being In Progress were never worked on
        # and must not appear as closed in any metric.
        if closed_date is not None and first_date is None:
            closed_date = None

        records.append(IssueRecord(
            project=project,
            key=key,
            issuetype=issuetype,
            status=current_status,
            created=created,
            component=component,
            first_date=first_date,
            inprogress_date=inprogress_date,
            closed_date=closed_date,
            stage_minutes=stage_minutes,
            resolution=resolution,
            initial_stage=initial_stage,
            transitions=transitions,
        ))

    return records, unmapped_statuses
