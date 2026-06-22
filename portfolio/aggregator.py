# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       22.06.2026
# Geändert:       22.06.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Aggregations-Kern für Solution-/Portfolio-Reports. Zwei Modi:
#   - "pooled":     Issues aller ARTs auf Record-Ebene zu EINEM ReportData
#                   zusammenführen und die bestehenden build_reports-Metriken
#                   darüber laufen lassen (Solution als ein System). Es wird
#                   NICHT auf Statistik-Ebene gemittelt (Pooled-Median ≠
#                   Mittel-der-Mediane), sondern auf Roh-Issue-Ebene gepoolt.
#   - "comparison": Jeden ART getrennt berechnen und die Figures pro Metrik
#                   gruppiert nebeneinanderstellen ("welcher ART ist der
#                   Ausreißer?"). Jede Figure trägt den ART-Namen via source_prefix.
#   Phase 1/2 nutzen die datums-getriebenen Metriken (Flow Velocity, Flow Time),
#   die unabhängig vom Workflow der einzelnen ARTs korrekt poolen/vergleichen.
# =============================================================================

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from build_reports.export import _build_combined_html
from build_reports.filters import FilterConfig, apply_filters
from build_reports.loader import CfdRecord, ReportData, load_report_data
from build_reports.metrics import get_metric
from build_reports.metrics.base import MetricPlugin
from build_reports.metrics.flow_load import FlowLoadMetric
from build_reports.metrics.flow_time import CT_METHOD_A, FlowTimeMetric
from build_reports.metrics.flow_velocity import FlowVelocityMetric
from build_reports.stage_groups import (
    GROUP_DONE,
    GROUP_IN_PROGRESS,
    GROUP_TODO,
    classify_stages,
)
from build_reports.terminology import (
    FLOW_DISTRIBUTION,
    FLOW_LOAD,
    FLOW_TIME,
    FLOW_VELOCITY,
    SAFE,
    term,
)

#: CFD metric id (build_reports registers it under this string).
METRIC_CFD = "cfd"

#: Canonical, workflow-agnostic stages used to pool CFDs across ARTs with
#: differing workflows. Every ART stage maps into one of these three groups
#: via build_reports' classify_stages(), so daily entry counts stay additive.
_CANON_STAGES = [GROUP_TODO, GROUP_IN_PROGRESS, GROUP_DONE]

from project_template import MODULE_BUILD_REPORTS, get_section, load_template

from .solution_config import (
    KIND_PORTFOLIO,
    KIND_SOLUTION,
    Member,
    SolutionConfig,
    load_solution_config,
)

#: Default metrics for the POOLED mode. Flow Velocity, Flow Time and Flow
#: Distribution are record-based and pool cleanly regardless of differing ART
#: workflows. Flow Load is deliberately excluded here: it groups open issues by
#: their current stage, so pooling ARTs with different workflows would mix
#: incomparable stage columns. Request it explicitly only when all ARTs share a
#: workflow.
DEFAULT_POOLED_METRICS = [FLOW_VELOCITY, FLOW_TIME, FLOW_DISTRIBUTION, METRIC_CFD]

#: Default metrics for the COMPARISON mode. Each ART is computed separately, so
#: the stage-dependent Flow Load is safe to include here too.
DEFAULT_COMPARISON_METRICS = [FLOW_VELOCITY, FLOW_TIME, FLOW_DISTRIBUTION,
                              METRIC_CFD, FLOW_LOAD]

# Backwards-compatible alias (Phase-1 name).
DEFAULT_METRICS = DEFAULT_POOLED_METRICS


