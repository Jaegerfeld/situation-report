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
    stage_minutes: dict[str, int]  # canonical stage -> minutes (only from explicit transitions)
    resolution: str
    initial_stage: str | None      # stage before any transition (for CFD)
    transitions: list[Transition]  # sorted by timestamp; first entry is always "Created"


def process_issues(
    json_path: Path,
    workflow: Workflow,
    reference_dt: datetime | None = None,
) -> list[IssueRecord]:
    """
    Parse Jira JSON export and compute per-issue stage times.

    Stage time rules:
    - Only explicit status transitions from the Jira changelog are counted.
    - Time from issue creation to first transition is NOT counted.
    - The current (last) stage accumulates time up to reference_dt.
    - Issues with no transitions have all-zero stage times.
    """
    if reference_dt is None:
        reference_dt = datetime.now(tz=timezone.utc)

    data = json.loads(json_path.read_text(encoding="utf-8"))
    records: list[IssueRecord] = []

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

        # Initial stage for CFD: the status the issue had before its first transition.
        # If no transitions, use the current status (it has never changed).
        initial_status = raw[0][0] if raw else current_status
        initial_stage = workflow.status_to_stage.get(initial_status)

        # Build sorted transition list (for Transitions CSV and CFD)
        transitions: list[Transition] = [Transition(key, "Created", created)]
        for _, to_status, ts in raw:
            label = workflow.status_to_stage.get(to_status, to_status)
            transitions.append(Transition(key, label, ts))

        # Map each raw transition to (canonical_stage | None, timestamp)
        mapped: list[tuple[str | None, datetime]] = [
            (workflow.status_to_stage.get(to_s), ts) for _, to_s, ts in raw
        ]

        # Compute cumulative minutes per stage
        stage_minutes: dict[str, int] = {s: 0 for s in workflow.stages}
        first_date: datetime | None = None
        inprogress_date: datetime | None = None
        closed_date: datetime | None = None

        # Count the pre-transition period (creation → first explicit transition) in the
        # initial stage. If the initial status is unmapped, fall back to the first stage
        # in the workflow (typically "Funnel").
        if mapped:
            pre_stage = initial_stage or (workflow.stages[0] if workflow.stages else None)
            if pre_stage:
                pre_duration = max(0, int((mapped[0][1] - created).total_seconds() / 60))
                stage_minutes[pre_stage] += pre_duration

        for i, (stage, entry_ts) in enumerate(mapped):
            if stage is None:
                continue
            exit_ts = mapped[i + 1][1] if i + 1 < len(mapped) else reference_dt
            duration = max(0, int((exit_ts - entry_ts).total_seconds() / 60))
            stage_minutes[stage] += duration

            if stage == workflow.first_stage and first_date is None:
                first_date = entry_ts
            if stage == workflow.inprogress_stage and inprogress_date is None:
                inprogress_date = entry_ts
            if stage == workflow.closed_stage and closed_date is None:
                closed_date = entry_ts

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

    return records
