# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       13.10.2026
# Geändert:       13.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Fortschreibung eines erzeugten Datensatzes (Auftrag Robert 13.10.2026):
#   Ein Rohdatensatz (Jira-JSON) ist ein Abzug zum Stichtag T1. Die
#   Fortschreibung auf T2 erzeugt den Abzug, den man an T2 gezogen hätte —
#   „ganz so wie wenn man zweimal manuell Daten abgezogen hätte":
#   (1) Die Vergangenheit ist unantastbar: Schlüssel, Anlagedatum und alle
#       Übergänge bis T1 bleiben byteidentisch.
#   (2) Offene Vorgänge laufen weiter: ab T1 neue Übergänge nach demselben
#       Pfad-/Zeitmodell, bis sie fertig sind oder T2 erreicht ist.
#   (3) Neue Vorgänge kommen in (T1, T2] dazu; Schlüssel laufen weiter.
#   (4) Reproduzierbar: Seed je Fortschreibung = Basis-Seed + T2.
#   Der Generator schreibt dazu Metadaten in den JSON-Envelope (Schlüssel
#   "generator": Stichtag, Seed, Regler, Stages); transform_data liest nur
#   "issues" und bleibt unberührt. Ohne Metadaten gilt T1 = jüngster
#   Zeitstempel, und die Regler kommen vom Aufrufer.
# =============================================================================

from __future__ import annotations

import copy
import dataclasses
import random
from datetime import date, datetime, timedelta, timezone
from typing import Any

from .generator import (
    GeneratorConfig,
    _fill_time_budget,
    _fmt_dt,
    _make_history,
    _sample_ct_days,
    generate,
)
from .paths import PathSpec, detect_parking, knobs_at, sample_path
from .workflow_parser import WorkflowSpec

META_KEY = "generator"
META_SCHEMA = 1
_TZ = timezone(timedelta(hours=1))


class ContinuationError(ValueError):
    """The data set cannot be continued as requested."""


# ---------------------------------------------------------------------------
# Envelope-Metadaten
# ---------------------------------------------------------------------------

def build_meta(config: GeneratorConfig, workflow: WorkflowSpec,
               continued_from: list[str] | None = None) -> dict[str, Any]:
    """The envelope record the generator writes next to ``issues``."""
    cfg = dataclasses.asdict(config)
    cfg["from_date"] = config.from_date.isoformat()
    cfg["to_date"] = config.to_date.isoformat()
    return {
        "schema": META_SCHEMA,
        "tool": "situation-report testdata_generator",
        "from_date": config.from_date.isoformat(),
        "to_date": config.to_date.isoformat(),
        "seed": config.seed,
        "config": cfg,
        "stages": list(workflow.stages),
        "continued_from": list(continued_from or []),
    }


def read_meta(data: dict[str, Any]) -> dict[str, Any] | None:
    """The generator record, or None for a file without one (e.g. a real export)."""
    meta = data.get(META_KEY)
    if isinstance(meta, dict) and meta.get("schema") == META_SCHEMA:
        return meta
    return None


def config_from_meta(meta: dict[str, Any]) -> GeneratorConfig:
    """Rebuild the GeneratorConfig the data set was made with."""
    raw = dict(meta.get("config") or {})
    known = {f.name for f in dataclasses.fields(GeneratorConfig)}
    kwargs = {k: v for k, v in raw.items() if k in known}
    for key in ("from_date", "to_date"):
        if key in kwargs and isinstance(kwargs[key], str):
            kwargs[key] = date.fromisoformat(kwargs[key])
    return GeneratorConfig(**kwargs)


def _parse_dt(text: str) -> datetime:
    """Parse the generator's Jira timestamp (2025-11-30T16:49:19.000+0100)."""
    base, _, rest = text.partition(".")
    sign = 1 if rest[3] == "+" else -1
    hh, mm = int(rest[4:6]), int(rest[6:8])
    tz = timezone(sign * timedelta(hours=hh, minutes=mm))
    return datetime.strptime(base, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=tz)