def _resolve_member_paths(member: Member) -> dict[str, Path | None]:
    """
    Resolve a member's data file paths.

    A direct ``issue_times`` on the member takes precedence; otherwise the
    member's project template is read and its build_reports section supplies
    the paths.

    Args:
        member: The solution member to resolve.

    Returns:
        Dict with keys ``issue_times`` (Path), and optional ``cfd`` / ``workflow``
        / ``transitions`` (Path or None).

    Raises:
        ValueError: If no IssueTimes path can be resolved.
    """
    def _p(value: str) -> Path | None:
        value = (value or "").strip()
        return Path(value) if value else None

    if member.issue_times:
        issue_times = _p(member.issue_times)
        cfd, workflow, transitions = _p(member.cfd), _p(member.workflow), _p(member.transitions)
    elif member.template:
        section = get_section(load_template(Path(member.template)), MODULE_BUILD_REPORTS)
        issue_times = _p(str(section.get("issue_times", "")))
        cfd = _p(str(section.get("cfd", "")))
        workflow = _p(str(section.get("workflow", "")))
        transitions = _p(str(section.get("transitions", "")))
    else:
        raise ValueError(f"Member '{member.name}' has neither template nor issue_times.")

    if issue_times is None:
        raise ValueError(f"Member '{member.name}' resolves to no IssueTimes path.")
    return {"issue_times": issue_times, "cfd": cfd,
            "workflow": workflow, "transitions": transitions}


def _iter_art_members(
    config: SolutionConfig,
    _visited: set[str] | None = None,
) -> list[Member]:
    """
    Flatten a configuration to the list of ART members it ultimately contains.

    For a solution this is simply its members. For a portfolio, each member
    references a solution template, which is loaded and recursively flattened to
    its ARTs (a portfolio of portfolios works too). Already-visited template
    paths are skipped so a self-referential config cannot loop forever.

    Args:
        config:   The solution or portfolio configuration.
        _visited: Internal set of resolved template paths already expanded.

    Returns:
        Flat list of ART-level Members.
    """
    if config.kind == KIND_SOLUTION:
        return list(config.members)

    visited = _visited if _visited is not None else set()
    arts: list[Member] = []
    for member in config.members:
        resolved = str(Path(member.template).resolve())
        if resolved in visited:
            continue
        visited.add(resolved)
        sub = load_solution_config(Path(member.template))
        arts.extend(_iter_art_members(sub, visited))
    return arts


def _load_member(member: Member) -> ReportData:
    """
    Load one member ART's ReportData and label it with the member's name.

    The source_prefix is overridden with the member's friendly name so figure
    titles show the ART name rather than the file-derived project key.
    """
    paths = _resolve_member_paths(member)
    data = load_report_data(
        paths["issue_times"], paths["cfd"], paths["workflow"], paths["transitions"]
    )
    data.source_prefix = member.name
    return data


def _make_plugins(
    metric_ids: list[str],
    ct_method: str,
    target_ct: int,
    pi_config: Path | None,
    log: Callable[[str], None] = print,
) -> list[MetricPlugin]:
    """Instantiate and configure the requested metric plugins (shared by both modes)."""
    plugins: list[MetricPlugin] = []
    for mid in metric_ids:
        try:
            plugin = get_metric(mid)
        except KeyError:
            log(f"WARNING: Unknown metric '{mid}' — skipped.")
            continue
        if isinstance(plugin, FlowTimeMetric):
            plugin.ct_method = ct_method
            plugin.target_ct = target_ct
        if isinstance(plugin, FlowLoadMetric):
            plugin.target_ct = target_ct
        if isinstance(plugin, FlowVelocityMetric):
            plugin.pi_config_path = str(pi_config) if pi_config else ""
        plugins.append(plugin)
    return plugins


def _pool_cfd(member_datas: list[ReportData]) -> list[CfdRecord]:
    """
    Merge per-ART CFDs into one canonical CFD via the shared stage mapping.

    Each ART stage is classified into To Do / In Progress / Done
    (build_reports.classify_stages), and the daily entry counts are summed per
    canonical group across all ARTs. ARTs without CFD data contribute nothing.
    Collapsing to the three groups is what makes a CFD poolable across ARTs with
    different workflows (their stage names are otherwise incomparable).

    Args:
        member_datas: Per-ART ReportData (each with its own stages and CFD).

    Returns:
        CFD records keyed by the three canonical stages, ordered by day; empty
        when no member supplied CFD data.
    """
    by_day: dict = {}
    for data in member_datas:
        if not data.cfd or not data.stages:
            continue
        # Mirror the CFD metric's own boundary fallback: when the workflow
        # markers are absent, treat the first/last stage as the In/Out boundary
        # so the Done group is still populated instead of collapsing to one group.
        first = data.first_stage if data.first_stage in data.stages else data.stages[0]
        closed = data.closed_stage if data.closed_stage in data.stages else data.stages[-1]
        mapping = classify_stages(data.stages, first, closed)
        for rec in data.cfd:
            bucket = by_day.setdefault(rec.day, {g: 0 for g in _CANON_STAGES})
            for stage, count in rec.stage_counts.items():
                group = mapping.get(stage, GROUP_IN_PROGRESS)
                bucket[group] += count
    return [CfdRecord(day=day, stage_counts=dict(by_day[day]))
            for day in sorted(by_day)]


