# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       02.05.2026
# Geändert:       13.05.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Kernlogik des testdata_generator. Simuliert synthetische Jira-Issues mit
#   realistischen Status-Übergängen entlang eines definierten Workflows.
#   Unterstützt vier Flow-Muster (Triangle, Flat Triangle, Cluster, Batch)
#   sowie lognormale Cycle-Time-Verteilung. Erzeugt JSON im Jira-REST-API-
#   Format (kompatibel mit transform_data).
# =============================================================================

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from math import ceil

from .workflow_parser import WorkflowSpec

PATTERN_NONE = "none"
PATTERN_TRIANGLE = "triangle"
PATTERN_FLAT_TRIANGLE = "flat_triangle"
PATTERN_CLUSTER = "cluster"
PATTERN_BATCH = "batch"


@dataclass
class GeneratorConfig:
    """
    Configuration for synthetic issue generation.

    Args:
        project_key:       Jira project key used for issue keys and project field.
        issue_count:       Total number of issues to generate.
        from_date:         Earliest possible issue creation date.
        to_date:           Latest possible issue creation/transition date.
        issue_types:       Mapping of issue type name to relative weight (will be normalised).
        completion_rate:   Fraction of issues that reach the closed stage (0.0–1.0).
        todo_rate:         Fraction of non-complete issues that stay in a To Do stage.
        backflow_prob:     Probability of a backward transition at each step (0.0–1.0).
        min_dwell_hours:   Minimum hours an issue spends in a stage (normal mode only).
        max_dwell_hours:   Maximum hours an issue spends in a stage (normal mode only).
        seed:              Optional RNG seed for reproducible output.
        mean_cycle_days:   Target mean cycle time in days (lognormal). None = use dwell hours.
        std_cycle_days:    Std deviation of cycle time in days. None = 30 % of mean.
        pattern:           Flow pattern: none | triangle | flat_triangle | cluster | batch.
        pi_duration_weeks: PI cycle length in weeks (used by cluster/batch patterns).
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
    mean_cycle_days: float | None = None
    std_cycle_days: float | None = None
    pattern: str = PATTERN_NONE
    pi_duration_weeks: int = 12


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
    return datetime(d.year, d.month, d.day, hour, minute, second,
                    tzinfo=timezone(timedelta(hours=1)))


def _make_history(from_stage: str, to_stage: str, ts: datetime, history_id: int) -> dict:
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


def _sample_ct_days(rng: random.Random, mean: float, std: float) -> float:
    """Sample a cycle time from a lognormal distribution with given mean and std (in days)."""
    if mean <= 0:
        return 1.0
    if std <= 0:
        return max(1.0, mean)
    cv2 = (std / mean) ** 2
    sigma = math.sqrt(math.log(1 + cv2))
    mu = math.log(mean) - sigma ** 2 / 2
    return max(1.0, rng.lognormvariate(mu, sigma))


def _fill_time_budget(rng: random.Random, n_steps: int, total_hours: float) -> list[float]:
    """Distribute total_hours across n_steps using exponential draws (Dirichlet-like)."""
    if n_steps <= 0:
        return []
    draws = [rng.expovariate(1.0) for _ in range(n_steps)]
    total = sum(draws)
    return [d / total * total_hours for d in draws]


def _compute_pi_ends(from_date: date, to_date: date, pi_weeks: int) -> list[date]:
    """Return the list of PI end dates within the given range."""
    ends: list[date] = []
    current = from_date + timedelta(weeks=pi_weeks)
    while current <= to_date:
        ends.append(current)
        current += timedelta(weeks=pi_weeks)
    return ends or [to_date]


def _sample_pi_close_dt(
    rng: random.Random, pi_ends: list[date], config: GeneratorConfig
) -> datetime:
    """
    Sample a closed datetime concentrated in the last 2 weeks of a random PI.
    Uses Beta(2, 0.5) to skew deliveries toward the PI end date.
    """
    pi_end = rng.choice(pi_ends)
    u = rng.betavariate(2.0, 0.5)
    offset_days = int(u * 14)
    close_date = pi_end - timedelta(days=14 - offset_days)
    close_date = max(config.from_date + timedelta(days=1), min(close_date, config.to_date))
    return datetime(
        close_date.year, close_date.month, close_date.day,
        rng.randint(7, 17), rng.randint(0, 59), rng.randint(0, 59),
        tzinfo=timezone(timedelta(hours=1)),
    )


def _simulate_issue(
    workflow: WorkflowSpec,
    config: GeneratorConfig,
    rng: random.Random,
    issue_num: int,
    target_ct_hours: float | None = None,
    target_closed_dt: datetime | None = None,
    _prerolled_incomplete: bool = False,
) -> dict:
    """
    Simulate a single Jira issue with status transitions along the workflow.

    When target_ct_hours is provided (pattern mode), the transition chain is
    forward-only with time distributed proportionally across stages. When None,
    the original random dwell / backflow logic is used.

    Returns a dict in Jira REST API format.
    """
    stages = workflow.stages
    if not stages:
        raise ValueError("Workflow has no stages")

    first_idx = (stages.index(workflow.first_stage)
                 if workflow.first_stage and workflow.first_stage in stages else 0)
    closed_idx = (stages.index(workflow.closed_stage)
                  if workflow.closed_stage and workflow.closed_stage in stages
                  else len(stages) - 1)

    issue_type = rng.choices(
        list(config.issue_types.keys()), weights=list(config.issue_types.values()), k=1
    )[0]

    # ── Determine created_ts and target_idx ──────────────────────────────────
    target_idx: int
    if target_ct_hours is not None:
        # Pattern mode: always complete, CT is controlled externally
        target_idx = closed_idx
        if target_closed_dt is not None:
            # Cluster / Batch: work backwards from the prescribed close date
            created_ts = target_closed_dt - timedelta(hours=target_ct_hours)
            from_dt = datetime(
                config.from_date.year, config.from_date.month, config.from_date.day,
                7, 0, 0, tzinfo=timezone(timedelta(hours=1)),
            )
            if created_ts < from_dt:
                created_ts = from_dt
        else:
            # Triangle / Flat-Triangle: random start, CT budget determines close date
            safe_to = config.to_date - timedelta(days=ceil(target_ct_hours / 24) + 1)
            if safe_to < config.from_date:
                safe_to = config.from_date
            created_ts = _random_datetime(rng, config.from_date, safe_to)
    else:
        # Normal mode (original logic)
        is_complete = False if _prerolled_incomplete else rng.random() < config.completion_rate
        if is_complete:
            target_idx = closed_idx
            expected_steps = ceil(closed_idx / max(0.01, 1.0 - config.backflow_prob))
            buffer_days = ceil((expected_steps + first_idx) * config.max_dwell_hours / 24) + 1
            latest_start = config.to_date - timedelta(days=buffer_days)
            if latest_start < config.from_date:
                latest_start = config.from_date
            created_ts = _random_datetime(rng, config.from_date, latest_start)
        else:
            if first_idx > 0 and rng.random() < config.todo_rate:
                target_idx = rng.randint(0, first_idx - 1)
            elif closed_idx > first_idx:
                target_idx = rng.randint(first_idx, closed_idx - 1)
            else:
                target_idx = first_idx
            created_ts = _random_datetime(rng, config.from_date, config.to_date)

    # ── Simulate transition chain ────────────────────────────────────────────
    histories: list[dict] = []
    current_idx = 0
    current_ts = created_ts
    hist_id = issue_num * 10000

    if target_ct_hours is not None:
        # Pattern mode: forward-only with Dirichlet-like time distribution
        n_fwd = target_idx - current_idx
        dwells = _fill_time_budget(rng, n_fwd, target_ct_hours)
        for dwell in dwells:
            nxt = current_idx + 1
            current_ts += timedelta(hours=max(1.0, dwell))
            histories.append(_make_history(stages[current_idx], stages[nxt], current_ts, hist_id))
            hist_id += 1
            current_idx = nxt
    else:
        # Normal mode: random dwell with optional backflow
        max_steps = len(stages) * 6
        step = 0
        while current_idx < target_idx and step < max_steps:
            step += 1
            if current_idx > first_idx and rng.random() < config.backflow_prob:
                back_idx = max(first_idx, current_idx - 1)
                dwell = rng.randint(config.min_dwell_hours, config.max_dwell_hours)
                current_ts += timedelta(hours=dwell)
                histories.append(
                    _make_history(stages[current_idx], stages[back_idx], current_ts, hist_id)
                )
                hist_id += 1
                current_idx = back_idx
                continue
            nxt = current_idx + 1
            dwell = rng.randint(config.min_dwell_hours, config.max_dwell_hours)
            current_ts += timedelta(hours=dwell)
            histories.append(_make_history(stages[current_idx], stages[nxt], current_ts, hist_id))
            hist_id += 1
            current_idx = nxt

    current_stage = stages[current_idx]
    numeric_id = 100000 + issue_num
    key = f"{config.project_key}-{issue_num + 1}"

    return {
        "expand": "operations,versionedRepresentations,editmeta,changelog,renderedFields",
        "id": str(numeric_id),
        "self": f"https://jira.example.com/rest/api/latest/issue/{numeric_id}",
        "key": key,
        "fields": {
            "issuetype": {"id": "1", "name": issue_type, "subtask": False},
            "components": [],
            "created": _fmt_dt(created_ts),
            "project": {"id": "1", "key": config.project_key, "name": config.project_key},
            "resolution": None,
            "status": {"id": "1", "name": current_stage},
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
        config:   Generation parameters (issue count, dates, completion rate, pattern, etc.).

    Returns:
        Dict matching the Jira REST API envelope:
        {"expand": ..., "startAt": 0, "maxResults": N, "total": N, "issues": [...]}
    """
    rng = random.Random(config.seed)
    n = config.issue_count

    pi_ends: list[date] = []
    if config.pattern in (PATTERN_CLUSTER, PATTERN_BATCH):
        pi_ends = _compute_pi_ends(config.from_date, config.to_date, config.pi_duration_weeks)

    issues: list[dict] = []
    for i in range(n):
        t = i / max(1, n - 1)  # normalised position [0, 1] across all issues
        target_ct_hours: float | None = None
        target_closed_dt: datetime | None = None
        prerolled_incomplete = False

        if config.mean_cycle_days is not None:
            will_complete = rng.random() < config.completion_rate
            if will_complete:
                mean = config.mean_cycle_days
                std = config.std_cycle_days if config.std_cycle_days is not None else mean * 0.3

                if config.pattern == PATTERN_TRIANGLE:
                    mult = 1.0 + 3.0 * t
                    ct_days = _sample_ct_days(rng, mean * mult, std * mult)
                    target_ct_hours = ct_days * 24

                elif config.pattern == PATTERN_FLAT_TRIANGLE:
                    mult = 1.0 + 3.0 * math.tanh(2.5 * t)
                    ct_days = _sample_ct_days(rng, mean * mult, std * mult)
                    target_ct_hours = ct_days * 24

                elif config.pattern == PATTERN_CLUSTER:
                    ct_days = _sample_ct_days(rng, mean, std)
                    target_ct_hours = ct_days * 24
                    target_closed_dt = _sample_pi_close_dt(rng, pi_ends, config)

                elif config.pattern == PATTERN_BATCH:
                    ct_days = rng.uniform(mean * 0.1, mean * 3.0)
                    target_ct_hours = max(24.0, ct_days * 24)
                    target_closed_dt = _sample_pi_close_dt(rng, pi_ends, config)

                else:  # PATTERN_NONE with mean_cycle_days set: lognormal without shape
                    ct_days = _sample_ct_days(rng, mean, std)
                    target_ct_hours = ct_days * 24
            else:
                prerolled_incomplete = True

        issues.append(
            _simulate_issue(workflow, config, rng, i, target_ct_hours, target_closed_dt,
                            _prerolled_incomplete=prerolled_incomplete)
        )

    return {
        "expand": "schema,names",
        "startAt": 0,
        "maxResults": n,
        "total": n,
        "issues": issues,
    }