def latest_timestamp(data: dict[str, Any]) -> datetime | None:
    """The youngest timestamp in the data set (creation or transition)."""
    latest: datetime | None = None
    for issue in data.get("issues", []):
        stamps = [issue["fields"]["created"]]
        stamps += [h["created"] for h in issue.get("changelog", {}).get("histories", [])]
        for s in stamps:
            ts = _parse_dt(s)
            if latest is None or ts > latest:
                latest = ts
    return latest


# ---------------------------------------------------------------------------
# Fortschreibung
# ---------------------------------------------------------------------------

def _key_number(key: str) -> int:
    return int(key.rsplit("-", 1)[1])


def _continue_issue(issue: dict[str, Any], workflow: WorkflowSpec, config: GeneratorConfig,
                    rng: random.Random, start_dt: datetime, to_dt: datetime) -> dict[str, Any]:
    """
    Give one open issue its life after T1: a fresh path from its current
    stage, time laid over it from ``start_dt``, cut at ``to_dt``. Returns the
    issue unchanged when it is terminal (closed or in the final stage) or when
    the dice let it rest.
    """
    stages = workflow.stages
    first_idx = (stages.index(workflow.first_stage)
                 if workflow.first_stage and workflow.first_stage in stages else 0)
    closed_idx = (stages.index(workflow.closed_stage)
                  if workflow.closed_stage and workflow.closed_stage in stages
                  else len(stages) - 1)
    status = issue["fields"]["status"]["name"]
    if status not in stages:
        return issue
    cur = stages.index(status)
    if cur >= closed_idx:
        return issue                                  # closed, archived or cancelled
    completes = rng.random() < config.completion_rate
    if completes:
        target = closed_idx
    else:
        lo = max(cur, first_idx)
        target = rng.randint(lo, max(lo, closed_idx - 1))
        if target == cur:
            return issue                              # rests until the next cut
    spec = PathSpec(
        n_stages=len(stages), first_idx=first_idx, closed_idx=closed_idx,
        target_idx=target, parking_idx=detect_parking(stages, config.parking_stage),
        backflow_prob=config.backflow_prob, knobs=knobs_at(config.realism),
        start_idx=cur)
    path = sample_path(spec, rng)
    if not path:
        return issue
    if config.mean_cycle_days is not None:
        std = (config.std_cycle_days if config.std_cycle_days is not None
               else config.mean_cycle_days * 0.3)
        budget = _sample_ct_days(rng, config.mean_cycle_days, std) * 24
        # the remaining work is a share of a whole cycle: as many steps as are left
        share = len(path) / max(len(path), closed_idx)
        dwells = [max(1.0, d) for d in _fill_time_budget(rng, len(path), budget * share)]
    else:
        dwells = [float(rng.randint(config.min_dwell_hours, config.max_dwell_hours))
                  for _ in path]

    out = copy.deepcopy(issue)
    histories = out["changelog"]["histories"]
    # ids follow the generator scheme (key n -> (n-1)*10000 + k); an issue
    # without history so far starts at its own block, not at the next one
    hist_id = max((int(h["id"]) for h in histories),
                  default=(_key_number(out["key"]) - 1) * 10000 - 1) + 1
    ts = start_dt + timedelta(hours=rng.randint(0, 72))      # not everyone moves on day one
    idx = cur
    for nxt, dwell in zip(path, dwells):
        ts = ts + timedelta(hours=dwell)
        if ts > to_dt:
            break
        histories.append(_make_history(stages[idx], stages[nxt], ts, hist_id))
        hist_id += 1
        idx = nxt
    out["fields"]["status"]["name"] = stages[idx]
    out["changelog"]["total"] = len(histories)
    out["changelog"]["maxResults"] = len(histories)
    return out


def _renumber(issue: dict[str, Any], project_key: str, number: int) -> dict[str, Any]:
    """Give a freshly generated issue the next free key (and matching ids)."""
    issue["key"] = f"{project_key}-{number}"
    issue["id"] = str(100000 + number - 1)
    issue["self"] = f"https://jira.example.com/rest/api/latest/issue/{100000 + number - 1}"
    for k, h in enumerate(issue["changelog"]["histories"]):
        h["id"] = str((number - 1) * 10000 + k)
    return issue