def build_pooled_report_data(
    config: SolutionConfig,
    log: Callable[[str], None] = print,
) -> ReportData:
    """
    Load every member ART and pool their issues into one ReportData.

    Issues are concatenated at the record level (each IssueRecord already carries
    its own ``project``/``group``). The CFDs are merged via the shared stage
    mapping into the three canonical stages (To Do / In Progress / Done, see
    _pool_cfd), which also become the pooled ``stages`` — that is what lets the
    CFD render across ARTs with different workflows. The issue-based metrics
    (Flow Velocity/Time/Distribution) do not depend on this stage list. The
    pooled source_prefix is the config name, so figure titles are labelled with
    the solution/portfolio. For a portfolio the member solutions are flattened to
    all their ARTs first (see _iter_art_members), so a portfolio pools every ART.

    Args:
        config: Validated solution or portfolio configuration.
        log:    Progress callback.

    Returns:
        A single pooled ReportData spanning all contained ARTs.
    """
    art_members = _iter_art_members(config)
    member_datas = [_load_member(m) for m in art_members]

    pooled_issues = []
    for member, data in zip(art_members, member_datas):
        log(f"  {member.name}: {len(data.issues)} issues, "
            f"{len(data.stages)} stages, {len(data.cfd)} CFD day(s)")
        pooled_issues.extend(data.issues)

    cfd_records = _pool_cfd(member_datas)
    log(f"Pooled total: {len(pooled_issues)} issues from {len(art_members)} ART(s); "
        f"{len(cfd_records)} canonical CFD day(s)")
    # Stages are the canonical To Do / In Progress / Done groups so the pooled
    # CFD renders across heterogeneous workflows; the issue-based metrics
    # (Flow Velocity/Time/Distribution) do not depend on this stage list.
    return ReportData(
        issues=pooled_issues,
        cfd=cfd_records,
        transitions=[],
        stages=list(_CANON_STAGES),
        source_prefix=config.name,
        first_stage=GROUP_IN_PROGRESS,
        closed_stage=GROUP_DONE,
    )


def load_members(
    config: SolutionConfig,
    log: Callable[[str], None] = print,
) -> list[ReportData]:
    """
    Load each member ART separately (for the comparison mode).

    Every member's ReportData is loaded on its own, labelled with the member
    name, and passed through the solution-level date filter.

    Args:
        config: Validated solution configuration.
        log:    Progress callback.

    Returns:
        One filtered ReportData per member, in configuration order.
    """
    cfg = FilterConfig(from_date=config.from_date, to_date=config.to_date)
    out: list[ReportData] = []
    for member in config.members:
        data = _load_member(member)
        data = apply_filters(data, cfg)
        log(f"  {member.name}: {len(data.issues)} issues after filter")
        out.append(data)
    return out


def load_comparison_units(
    config: SolutionConfig,
    log: Callable[[str], None] = print,
) -> list[ReportData]:
    """
    Load the side-by-side comparison units for a config, labelled per unit.

    The comparison granularity matches the config level so the grouping stays
    meaningful ("which X is the outlier?"):
    - **solution** → one ReportData per **ART** (each labelled with the ART name).
    - **portfolio** → one ReportData per **member solution** (each solution's ARTs
      pooled, labelled with the solution name) — so solutions are compared, not
      flattened to individual ARTs.

    The config-level date filter is applied to every unit.

    Args:
        config: Validated solution or portfolio configuration.
        log:    Progress callback.

    Returns:
        One filtered, labelled ReportData per comparison unit.
    """
    if config.kind != KIND_PORTFOLIO:
        return load_members(config, log=log)

    cfg = FilterConfig(from_date=config.from_date, to_date=config.to_date)
    units: list[ReportData] = []
    for member in config.members:
        sub = load_solution_config(Path(member.template))
        data = build_pooled_report_data(sub, log=log)  # source_prefix = solution name
        data = apply_filters(data, cfg)
        log(f"  Solution '{sub.name}': {len(data.issues)} issues after filter")
        units.append(data)
    return units


