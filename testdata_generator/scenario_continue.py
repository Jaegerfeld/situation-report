# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       13.10.2026
# Geändert:       26.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Fortschreibung eines ganzen Portfolio-Datenraums (Schritt 3 der
#   Generator-Überarbeitung, Auftrag Robert 13.10.2026): Der Demo-Ordner aus
#   build_portfolio_scenario ist ein Abzug zum Referenzdatum R1. Die
#   Fortschreibung auf R2 zieht jeden Roh-Abzug (raw/*_jira.json) mit
#   continuation.continue_generation nach — die Vergangenheit bleibt, offene
#   Vorgänge laufen weiter, neue kommen dazu; eine veraltete Quelle (Beta-3,
#   Datenstand 60 Tage alt) bleibt genau so veraltet —, lässt transform_data
#   die IssueTimes/Transitions/CFD neu schreiben, schiebt das Datenfenster der
#   Solution- und Portfolio-Configs und der PI-Config auf R2 und rotiert die
#   Snapshots: das bisherige snapshot_now wird snapshot_prev, ein neues
#   snapshot_now wird eingefroren. Damit zeigt das Delta-Briefing echte
#   vergangene Zeit statt der gestellten Zwei-Wochen-Story. Register bleiben
#   unverändert (Entscheidung Robert: sie werden von Menschen gepflegt).
# =============================================================================

from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from portfolio.solution_config import (
    KIND_PORTFOLIO,
    SolutionConfig,
    load_solution_config,
    resolve_config_path,
    save_solution_config,
)
from transform_data.processor import process_issues
from transform_data.workflow import parse_workflow
from transform_data.writers import write_cfd, write_issue_times, write_transitions

from .continuation import ContinuationError, continue_generation, read_meta


class ScenarioContinuationError(ValueError):
    """The data room cannot be continued as requested."""


def _art_short_name(member_name: str) -> str:
    """'ART Alpha-1' -> 'Alpha-1' (the raw file is named after the profile)."""
    return member_name.removeprefix("ART ").strip()


def _raw_file(out: Path, member_name: str) -> Path:
    raw = out / "raw" / f"{_art_short_name(member_name)}_jira.json"
    if not raw.is_file():
        raise ScenarioContinuationError(f"raw extract missing for '{member_name}': {raw}")
    return raw


def _pi_config(path: Path, start: date, end: date) -> None:
    """Rewrite the quarter intervals the way build_portfolio_scenario does."""
    quarters = []
    q_start, n = start, 1
    while q_start < end:
        q_end = min(q_start + timedelta(days=90), end)
        quarters.append({"name": f"PI {n}", "from": q_start.isoformat(),
                         "to": q_end.isoformat()})
        q_start = q_end + timedelta(days=1)
        n += 1
    path.write_text(json.dumps({"mode": "date", "intervals": quarters}, indent=2),
                    encoding="utf-8")


def _continue_art(out: Path, solution: SolutionConfig, member, to_date: date,
                  old_reference: date, log: Callable[[str], None]) -> int:
    """Continue one ART's raw extract and rewrite its transform_data outputs."""
    raw = _raw_file(out, member.name)
    data = json.loads(raw.read_text(encoding="utf-8"))
    meta = read_meta(data)
    if meta is None:
        raise ScenarioContinuationError(
            f"{raw.name} carries no generator record - built before 0.39.0? "
            f"Rebuild the scenario once, then continue it.")
    workflow = parse_workflow(resolve_config_path(solution.base_dir, member.workflow))
    old_art_to = date.fromisoformat(meta["to_date"])
    stale_days = max(0, (old_reference - old_art_to).days)     # Beta-3 stays stale
    art_to = to_date - timedelta(days=stale_days)
    try:
        result = continue_generation(data, workflow, art_to)
    except ContinuationError as exc:
        raise ScenarioContinuationError(f"{raw.name}: {exc}") from exc
    raw.write_text(json.dumps(result, indent=2), encoding="utf-8")

    reference_dt = datetime.combine(art_to + timedelta(days=1), datetime.min.time(), tzinfo=UTC)
    records, unmapped = process_issues(raw, workflow, reference_dt=reference_dt)
    if unmapped:
        log(f"  WARNING [{member.name}]: unmapped statuses {sorted(unmapped)}")
    write_issue_times(records, workflow,
                      resolve_config_path(solution.base_dir, member.issue_times))
    if member.transitions:
        write_transitions(records, resolve_config_path(solution.base_dir, member.transitions))
    if member.cfd:
        write_cfd(records, workflow, resolve_config_path(solution.base_dir, member.cfd),
                  reference_dt=reference_dt)
    before = len(data.get("issues", []))
    log(f"  {_art_short_name(member.name)}: {before} -> {len(records)} issues"
        f"{' (Datenstand -' + str(stale_days) + 'd bleibt)' if stale_days else ''}")
    return len(records) - before