def continue_generation(
    data: dict[str, Any],
    workflow: WorkflowSpec,
    to_date: date,
    config: GeneratorConfig | None = None,
    new_issue_count: int | None = None,
    rate_per_day: float | None = None,
    seed: int | None = None,
) -> dict[str, Any]:
    """
    The data set as a second extract taken on ``to_date`` (T2).

    Args:
        data:            The earlier extract (generator JSON, with or without
                         the "generator" record).
        workflow:        The workflow the data set follows.
        to_date:         The new cut T2; must lie after T1.
        config:          Generator knobs for the continuation; defaults to the
                         knobs stored in the record. Required without a record.
        new_issue_count: Number of issues created in (T1, T2]; default from the
                         earlier rate (issues per day of the first window).
        rate_per_day:    Alternative to new_issue_count: issues per day.
        seed:            Base seed; default the record's seed. The effective
                         seed is derived from base seed and T2, so repeating the
                         same continuation repeats the result.

    Raises:
        ContinuationError: T2 not after T1, no knobs available, or a workflow
                           whose stages differ from the record's.
    """
    meta = read_meta(data)
    if config is None:
        if meta is None:
            raise ContinuationError(
                "The file carries no generator record - pass the generator knobs explicitly.")
        config = config_from_meta(meta)
    if meta is not None and meta.get("stages") and list(meta["stages"]) != list(workflow.stages):
        raise ContinuationError(
            f"Workflow stages differ from the record: {meta['stages']} vs {workflow.stages}.")

    if meta is not None:
        t1 = date.fromisoformat(meta["to_date"])
    else:
        latest = latest_timestamp(data)
        if latest is None:
            raise ContinuationError("The data set has no issues to continue.")
        t1 = latest.date()
    if to_date <= t1:
        raise ContinuationError(f"to_date {to_date} must lie after the last cut {t1}.")

    base_seed = seed if seed is not None else (meta.get("seed") if meta else None)
    rng = random.Random(f"{base_seed}|{to_date.isoformat()}")
    start_dt = datetime(t1.year, t1.month, t1.day, 7, 0, 0, tzinfo=_TZ) + timedelta(days=1)
    to_dt = datetime(to_date.year, to_date.month, to_date.day, 23, 59, 59, tzinfo=_TZ)

    issues = [_continue_issue(iss, workflow, config, rng, start_dt, to_dt)
              for iss in data.get("issues", [])]

    # new issues: the earlier rate, unless told otherwise
    first_day = config.from_date
    if meta is not None:
        first_day = date.fromisoformat(meta.get("from_date", config.from_date.isoformat()))
    span_before = max(1, (t1 - first_day).days + 1)
    if new_issue_count is None:
        rate = rate_per_day if rate_per_day is not None else len(issues) / span_before
        new_issue_count = round(rate * ((to_date - t1).days))
    new_issue_count = max(0, new_issue_count)
    next_number = max((_key_number(i["key"]) for i in issues), default=0) + 1
    if new_issue_count:
        new_config = dataclasses.replace(
            config, issue_count=new_issue_count, from_date=t1 + timedelta(days=1),
            to_date=to_date, seed=rng.randrange(1 << 30))
        fresh = generate(workflow, new_config)
        for i, iss in enumerate(fresh["issues"]):
            issues.append(_renumber(iss, config.project_key, next_number + i))

    out: dict[str, Any] = {
        "expand": "schema,names", "startAt": 0,
        "maxResults": len(issues), "total": len(issues), "issues": issues,
    }
    continued = list(meta.get("continued_from", [])) if meta else []
    continued.append(t1.isoformat())
    new_meta = build_meta(dataclasses.replace(config, to_date=to_date, seed=base_seed),
                          workflow, continued)
    if meta is not None:
        new_meta["from_date"] = meta.get("from_date", new_meta["from_date"])
    out[META_KEY] = new_meta
    return out


def cut_timestamp(t1: date) -> datetime:
    """End of day T1 in the generator's time zone — the border of the untouchable past."""
    return datetime(t1.year, t1.month, t1.day, 23, 59, 59, tzinfo=_TZ)


__all__ = ["META_KEY", "META_SCHEMA", "ContinuationError", "build_meta", "read_meta",
           "config_from_meta", "latest_timestamp", "continue_generation", "cut_timestamp",
           "_fmt_dt"]
