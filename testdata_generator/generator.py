# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       02.05.2026
# Geändert:       02.05.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Kernlogik des testdata_generator. Simuliert synthetische Jira-Issues mit
#   realistischen Status-Übergängen entlang eines definierten Workflows.
#   Erzeugt JSON im Jira-REST-API-Format (kompatibel mit transform_data).
# =============================================================================

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from .workflow_parser import WorkflowSpec


@dataclass
class GeneratorConfig:
    """
    Configuration for synthetic issue generation.

    Args:
        project_key:      Jira project key used for issue keys and project field.
        issue_count:      Total number of issues to generate.
        from_date:        Earliest possible issue creation date.
        to_date:          Latest possible issue creation/transition date.
        issue_types:      Mapping of issue type name to relative weight (will be normalised).
        completion_rate:  Fraction of issues that reach the closed stage (0.0–1.0).
        todo_rate:        Fraction of non-complete issues that stay in a To Do stage
                          (before first_stage). Applied to open issues only.
        backflow_prob:    Probability of a backward transition at each step (0.0–1.0).
        min_dwell_hours:  Minimum hours an issue spends in a stage before transitioning.
        max_dwell_hours:  Maximum hours an issue spends in a stage before transitioning.
        seed:             Optional RNG seed for reproducible output.
    """

    project_key: str = "TEST"
    issue_count: int = 100
    from_date: date = field(default_factory=lambda: date(2025, 1, 1))
    to_date: date = field(default_factory=lambda: date(2025, 12, 31))
    issue_types: dict[str, float] = field(
        default_factory=lambda: {"Feature": 0.6, "Bug": 0.3, "Enabler": 0.1}
    )
    completion_rate: float = 0.7
    todo_rate: float = 0.15
    backflow_prob: float = 0.1
    min_dwell_hours: int = 1
    max_dwell_hours: int = 240
    seed: int | None = None


def _fmt_dt(dt: datetime) -> str:
    """Format datetime as Jira ISO string: 2025-11-30T16:49:19.000+0100."""
    offset = dt.utcoffset() or timedelta(0)
    total_seconds = int(offset.total_seconds())
    sign = "+" if total_seconds >= 0 else "-"
    abs_seconds = abs(total_seconds)
    hours, remainder = divmod(abs_seconds, 3600)
    minutes = remainder // 60
    return f"{dt.strftime('%Y-%m-%dT%H:%M:%S')}.000{sign}{hours:02d}{minutes:02d}"


def _random_datetime(rng: random.Random, from_date: date, to_date: date) -> datetime:
    """Return a random datetime (UTC+1) within the given date range."""
    delta_days = (to_date - from_date).days
    offset_days = rng.randint(0, max(0, delta_days))
    hour = rng.randint(7, 17)
    minute = rng.randint(0, 59)
    second = rng.randint(0, 59)
    d = from_date + timedelta(days=offset_days)
    return datetime(d.year, d.month, d.day, hour, minute, second, tzinfo=timezone(timedelta(hours=1)))


def _choose_weighted(rng: random.Random, weights: dict[str, float]) -> str:
    """Choose a key from a dict with relative weights."""
    keys = list(weights.keys())
    values = list(weights.values())
    total = sum(values)
    r = rng.random() * total
    cumulative = 0.0
    for key, value in zip(keys, values):
        cumulative += value
        if r <= cumulative:
            return key
    return keys[-1]


def _make_history(
    from_stage: str,
    to_stage: str,
    ts: datetime,
    history_id: int,
) -> dict:
    """Build a single Jira changelog history entry for a status transition."""
    return {
        "id": str(history_id),
        "author": {
            "name": "generated_user",
            "key": "generated_user",
            "emailAddress": "generated@example.invalid",
            "displayName": "Generated User",
            "active": True,
            "timeZone": "Europe/Berlin",
        },
        "created": _fmt_dt(ts),
        "items": [
            {
                "field": "status",
                "fieldtype": "jira",
                "from": None,
                "fromString": from_stage,
                "to": None,
                "toString": to_stage,
            }
        ],
    }