def _append_stand(out: Path, snapshot_now: Path, to_date: date,
                  log: Callable[[str], None]) -> None:
    """
    Series of stands (Beta 1b): if the data room carries ``stands.json``,
    the new now becomes stand N+1 and the Delta-Briefing N -> N+1 is
    rendered. Rooms built before the series (no index) are left as they are.
    """
    snapshots_dir = out / "snapshots"
    index_path = snapshots_dir / "stands.json"
    if not index_path.is_file():
        return
    from .scenario import write_stand_delta, write_stands_index

    index = json.loads(index_path.read_text(encoding="utf-8"))
    entries = [(int(s["index"]), date.fromisoformat(s["as_of"]), str(s["file"]))
               for s in index.get("stands", [])]
    if not entries:
        return
    k = entries[-1][0] + 1
    name = f"snapshot_{k:02d}_{to_date.isoformat()}.json"
    shutil.copyfile(snapshot_now, snapshots_dir / name)
    entries.append((k, to_date, name))
    write_stands_index(snapshots_dir, entries)
    write_stand_delta(snapshots_dir, out / "deltas", k - 1)
    log(f"  Stand {k:02d} ({to_date}) an die Reihe angehängt, Delta {k - 1:02d}-{k:02d} gerendert")


def continue_portfolio_scenario(
    folder: Path,
    to_date: date,
    log: Callable[[str], None] = print,
) -> dict[str, Path]:
    """
    Continue the demo data room in place to the new reference date ``to_date``.

    Returns the key paths (portfolio config, snapshots, readme).

    Raises:
        ScenarioContinuationError: no portfolio.json, to_date not after the
            current reference, a raw extract missing or without record.
    """
    out = Path(folder)
    portfolio_path = out / "portfolio.json"
    if not portfolio_path.is_file():
        raise ScenarioContinuationError(f"no portfolio.json in {out}")
    portfolio = load_solution_config(portfolio_path)
    if portfolio.kind != KIND_PORTFOLIO or portfolio.to_date is None or portfolio.from_date is None:
        raise ScenarioContinuationError("portfolio.json is not a scenario portfolio with a data window")
    old_reference = portfolio.to_date
    if to_date <= old_reference:
        raise ScenarioContinuationError(
            f"to_date {to_date} must lie after the current reference {old_reference}.")
    window_days = (old_reference - portfolio.from_date).days
    new_from = to_date - timedelta(days=window_days)
    log(f"Szenario fortschreiben: {old_reference} -> {to_date} ({(to_date - old_reference).days} Tage)")

    added = 0
    for sol_member in portfolio.members:
        sol_path = resolve_config_path(portfolio.base_dir, sol_member.template)
        solution = load_solution_config(sol_path)
        for art in solution.members:
            added += _continue_art(out, solution, art, to_date, old_reference, log)
        solution.from_date, solution.to_date = new_from, to_date
        save_solution_config(sol_path, solution)
    portfolio.from_date, portfolio.to_date = new_from, to_date
    save_solution_config(portfolio_path, portfolio)

    pi_cfg = out / "pi_config.json"
    if pi_cfg.is_file():
        _pi_config(pi_cfg, new_from, to_date)

    snapshot_prev = out / "snapshots" / "snapshot_prev.json"
    snapshot_now = out / "snapshots" / "snapshot_now.json"
    if snapshot_now.is_file():
        from portfolio.snapshot import build_snapshot, save_snapshot

        shutil.copyfile(snapshot_now, snapshot_prev)
        save_snapshot(snapshot_now, build_snapshot(
            load_solution_config(portfolio_path), as_of=to_date, log=lambda m: None))
        log(f"  Snapshots rotiert: now ({old_reference}) -> prev, neues now ({to_date})")
        _append_stand(out, snapshot_now, to_date, log)

    readme = out / "README.md"
    if readme.is_file():
        with readme.open("a", encoding="utf-8") as f:
            f.write(f"\n\n_Fortgeschrieben am {date.today().isoformat()}: Referenzdatum "
                    f"{old_reference.isoformat()} → {to_date.isoformat()}, {added} neue Vorgänge; "
                    f"snapshot_prev = Stand {old_reference.isoformat()}, snapshot_now = Stand "
                    f"{to_date.isoformat()}. Register unverändert._\n")
    log(f"Fortschreibung komplett: {out} (+{added} Vorgänge)")
    return {"portfolio": portfolio_path, "snapshot_prev": snapshot_prev,
            "snapshot_now": snapshot_now, "readme": readme}
