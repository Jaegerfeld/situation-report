# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       22.06.2026
# Geändert:       22.06.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Aggregations-Kern für Solution-/Portfolio-Reports (Phase 1, Modus "pooled").
#   Lädt die ReportData jedes referenzierten ARTs über build_reports.loader und
#   führt die Issues auf Record-Ebene zu EINEM gepoolten ReportData zusammen.
#   Anschließend laufen die bestehenden build_reports-Metriken unverändert über
#   den gepoolten Datensatz — es wird bewusst NICHT auf Statistik-Ebene gemittelt
#   (Pooled-Median ≠ Mittel-der-Mediane), sondern auf Roh-Issue-Ebene gepoolt.
#   Phase 1 nutzt nur datums-getriebene Metriken (Flow Velocity, Flow Time), die
#   unabhängig vom Workflow der einzelnen ARTs korrekt poolen.
# =============================================================================

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from pathlib import Path

from build_reports.export import _build_combined_html
from build_reports.filters import FilterConfig, apply_filters
from build_reports.loader import ReportData, load_report_data
from build_reports.metrics import get_metric
from build_reports.metrics.flow_time import CT_METHOD_A, FlowTimeMetric
from build_reports.metrics.flow_velocity import FlowVelocityMetric
from build_reports.terminology import FLOW_TIME, FLOW_VELOCITY, SAFE, term

from project_template import MODULE_BUILD_REPORTS, get_section, load_template

from .solution_config import Member, SolutionConfig

#: Phase-1 default metrics for the pooled report — both date-driven, so they
#: pool cleanly regardless of differing ART workflows.
DEFAULT_POOLED_METRICS = [FLOW_VELOCITY, FLOW_TIME]


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
        paths = _resolve_member_paths(member)
        data = load_report_data(
            paths["issue_times"], paths["cfd"], paths["workflow"], paths["transitions"]
        )
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

    Args:
        config:      Validated solution configuration.
        metrics:     Metric IDs to run. None = DEFAULT_POOLED_METRICS.
        terminology: SAFE or GLOBAL display mode.
        ct_method:   Cycle-time method for Flow Time (A=date diff, B=stage minutes).
        target_ct:   Target cycle time in days for the Flow Time header.
        pi_config:   Optional PI interval JSON for Flow Velocity.
        log:         Progress callback.

    Returns:
        Complete HTML document, or "" if no figures were produced.
    """
    metric_ids = metrics or DEFAULT_POOLED_METRICS
    data = build_pooled_report_data(config, log=log)

    cfg = FilterConfig(from_date=config.from_date, to_date=config.to_date)
    data = apply_filters(data, cfg)
    log(f"After solution date filter: {len(data.issues)} issues")

    plugins = []
    for mid in metric_ids:
        try:
            plugins.append(get_metric(mid))
        except KeyError:
            log(f"WARNING: Unknown metric '{mid}' — skipped.")

    for plugin in plugins:
        if isinstance(plugin, FlowTimeMetric):
            plugin.ct_method = ct_method
            plugin.target_ct = target_ct
        if isinstance(plugin, FlowVelocityMetric):
            plugin.pi_config_path = str(pi_config) if pi_config else ""

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
