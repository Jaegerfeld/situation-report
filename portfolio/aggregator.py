# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       22.06.2026
# Geändert:       04.09.2026
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

import dataclasses
import json
from collections.abc import Callable
from datetime import date
from pathlib import Path

from build_reports.export import _build_combined_html, export_pdf
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
    PROCESS_FLOW,
    PROCESS_FLOW_TIME,
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
from sources.base import DoraRecord, QualityRecord, SloRecord

from .capability_config import Capability, load_capabilities
from .decision_config import LogEntry, load_decisions
from .dependency_config import Dependency, load_dependencies
from .dora_config import load_delivery
from .flow_problems_config import FlowProblem, load_flow_problems
from .nfr_config import Nfr, RunwayItem, load_nfr
from .risks_config import Risk, load_risks
from .slo_config import load_slo
from .solution_config import (
    KIND_PORTFOLIO,
    KIND_SOLUTION,
    MODE_COMPARISON,
    MODE_POOLED,
    Member,
    SolutionConfig,
    StageMap,
    load_solution_config,
    resolve_config_path,
)
from .summary import (
    SourceQuality,
    assess_quality,
    capability_figure,
    compute_summary,
    decisions_figure,
    dependency_figure,
    dora_figure,
    flow_problems_figure,
    nfr_figure,
    quality_figure,
    render_capabilities_html,
    render_decisions_html,
    render_dependencies_html,
    render_dora_html,
    render_flow_problems_html,
    render_nfr_html,
    render_quality_html,
    render_roam_html,
    render_slo_html,
    render_summary_html,
    render_themes_html,
    roam_figure,
    slo_figure,
    summary_figure,
    themes_figure,
)
from .themes_config import Epic, StrategicTheme, load_themes

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

#: Default metrics for the COMPARISON mode WITH ART depth. On top of the
#: comparison set these add the two workflow-bound „ART & Teams" analyses:
#: Process Flow needs each ART's own transitions and stages, which pooling
#: discards — they are only meaningful on a single ART and would silently
#: produce nothing on a pooled solution or portfolio unit.
DEFAULT_ART_METRICS = DEFAULT_COMPARISON_METRICS + [PROCESS_FLOW,
                                                    PROCESS_FLOW_TIME]

# Backwards-compatible alias (Phase-1 name).
DEFAULT_METRICS = DEFAULT_POOLED_METRICS


def _absolutize_member(member: Member, base: Path | None) -> Member:
    """
    Resolve a member's path fields against its owning config's folder.

    Applied once when members are gathered for loading, so everything
    downstream works with plain paths; the config object itself keeps the
    stated (possibly relative) strings — serialisation stays portable.
    """
    if base is None:
        return member
    updates = {
        key: str(resolve_config_path(base, value))
        for key in ("template", "issue_times", "cfd", "workflow",
                    "transitions")
        if (value := getattr(member, key).strip())
    }
    return dataclasses.replace(member, **updates) if updates else member