def _simulate_issue(
    workflow: WorkflowSpec,
    config: GeneratorConfig,
    rng: random.Random,
    issue_num: int,
) -> dict:
    """
    Simulate a single Jira issue with status transitions along the workflow.

    Returns a dict in Jira REST API format.
    """
    stages = workflow.stages
    if not stages:
        raise ValueError("Workflow has no stages")

    first_idx = stages.index(workflow.first_stage) if (
        workflow.first_stage and workflow.first_stage in stages
    ) else 0
    closed_idx = stages.index(workflow.closed_stage) if (
        workflow.closed_stage and workflow.closed_stage in stages
    ) else len(stages) - 1

    created_ts = _random_datetime(rng, config.from_date, config.to_date)
    issue_type = _choose_weighted(rng, config.issue_types)

    is_complete = rng.random() < config.completion_rate

    if is_complete:
        target_idx = closed_idx
    else:
        # Decide if this is a To Do issue (before first_stage) or In Progress
        if first_idx > 0 and rng.random() < config.todo_rate:
            target_idx = rng.randint(0, first_idx - 1)
        elif closed_idx > first_idx:
            target_idx = rng.randint(first_idx, closed_idx - 1)
        else:
            target_idx = first_idx

    histories: list[dict] = []
    current_idx = 0  # issues implicitly start in stages[0]
    current_ts = created_ts
    hist_id = issue_num * 10000
    max_steps = len(stages) * 6  # prevent runaway loops with high backflow_prob

    step = 0
    while current_idx < target_idx and step < max_steps:
        step += 1

        # Possible backflow after first_stage, but never back before it
        if current_idx > first_idx and rng.random() < config.backflow_prob:
            back_idx = max(first_idx, current_idx - 1)
            dwell = rng.randint(config.min_dwell_hours, config.max_dwell_hours)
            current_ts += timedelta(hours=dwell)
            histories.append(_make_history(stages[current_idx], stages[back_idx], current_ts, hist_id))
            hist_id += 1
            current_idx = back_idx
            continue

        next_idx = current_idx + 1
        dwell = rng.randint(config.min_dwell_hours, config.max_dwell_hours)
        current_ts += timedelta(hours=dwell)
        histories.append(_make_history(stages[current_idx], stages[next_idx], current_ts, hist_id))
        hist_id += 1
        current_idx = next_idx

    current_stage = stages[current_idx]
    numeric_id = 100000 + issue_num
    key = f"{config.project_key}-{issue_num + 1}"

    return {
        "expand": "operations,versionedRepresentations,editmeta,changelog,renderedFields",
        "id": str(numeric_id),
        "self": f"https://jira.example.com/rest/api/latest/issue/{numeric_id}",
        "key": key,
        "fields": {
            "issuetype": {
                "id": "1",
                "name": issue_type,
                "subtask": False,
            },
            "components": [],
            "created": _fmt_dt(created_ts),
            "project": {
                "id": "1",
                "key": config.project_key,
                "name": config.project_key,
            },
            "resolution": None,
            "status": {
                "id": "1",
                "name": current_stage,
            },
        },
        "changelog": {
            "startAt": 0,
            "maxResults": len(histories),
            "total": len(histories),
            "histories": histories,
        },
    }


def generate(workflow: WorkflowSpec, config: GeneratorConfig) -> dict:
    """
    Generate synthetic Jira issues in REST API JSON format.

    Args:
        workflow: Parsed workflow specification (stages, first_stage, closed_stage).
        config:   Generation parameters (issue count, dates, completion rate, etc.).

    Returns:
        Dict matching the Jira REST API envelope:
        {"expand": ..., "startAt": 0, "maxResults": N, "total": N, "issues": [...]}
    """
    rng = random.Random(config.seed)
    issues = [
        _simulate_issue(workflow, config, rng, i)
        for i in range(config.issue_count)
    ]
    return {
        "expand": "schema,names",
        "startAt": 0,
        "maxResults": config.issue_count,
        "total": config.issue_count,
        "issues": issues,
    }