def render_pooled_html(
    config: SolutionConfig,
    metrics: list[str] | None = None,
    terminology: str = SAFE,
    ct_method: str = CT_METHOD_A,
    target_ct: int = 90,
    pi_config: Path | None = None,
    log: Callable[[str], None] = print,
) -> str:
    """
    Build the pooled solution report and return it as a single HTML document.

    Loads and pools all members, applies the solution-level date filter, runs the
    requested (date-driven) metrics over the pooled data, and combines the figures
    into one self-contained HTML page.

    Args mirror render_comparison_html(); defaults to DEFAULT_POOLED_METRICS.

    Returns:
        Complete HTML document, or "" if no figures were produced.
    """
    metric_ids = metrics or DEFAULT_POOLED_METRICS
    data = build_pooled_report_data(config, log=log)

    cfg = FilterConfig(from_date=config.from_date, to_date=config.to_date)
    data = apply_filters(data, cfg)
    log(f"After solution date filter: {len(data.issues)} issues")

    plugins = _make_plugins(metric_ids, ct_method, target_ct, pi_config, log)

    all_figures: list = []
    section_breaks: dict[int, str] = {}
    for plugin in plugins:
        log(f"Computing {plugin.metric_id} (pooled) ...")
        result = plugin.run(data, terminology)
        for w in result.warnings:
            log(f"  WARNING: {w}")
        figures = plugin.run_render(result, terminology)
        if figures:
            section_breaks[len(all_figures)] = term(plugin.metric_id, terminology)
        all_figures.extend(figures)

    if not all_figures:
        log("No figures produced — nothing to render.")
        return ""
    return _build_combined_html(all_figures, section_breaks)


def render_comparison_html(
    config: SolutionConfig,
    metrics: list[str] | None = None,
    terminology: str = SAFE,
    ct_method: str = CT_METHOD_A,
    target_ct: int = 90,
    pi_config: Path | None = None,
    log: Callable[[str], None] = print,
) -> str:
    """
    Build the per-ART comparison report and return it as a single HTML document.

    Each member ART is computed separately and the figures are grouped **by
    metric** — under one metric heading the ARTs appear consecutively, each
    figure labelled with its ART name (via source_prefix). This puts the ARTs
    side by side so outliers stand out, without any pooling.

    Args mirror render_pooled_html(). For a *solution* the units are single ARTs,
    so the default set is DEFAULT_COMPARISON_METRICS (it can include the
    stage-dependent Flow Load). For a *portfolio* the units are themselves pooled
    solutions, so the default falls back to DEFAULT_POOLED_METRICS (Flow Load is
    excluded — pooling differing workflows within a solution would mix
    incomparable stage columns).

    Returns:
        Complete HTML document, or "" if no figures were produced.
    """
    if metrics:
        metric_ids = metrics
    elif config.kind == KIND_PORTFOLIO:
        metric_ids = DEFAULT_POOLED_METRICS
    else:
        metric_ids = DEFAULT_COMPARISON_METRICS
    members_data = load_comparison_units(config, log=log)
    plugins = _make_plugins(metric_ids, ct_method, target_ct, pi_config, log)

    all_figures: list = []
    section_breaks: dict[int, str] = {}
    for plugin in plugins:
        log(f"Computing {plugin.metric_id} (comparison) ...")
        group_started = False
        for data in members_data:
            result = plugin.run(data, terminology)
            for w in result.warnings:
                log(f"  WARNING [{data.source_prefix}]: {w}")
            figures = plugin.run_render(result, terminology)
            if figures and not group_started:
                section_breaks[len(all_figures)] = term(plugin.metric_id, terminology)
                group_started = True
            all_figures.extend(figures)

    if not all_figures:
        log("No figures produced — nothing to render.")
        return ""
    return _build_combined_html(all_figures, section_breaks)
