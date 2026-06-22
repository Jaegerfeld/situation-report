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
from build_reports.loader import ReportData, load_report_data
from build_reports.metrics import get_metric
from build_reports.metrics.base import MetricPlugin
from build_reports.metrics.flow_time import CT_METHOD_A, FlowTimeMetric
from build_reports.metrics.flow_velocity import FlowVelocityMetric
from build_reports.terminology import FLOW_TIME, FLOW_VELOCITY, SAFE, term

from project_template import MODULE_BUILD_REPORTS, get_section, load_template

from .solution_config import Member, SolutionConfig

#: Default metrics for both modes — both date-driven, so they pool/compare
#: cleanly regardless of differing ART workflows.
DEFAULT_METRICS = [FLOW_VELOCITY, FLOW_TIME]

# Backwards-compatible alias (Phase-1 name).
DEFAULT_POOLED_METRICS = DEFAULT_METRICS


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
        if isinstance(plugin, FlowVelocityMetric):
            plugin.pi_config_path = str(pi_config) if pi_config else ""
        plugins.append(plugin)
    return plugins


def build_pooled_report_data(
    config: SolutionConfig,
    log: Callable[[str], None] = print,
) -> ReportData:
    """
    Load every member ART and pool their issues into one ReportData.

    Issues are concatenated at the record level (each IssueRecord already carries
    its own ``project``/``group``). Stage lists are unioned in first-seen order;
    the first/closed-stage markers are taken from the first member that defines
    them. The pooled ReportData's source_prefix is the solution name, so figure
    titles are labelled with the solution rather than a single project key.

    Args:
        config: Validated solution configuration.
        log:    Progress callback.

    Returns:
        A single pooled ReportData spanning all members.
    """
    pooled_issues = []
    pooled_stages: list[str] = []
    first_stage: str | None = None
    closed_stage: str | None = None

    for member in config.members:
        data = _load_member(member)
        log(f"  {member.name}: {len(data.issues)} issues, {len(data.stages)} stages")
        pooled_issues.extend(data.issues)
        for stage in data.stages:
            if stage not in pooled_stages:
                pooled_stages.append(stage)
        if first_stage is None:
            first_stage = data.first_stage
        if closed_stage is None:
            closed_stage = data.closed_stage

    log(f"Pooled total: {len(pooled_issues)} issues from {len(config.members)} ART(s)")
    return ReportData(
        issues=pooled_issues,
        cfd=[],
        transitions=[],
        stages=pooled_stages,
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
        data = _load_member(member)
        data = apply_filters(data, cfg)
        log(f"  {member.name}: {len(data.issues)} issues after filter")
        out.append(data)
    return out


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

    Args mirror render_comparison_html(); see DEFAULT_METRICS for the default set.

    Returns:
        Complete HTML document, or "" if no figures were produced.
    """
    metric_ids = metrics or DEFAULT_METRICS
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

    Args mirror render_pooled_html(); see DEFAULT_METRICS for the default set.

    Returns:
        Complete HTML document, or "" if no figures were produced.
    """
    metric_ids = metrics or DEFAULT_METRICS
    members_data = load_members(config, log=log)
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