def _resolve_member_paths(member: Member) -> dict[str, Path | None]:
    """
    Resolve a member's data file paths.

    A direct ``issue_times`` on the member takes precedence; otherwise the
    member's project template is read and its build_reports section supplies
    the paths (relative template entries resolve against the template's own
    folder — the Datenraum rule).

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
        template_path = Path(member.template)
        section = get_section(load_template(template_path), MODULE_BUILD_REPORTS)

        def _t(value: str) -> Path | None:
            value = (value or "").strip()
            if not value:
                return None
            return resolve_config_path(template_path.resolve().parent, value)

        issue_times = _t(str(section.get("issue_times", "")))
        cfd = _t(str(section.get("cfd", "")))
        workflow = _t(str(section.get("workflow", "")))
        transitions = _t(str(section.get("transitions", "")))
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
        return [_absolutize_member(m, config.base_dir)
                for m in config.members]

    visited = _visited if _visited is not None else set()
    arts: list[Member] = []
    for member in config.members:
        template = resolve_config_path(config.base_dir, member.template)
        resolved = str(template.resolve())
        if resolved in visited:
            continue
        visited.add(resolved)
        sub = load_solution_config(template)
        arts.extend(_iter_art_members(sub, visited))
    return arts


def _load_member(member: Member) -> ReportData:
    """
    Load one member ART's ReportData and label it with the member's name.

    The source_prefix is overridden with the member's friendly name so figure
    titles show the ART name rather than the file-derived project key.
    """
    paths = _resolve_member_paths(member)
    issue_times = paths["issue_times"]
    assert issue_times is not None  # guaranteed by _resolve_member_paths
    data = load_report_data(
        issue_times, paths["cfd"], paths["workflow"], paths["transitions"]
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


def _pool_cfd(
    member_datas: list[ReportData],
    stage_map: StageMap | None = None,
    log: Callable[[str], None] = print,
) -> list[CfdRecord]:
    """
    Merge per-ART CFDs into one canonical CFD.

    Without a StageMap, each ART stage is classified into To Do / In Progress /
    Done (build_reports.classify_stages) — collapsing to the three groups is
    what makes a CFD poolable across ARTs with different workflows. With a
    StageMap (A4), the solution config defines its own canonical stages and the
    exact source-stage assignment; source stages the map does not mention fall
    into the map's first_stage and are warned about once per name.

    Args:
        member_datas: Per-ART ReportData (each with its own stages and CFD).
        stage_map:    Optional custom canonical mapping from the solution config.
        log:          Progress callback (unmapped-stage warnings).

    Returns:
        CFD records keyed by the canonical stages, ordered by day; empty when
        no member supplied CFD data.
    """
    canon = list(stage_map.stages.keys()) if stage_map else _CANON_STAGES
    custom_lookup = stage_map.lookup() if stage_map else None
    warned: set[str] = set()

    by_day: dict = {}
    for data in member_datas:
        if not data.cfd or not data.stages:
            continue
        if stage_map is None:
            # Mirror the CFD metric's own boundary fallback: when the workflow
            # markers are absent, treat the first/last stage as the In/Out
            # boundary so the Done group is still populated.
            first = data.first_stage if data.first_stage in data.stages else data.stages[0]
            closed = data.closed_stage if data.closed_stage in data.stages else data.stages[-1]
            mapping = classify_stages(data.stages, first, closed)
            fallback = GROUP_IN_PROGRESS
        else:
            mapping = custom_lookup or {}
            fallback = stage_map.first_stage
        for rec in data.cfd:
            bucket = by_day.setdefault(rec.day, {g: 0 for g in canon})
            for stage, count in rec.stage_counts.items():
                group = mapping.get(stage)
                if group is None:
                    group = fallback
                    if custom_lookup is not None and stage not in warned:
                        warned.add(stage)
                        log(f"  WARNING: stage '{stage}' is not in the stage_map — "
                            f"counted as '{fallback}'.")
                bucket[group] += count
    return [CfdRecord(day=day, stage_counts=dict(by_day[day]))
            for day in sorted(by_day)]


def build_pooled_report_data(
    config: SolutionConfig,
    log: Callable[[str], None] = print,
    quality_sink: list[SourceQuality] | None = None,
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
        config:       Validated solution or portfolio configuration.
        log:          Progress callback.
        quality_sink: Optional list that receives one SourceQuality per member
                      ART (A1 confidence flag). The member data is already
                      loaded here, so assessing it in-place avoids a second
                      pass over the input files.

    Returns:
        A single pooled ReportData spanning all contained ARTs.
    """
    art_members = _iter_art_members(config)
    member_datas = [_load_member(m) for m in art_members]

    pooled_issues = []
    for member, data in zip(art_members, member_datas):
        log(f"  {member.name}: {len(data.issues)} issues, "
            f"{len(data.stages)} stages, {len(data.cfd)} CFD day(s)")
        if quality_sink is not None:
            quality_sink.append(assess_quality(data, member.name))
        pooled_issues.extend(data.issues)

    cfd_records = _pool_cfd(member_datas, stage_map=config.stage_map, log=log)
    log(f"Pooled total: {len(pooled_issues)} issues from {len(art_members)} ART(s); "
        f"{len(cfd_records)} canonical CFD day(s)")
    # Stages are the canonical groups so the pooled CFD renders across
    # heterogeneous workflows — the fixed three (To Do / In Progress / Done) or,
    # with a config stage_map (A4), its custom canonical stages. The issue-based
    # metrics (Flow Velocity/Time/Distribution) do not depend on this stage list.
    if config.stage_map is not None:
        stages = list(config.stage_map.stages.keys())
        first_stage = config.stage_map.first_stage
        closed_stage = config.stage_map.closed_stage
    else:
        stages = list(_CANON_STAGES)
        first_stage = GROUP_IN_PROGRESS
        closed_stage = GROUP_DONE
    return ReportData(
        issues=pooled_issues,
        cfd=cfd_records,
        transitions=[],
        stages=stages,
        source_prefix=config.name,
        first_stage=first_stage,
        closed_stage=closed_stage,
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
        data = _load_member(_absolutize_member(member, config.base_dir))
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
        sub = load_solution_config(
            resolve_config_path(config.base_dir, member.template))
        data = build_pooled_report_data(sub, log=log)  # source_prefix = solution name
        data = apply_filters(data, cfg)
        log(f"  Solution '{sub.name}': {len(data.issues)} issues after filter")
        units.append(data)
    return units


#: Separator between the owning solution and the ART in a drill-down label.
ART_LABEL_SEP = " · "


def _iter_labelled_arts(
    config: SolutionConfig,
    _prefix: str = "",
    _visited: set[str] | None = None,
) -> list[tuple[Member, str]]:
    """
    Flatten a configuration to its ARTs, each with a label unique across solutions.

    Same recursion as _iter_art_members, but every ART additionally carries the
    chain of solutions it sits in ("Solution Alpha · ART Alpha-1"). Two member
    solutions may well name an ART identically ("ART Team A"); without the
    prefix their rows would silently merge in the summary and collide as
    figure labels.

    Args:
        config:   The solution or portfolio configuration.
        _prefix:  Internal label prefix accumulated while descending.
        _visited: Internal set of resolved template paths already expanded.

    Returns:
        Flat list of (ART member, display label) pairs.
    """
    if config.kind == KIND_SOLUTION:
        return [(_absolutize_member(m, config.base_dir), f"{_prefix}{m.name}")
                for m in config.members]

    visited = _visited if _visited is not None else set()
    out: list[tuple[Member, str]] = []
    for member in config.members:
        template = resolve_config_path(config.base_dir, member.template)
        resolved = str(template.resolve())
        if resolved in visited:
            continue
        visited.add(resolved)
        sub = load_solution_config(template)
        out.extend(_iter_labelled_arts(
            sub, f"{_prefix}{sub.name}{ART_LABEL_SEP}", visited))
    return out


def load_art_units(
    config: SolutionConfig,
    log: Callable[[str], None] = print,
) -> list[ReportData]:
    """
    Load one ReportData per ART — the drill-down granularity (ART depth).

    Unlike load_comparison_units this always descends to the ARTs themselves,
    also for a portfolio, where the default comparison unit is the member
    solution. Each ART keeps its own transitions and stages, which is what the
    workflow-bound „ART & Teams" analyses (Process Flow) need — pooling
    discards them.

    Args:
        config: Validated solution or portfolio configuration.
        log:    Progress callback.

    Returns:
        One filtered ReportData per ART, labelled uniquely across solutions.
    """
    cfg = FilterConfig(from_date=config.from_date, to_date=config.to_date)
    units: list[ReportData] = []
    for member, label in _iter_labelled_arts(config):
        data = _load_member(member)
        data.source_prefix = label
        data = apply_filters(data, cfg)
        log(f"  {label}: {len(data.issues)} issues after filter")
        if not data.transitions:
            log(f"  NOTE [{label}]: no transition data — the Process-Flow "
                f"analyses stay empty for this ART.")
        units.append(data)
    return units


def _art_detail_units(
    config: SolutionConfig,
    unit_labels: list[str],
    log: Callable[[str], None] = print,
) -> list[ReportData]:
    """
    The ARTs to add as a drill-down — or [] when they are already on display.

    A solution in comparison mode (and a solution pre-read) enumerates exactly
    these ARTs anyway; repeating them would be noise. The labels are derived
    from the configuration alone, so the redundant case costs no file access.

    Args:
        config:      The solution or portfolio configuration.
        unit_labels: Labels of the units the main table already shows.
        log:         Progress callback.

    Returns:
        One ReportData per ART, or [] if the drill-down adds nothing.
    """
    labels = [label for _member, label in _iter_labelled_arts(config)]
    if not labels or labels == list(unit_labels):
        return []
    return load_art_units(config, log=log)


def _art_detail_html(
    config: SolutionConfig,
    unit_labels: list[str],
    target_ct: int,
    log: Callable[[str], None] = print,
) -> str:
    """
    Build the optional ART drill-down block (summary + quality table per ART).

    Rendering the ARTs as their own table rather than as extra rows keeps the A3
    outlier highlighting peer-to-peer: an aggregate row is not a peer of an ART
    and would distort the column median it is compared against.

    Args:
        config:      The solution or portfolio configuration.
        unit_labels: Labels of the units the main table already shows.
        target_ct:   Target cycle time (column header + target share).
        log:         Progress callback.

    Returns:
        An HTML fragment, or "" if there is nothing to add.
    """
    art_units = _art_detail_units(config, unit_labels, log=log)
    if not art_units:
        return ""
    summary = render_summary_html(
        [compute_summary(u, u.source_prefix, target_ct) for u in art_units],
        title="ART Detail — Management Summary per ART", target_ct=target_ct)
    quality = render_quality_html(
        [assess_quality(u, u.source_prefix) for u in art_units],
        title="ART Detail — Data Quality per ART")
    return summary + quality


def _default_metrics(
    config: SolutionConfig, mode: str, art_depth: bool = False
) -> list[str]:
    """Pick the default metric set for a config + mode (see the DEFAULT_* notes)."""
    if mode != MODE_COMPARISON:
        return DEFAULT_POOLED_METRICS
    if art_depth:
        return DEFAULT_ART_METRICS
    if config.kind != KIND_PORTFOLIO:
        return DEFAULT_COMPARISON_METRICS
    return DEFAULT_POOLED_METRICS


def _collect_report(
    config: SolutionConfig,
    mode: str,
    metrics: list[str] | None,
    terminology: str,
    ct_method: str,
    target_ct: int,
    pi_config: Path | None,
    log: Callable[[str], None],
    art_depth: bool = False,
) -> tuple[list, dict[int, str], list[ReportData], list[SourceQuality]]:
    """
    Shared report core: resolve the report units, run the metrics, collect figures.

    Pooled mode has a single unit (the pooled solution/portfolio); comparison mode
    has one unit per ART (solution) or per member solution (portfolio). With
    art_depth the comparison units are always the individual ARTs, so a portfolio
    is compared ART by ART instead of solution by solution. The figures are
    grouped by metric (one section heading per metric), and each figure is
    labelled with its unit's name via source_prefix.

    Returns:
        (figures, section_breaks, units, qualities) — units carry the labelled
        ReportData used for both the figures and the management summary;
        qualities carry one SourceQuality per source (pooled: per member ART,
        comparison: per unit) for the A1 confidence table.
    """
    qualities: list[SourceQuality]
    if mode == MODE_COMPARISON:
        units = (load_art_units(config, log=log) if art_depth
                 else load_comparison_units(config, log=log))
        qualities = [assess_quality(u, u.source_prefix) for u in units]
    else:
        qualities = []
        data = build_pooled_report_data(config, log=log, quality_sink=qualities)
        data = apply_filters(
            data, FilterConfig(from_date=config.from_date, to_date=config.to_date))
        log(f"After date filter: {len(data.issues)} issues")
        units = [data]

    metric_ids = metrics or _default_metrics(config, mode, art_depth)
    plugins = _make_plugins(metric_ids, ct_method, target_ct, pi_config, log)

    all_figures: list = []
    section_breaks: dict[int, str] = {}
    for plugin in plugins:
        log(f"Computing {plugin.metric_id} ({mode}) ...")
        group_started = False
        for unit in units:
            result = plugin.run(unit, terminology)
            for w in result.warnings:
                log(f"  WARNING [{unit.source_prefix}]: {w}")
            figures = plugin.run_render(result, terminology)
            if figures and not group_started:
                section_breaks[len(all_figures)] = term(plugin.metric_id, terminology)
                group_started = True
            all_figures.extend(figures)

    return all_figures, section_breaks, units, qualities


def _governance_sources(
    config: SolutionConfig,
    log: Callable[[str], None] = print,
) -> list[tuple[str, SolutionConfig]]:
    """
    Resolve the configs whose governance files (risks, NFR) feed the report.

    A solution contributes itself; a portfolio contributes each member
    solution's loaded config (an unreadable member is logged and skipped —
    governance data must never break the flow report).

    Args:
        config: The solution or portfolio configuration.
        log:    Progress/warning callback.

    Returns:
        (solution name, SolutionConfig) pairs.
    """
    if config.kind != KIND_PORTFOLIO:
        return [(config.name, config)]
    sources: list[tuple[str, SolutionConfig]] = []
    for member in config.members:
        try:
            sub = load_solution_config(
                resolve_config_path(config.base_dir, member.template))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            log(f"  WARNING [{member.name}]: solution config not readable "
                f"for governance data ({exc})")
            continue
        sources.append((sub.name, sub))
    return sources


def _collect_capabilities(
    config: SolutionConfig,
    log: Callable[[str], None] = print,
) -> list[tuple[str, Capability]]:
    """
    Collect capabilities for the report (B1).

    Same resolution rules as the other governance registers: a solution loads
    its own ``capabilities`` file, a portfolio aggregates its member
    solutions' maps; broken or missing files are logged and skipped. An ART
    name in a capability that is not among the solution's members is logged
    as a warning (the map and the member list drifted apart) but kept.

    Args:
        config: The solution or portfolio configuration.
        log:    Progress/warning callback.

    Returns:
        (source label, Capability) pairs; empty when no map is referenced.
    """
    entries: list[tuple[str, Capability]] = []
    for label, sub in _governance_sources(config, log):
        if not sub.capabilities:
            continue
        try:
            cap_map = load_capabilities(resolve_config_path(sub.base_dir, sub.capabilities, log))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            log(f"  WARNING [{label}]: capabilities file skipped ({exc})")
            continue
        known = {m.name for m in sub.members}
        for cap in cap_map.capabilities:
            unknown = [a for a in cap.arts if a not in known]
            if unknown:
                log(f"  WARNING [{label}]: capability '{cap.cap_id}' maps "
                    f"unknown ARTs {unknown}")
            entries.append((label, cap))
    return entries


def _collect_decisions(
    config: SolutionConfig,
    log: Callable[[str], None] = print,
) -> list[tuple[str, LogEntry]]:
    """
    Collect decision/assumption-log entries for the report (B4).

    Same resolution rules as the other governance registers: a solution loads
    its own ``decisions`` file, a portfolio aggregates its member solutions'
    logs; broken or missing files are logged and skipped.

    Args:
        config: The solution or portfolio configuration.
        log:    Progress/warning callback.

    Returns:
        (source label, LogEntry) pairs; empty when no log is referenced.
    """
    entries: list[tuple[str, LogEntry]] = []
    for label, sub in _governance_sources(config, log):
        if not sub.decisions:
            continue
        try:
            decision_log = load_decisions(resolve_config_path(sub.base_dir, sub.decisions, log))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            log(f"  WARNING [{label}]: decisions file skipped ({exc})")
            continue
        entries.extend((label, entry) for entry in decision_log.entries)
    return entries


def _collect_flow_problems(
    config: SolutionConfig,
    log: Callable[[str], None] = print,
) -> list[tuple[str, FlowProblem]]:
    """
    Collect flow problems for the report (B6) — same rules as the other
    governance registers; broken or missing files are logged and skipped.
    """
    entries: list[tuple[str, FlowProblem]] = []
    for label, sub in _governance_sources(config, log):
        if not sub.flow_problems:
            continue
        try:
            register = load_flow_problems(resolve_config_path(sub.base_dir, sub.flow_problems, log))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            log(f"  WARNING [{label}]: flow-problems file skipped ({exc})")
            continue
        entries.extend((label, problem) for problem in register.problems)
    return entries


def _collect_themes(
    config: SolutionConfig,
    log: Callable[[str], None] = print,
) -> tuple[list[tuple[str, StrategicTheme]], list[tuple[str, Epic]]]:
    """
    Collect strategic themes and roadmap epics for the report (B7) —
    same rules as the other governance registers; broken or missing files
    are logged and skipped.
    """
    themes: list[tuple[str, StrategicTheme]] = []
    epics: list[tuple[str, Epic]] = []
    for label, sub in _governance_sources(config, log):
        if not sub.themes:
            continue
        try:
            register = load_themes(resolve_config_path(sub.base_dir, sub.themes, log))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            log(f"  WARNING [{label}]: themes file skipped ({exc})")
            continue
        themes.extend((label, theme) for theme in register.themes)
        epics.extend((label, epic) for epic in register.epics)
    return themes, epics


def _collect_slo(
    config: SolutionConfig,
    log: Callable[[str], None] = print,
) -> list[tuple[str, SloRecord]]:
    """
    Collect SLO records for the report (C1) — same rules as the other
    governance registers; broken or missing files are logged and skipped.
    """
    entries: list[tuple[str, SloRecord]] = []
    for label, sub in _governance_sources(config, log):
        if not sub.slo:
            continue
        try:
            register = load_slo(resolve_config_path(sub.base_dir, sub.slo, log))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            log(f"  WARNING [{label}]: slo file skipped ({exc})")
            continue
        entries.extend((label, record) for record in register.records)
    return entries


def _collect_delivery(
    config: SolutionConfig,
    log: Callable[[str], None] = print,
) -> tuple[list[tuple[str, DoraRecord]], list[tuple[str, QualityRecord]]]:
    """
    Collect DORA and quality records for the report (C2) — same rules as
    the other governance registers; broken files are logged and skipped.
    """
    dora: list[tuple[str, DoraRecord]] = []
    quality: list[tuple[str, QualityRecord]] = []
    for label, sub in _governance_sources(config, log):
        if not sub.dora:
            continue
        try:
            register = load_delivery(resolve_config_path(sub.base_dir, sub.dora, log))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            log(f"  WARNING [{label}]: dora file skipped ({exc})")
            continue
        dora.extend((label, record) for record in register.dora)
        quality.extend((label, record) for record in register.quality)
    return dora, quality


def _collect_dependencies(
    config: SolutionConfig,
    log: Callable[[str], None] = print,
) -> list[tuple[str, Dependency]]:
    """
    Collect dependencies for the report (B5).

    Same resolution rules as the other governance registers: a solution loads
    its own ``dependencies`` file, a portfolio aggregates its member
    solutions' registers; broken or missing files are logged and skipped.
    The 'to' side is deliberately not validated against the member list —
    integration points may target other solutions, vendors, or external
    systems.

    Args:
        config: The solution or portfolio configuration.
        log:    Progress/warning callback.

    Returns:
        (source label, Dependency) pairs; empty when no register is referenced.
    """
    entries: list[tuple[str, Dependency]] = []
    for label, sub in _governance_sources(config, log):
        if not sub.dependencies:
            continue
        try:
            register = load_dependencies(resolve_config_path(sub.base_dir, sub.dependencies, log))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            log(f"  WARNING [{label}]: dependencies file skipped ({exc})")
            continue
        entries.extend((label, dep) for dep in register.dependencies)
    return entries


def _collect_risks(
    config: SolutionConfig,
    log: Callable[[str], None] = print,
) -> list[tuple[str, Risk]]:
    """
    Collect ROAM risks for the report (B3).

    For a solution, its own ``risks`` file is loaded (source label = solution
    name); a portfolio aggregates the registers of its member solutions. A
    missing or invalid risks file is logged as a warning and skipped.

    Args:
        config: The solution or portfolio configuration.
        log:    Progress/warning callback.

    Returns:
        (source label, Risk) pairs; empty when no register is referenced.
    """
    entries: list[tuple[str, Risk]] = []
    for label, sub in _governance_sources(config, log):
        if not sub.risks:
            continue
        try:
            register = load_risks(resolve_config_path(sub.base_dir, sub.risks, log))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            log(f"  WARNING [{label}]: risks file skipped ({exc})")
            continue
        entries.extend((label, risk) for risk in register.risks)
    return entries


def _collect_nfr(
    config: SolutionConfig,
    log: Callable[[str], None] = print,
) -> tuple[list[tuple[str, Nfr]], list[tuple[str, RunwayItem]]]:
    """
    Collect NFRs and runway elements for the report (B2).

    Same resolution rules as _collect_risks: a solution loads its own ``nfr``
    file, a portfolio aggregates its member solutions' registers; broken or
    missing files are logged and skipped.

    Args:
        config: The solution or portfolio configuration.
        log:    Progress/warning callback.

    Returns:
        ((source label, Nfr) pairs, (source label, RunwayItem) pairs).
    """
    nfrs: list[tuple[str, Nfr]] = []
    runway: list[tuple[str, RunwayItem]] = []
    for label, sub in _governance_sources(config, log):
        if not sub.nfr:
            continue
        try:
            register = load_nfr(resolve_config_path(sub.base_dir, sub.nfr, log))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            log(f"  WARNING [{label}]: NFR file skipped ({exc})")
            continue
        nfrs.extend((label, nfr) for nfr in register.nfrs)
        runway.extend((label, item) for item in register.runway)
    return nfrs, runway


def render_html(
    config: SolutionConfig,
    mode: str = MODE_POOLED,
    metrics: list[str] | None = None,
    terminology: str = SAFE,
    ct_method: str = CT_METHOD_A,
    target_ct: int = 90,
    pi_config: Path | None = None,
    log: Callable[[str], None] = print,
    art_depth: bool = False,
) -> str:
    """
    Render a solution/portfolio report as a single self-contained HTML document.

    The management summary table is injected at the top, followed by the metric
    figures grouped by metric. See _collect_report for the pooled/comparison
    semantics.

    art_depth drills down to the individual ARTs: in comparison mode the figures
    and tables are computed per ART (which is what makes the workflow-bound
    „ART & Teams" analyses possible at portfolio level at all); in pooled mode
    the pooled figures stay pooled — pooling is the point there — and the ARTs
    are added as their own summary and quality table.

    Returns:
        Complete HTML document, or "" if no figures were produced.
    """
    figures, section_breaks, units, qualities = _collect_report(
        config, mode, metrics, terminology, ct_method, target_ct, pi_config, log,
        art_depth=art_depth)
    if not figures:
        log("No figures produced — nothing to render.")
        return ""
    html = _build_combined_html(figures, section_breaks)
    summary = render_summary_html(
        [compute_summary(u, u.source_prefix, target_ct) for u in units],
        target_ct=target_ct)
    quality = render_quality_html(qualities)
    if art_depth:
        quality += _art_detail_html(
            config, [u.source_prefix for u in units], target_ct, log=log)
    caps = render_capabilities_html(_collect_capabilities(config, log=log))
    roam = render_roam_html(_collect_risks(config, log=log))
    nfr = render_nfr_html(*_collect_nfr(config, log=log))
    deps = render_dependencies_html(_collect_dependencies(config, log=log))
    decisions = render_decisions_html(_collect_decisions(config, log=log))
    flow = render_flow_problems_html(_collect_flow_problems(config, log=log))
    theme_entries, epic_entries = _collect_themes(config, log=log)
    themes = render_themes_html(theme_entries, epic_entries)
    slo = render_slo_html(_collect_slo(config, log=log))
    dora_entries, quality_entries = _collect_delivery(config, log=log)
    dora = render_dora_html(dora_entries, quality_entries)
    return html.replace(
        "<body>",
        "<body>" + summary + quality + caps + roam + nfr + deps + decisions
        + flow + themes + slo + dora, 1)


def render_pdf(
    config: SolutionConfig,
    output_path: Path,
    mode: str = MODE_POOLED,
    metrics: list[str] | None = None,
    terminology: str = SAFE,
    ct_method: str = CT_METHOD_A,
    target_ct: int = 90,
    pi_config: Path | None = None,
    log: Callable[[str], None] = print,
    art_depth: bool = False,
) -> bool:
    """
    Render a solution/portfolio report to a multi-page PDF (kaleido).

    The management summary is rendered as the first page (a table figure), then
    one page per metric figure. art_depth behaves as in render_html; in pooled
    mode it adds one ART summary page. Note that ART depth multiplies the page
    count (ARTs × metrics) — it is opt-in for exactly that reason.

    Returns:
        True if a PDF was written, False if there were no figures.
    """
    figures, _section_breaks, units, qualities = _collect_report(
        config, mode, metrics, terminology, ct_method, target_ct, pi_config, log,
        art_depth=art_depth)
    if not figures:
        log("No figures produced — nothing to export.")
        return False
    summaries = [compute_summary(u, u.source_prefix, target_ct) for u in units]
    pages = [summary_figure(summaries, target_ct=target_ct)] + figures
    extra = []
    if qualities:
        extra.append(quality_figure(qualities))
    if art_depth:
        art_units = _art_detail_units(
            config, [u.source_prefix for u in units], log=log)
        if art_units:
            extra.append(summary_figure(
                [compute_summary(u, u.source_prefix, target_ct)
                 for u in art_units],
                title="ART Detail — Management Summary per ART",
                target_ct=target_ct))
    cap_entries = _collect_capabilities(config, log=log)
    if cap_entries:
        extra.append(capability_figure(cap_entries))
    risk_entries = _collect_risks(config, log=log)
    if risk_entries:
        extra.append(roam_figure(risk_entries))
    nfrs, runway = _collect_nfr(config, log=log)
    if nfrs or runway:
        extra.append(nfr_figure(nfrs, runway))
    dep_entries = _collect_dependencies(config, log=log)
    if dep_entries:
        extra.append(dependency_figure(dep_entries))
    log_entries = _collect_decisions(config, log=log)
    if log_entries:
        extra.append(decisions_figure(log_entries))
    flow_entries = _collect_flow_problems(config, log=log)
    if flow_entries:
        extra.append(flow_problems_figure(flow_entries))
    theme_entries, epic_entries = _collect_themes(config, log=log)
    if theme_entries or epic_entries:
        extra.append(themes_figure(theme_entries, epic_entries))
    slo_entries = _collect_slo(config, log=log)
    if slo_entries:
        extra.append(slo_figure(slo_entries))
    dora_entries, quality_entries = _collect_delivery(config, log=log)
    if dora_entries or quality_entries:
        extra.append(dora_figure(dora_entries, quality_entries))
    pages[1:1] = extra
    export_pdf(pages, Path(output_path))
    log(f"PDF written to: {output_path}")
    return True


def render_pooled_html(
    config: SolutionConfig,
    metrics: list[str] | None = None,
    terminology: str = SAFE,
    ct_method: str = CT_METHOD_A,
    target_ct: int = 90,
    pi_config: Path | None = None,
    log: Callable[[str], None] = print,
    art_depth: bool = False,
) -> str:
    """Render the pooled report as HTML (thin wrapper over render_html)."""
    return render_html(config, MODE_POOLED, metrics, terminology,
                       ct_method, target_ct, pi_config, log, art_depth)


def render_comparison_html(
    config: SolutionConfig,
    metrics: list[str] | None = None,
    terminology: str = SAFE,
    ct_method: str = CT_METHOD_A,
    target_ct: int = 90,
    pi_config: Path | None = None,
    log: Callable[[str], None] = print,
    art_depth: bool = False,
) -> str:
    """Render the per-unit comparison report as HTML (thin wrapper over render_html)."""
    return render_html(config, MODE_COMPARISON, metrics, terminology,
                       ct_method, target_ct, pi_config, log, art_depth)


def render_conference_html(
    config: SolutionConfig,
    conference_date: date | None = None,
    log: Callable[[str], None] = print,
    art_depth: bool = False,
) -> str:
    """
    Render the Value-Stream-Conference pre-read ("Konferenzmappe", B6).

    A deliberately light, printable page bundling the conference inputs in
    their meeting order: current data (summary + source quality), the
    impediment backlog (flow problems, with ROAM risks and dependencies as
    the related governance views) and the business objectives proxy
    (capability map + SLOs). The integrated roadmap view joins with B7.
    No plotly figures — the pre-read is meant to be read, the full report
    to be explored.

    With art_depth, Input 1 additionally carries the drill-down to the
    individual ARTs — the granularity the ART teams themselves prepare for the
    conference. For a solution the pre-read is ART-level already, so the block
    stays out (see _art_detail_html).

    Args:
        config:          The solution or portfolio configuration.
        conference_date: Date shown in the header (default: today).
        log:             Progress callback.
        art_depth:       Add the per-ART drill-down to Input 1.

    Returns:
        A complete standalone HTML document.
    """
    conference_date = conference_date or date.today()
    qualities: list[SourceQuality] = []
    build_pooled_report_data(config, log=log, quality_sink=qualities)
    units = load_comparison_units(config, log=log)
    summary = render_summary_html(
        [compute_summary(u, u.source_prefix, 90) for u in units])
    quality = render_quality_html(qualities)
    if art_depth:
        quality += _art_detail_html(
            config, [u.source_prefix for u in units], 90, log=log)
    flow = render_flow_problems_html(_collect_flow_problems(config, log=log))
    roam = render_roam_html(_collect_risks(config, log=log))
    deps = render_dependencies_html(_collect_dependencies(config, log=log))
    caps = render_capabilities_html(_collect_capabilities(config, log=log))
    slo = render_slo_html(_collect_slo(config, log=log))
    theme_entries, epic_entries = _collect_themes(config, log=log)
    themes = render_themes_html(theme_entries, epic_entries)

    def block(label: str, *fragments: str) -> str:
        body = "".join(f for f in fragments if f)
        if not body:
            return ""
        return (f"<h1 style='font-size:1.25rem;margin-top:28px;"
                f"border-bottom:2px solid #2b5b84;padding-bottom:4px'>"
                f"{label}</h1>{body}")

    head = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>VSC Pre-Read — {config.name}</title>"
        "<style>body{font-family:'Segoe UI',Arial,sans-serif;margin:24px;"
        "color:#222;} p.meta{color:#555;}</style></head><body>"
        f"<h1 style='font-size:1.5rem'>Value-Stream Conference — Pre-Read</h1>"
        f"<p class='meta'>{config.name} · Konferenz "
        f"{conference_date.strftime('%d.%m.%Y')} · Stand "
        f"{date.today().strftime('%d.%m.%Y')} — Inputs in Sitzungsreihenfolge; "
        f"der vollständige interaktive Report bleibt die Detailquelle.</p>"
    )
    body = (
        block("Input 1 · Aktuelle Daten", summary, quality)
        + block("Input 2 · Impediment-Backlog & Governance",
                flow, roam, deps)
        + block("Input 3 · Business Objectives (Capability-Map & SLOs)",
                caps, slo)
        + block("Input 4 · Integrierte Roadmap & Strategic Themes", themes)
    )
    return head + body + "</body></html>"
