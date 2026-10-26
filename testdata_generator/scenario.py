# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       02.09.2026
# Geändert:       26.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Portfolio-Szenario: erzeugt einen vollständigen, konsistenten Demo-
#   Datenraum mit allen Artefakten der Kette — Workflow-Dateien,
#   Jira-JSON (Generator), IssueTimes/CFD/Transitions (transform_data),
#   Solution-Configs (eine mit stage_map, Schema 2), Portfolio-Config und
#   PI-Config. Deterministisch über Seed; die Daten liegen relativ zu einem
#   Referenzdatum (Standard: heute), damit die Konfidenz-Ampel des
#   Portfolio-Reports nicht alles als veraltet einstuft.
#
#   Seit der Beta (Schnitt 1a, 26.10.2026) ist die Struktur Daten
#   (structure.py: beliebig viele Portfolios, Solutions, ARTs) und die
#   Geschichte bindet an Rollen (story.py): die erste Solution trägt den
#   Ausreißer, die zweite die schwache Quelle. Ohne Struktur entsteht die
#   Standard-Vorlage 1 Portfolio · 2 Solutions · je 3 ARTs — dieselben
#   Daten wie bisher. Die eingebaute Geschichte („Standard-Lage") am
#   Beispiel der Standard-Vorlage:
#
#   Eingebaute Geschichten für die Demo:
#   - "Alpha-3" ist der Ausreißer (Cycle Time ~3x) → A3-Hervorhebung.
#   - "Beta-3" liefert schwache Daten (viele Issues ohne First Date, kein CFD,
#     alter Datenstand) → A1-Ampel low, Abdeckungsgrad sichtbar.
#   - Solution Beta nutzt eine eigene stage_map (A4), Alpha den Default-Pfad.
#   - Beide Solutions bringen ein ROAM-Risiko-Register mit (B3); zwei
#     Owned-Risiken sind bewusst alt → Aging-Hervorhebung im Board.
#   - Beide Solutions bringen ein NFR-/Runway-Register mit (B2); Betas
#     API-NFR ist verletzt, ein Runway-Element überfällige Lücke → Ampel rot.
#   - Beide Solutions bringen eine Capability-Map mit (B1); Betas
#     Data-Insights-Capability ist kritisch, eine Alpha-Capability uncovered.
#   - Beide Solutions bringen ein Dependency-Register mit (B5); Alpha-1 →
#     Alpha-3 blockiert + überfällig, Beta-1 → Alpha-1 Cross-Solution.
#   - Beide Solutions bringen ein Decision-/Assumption-Log mit (B4); Betas
#     offene Annahme hat ihr Prüfdatum überschritten → „review due" rot.
#   - Delta-Briefing (D2): snapshot_prev/now.json liegen bei — die Prev-
#     Variante (story=STORY_PREV, 2 Wochen früher) hat weniger Items,
#     Beta-3 noch medium, AD-1 nur at_risk, kein BR-2; Runway-Lücke und
#     Annahme AS-B1 kippen erst im Now-Stand auf überfällig.
# =============================================================================

from __future__ import annotations

import dataclasses
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from build_reports.chart_texts import DEFAULT_LANG
from portfolio.capability_config import (
    HEALTH_AT_RISK,
    HEALTH_CRITICAL,
    HEALTH_HEALTHY,
    Capability,
    CapabilityMap,
    save_capabilities,
)
from portfolio.decision_config import (
    ASSUMPTION_CONFIRMED,
    ASSUMPTION_OPEN,
    DECISION_ACCEPTED,
    DECISION_SUPERSEDED,
    KIND_ASSUMPTION,
    KIND_DECISION,
    DecisionLog,
    LogEntry,
    save_decisions,
)
from portfolio.decision_points_config import (
    DecisionPoint,
    DecisionPointRegister,
    save_decision_points,
)
from portfolio.dependency_config import (
    DEP_AT_RISK,
    DEP_BLOCKED,
    DEP_DONE,
    DEP_ON_TRACK,
    Dependency,
    DependencyRegister,
    save_dependencies,
)
from portfolio.dora_config import DeliveryRegister, save_delivery
from portfolio.flow_problems_config import (
    FLOW_COMMITTED,
    FLOW_OPEN,
    FLOW_RESOLVED,
    FlowProblem,
    FlowProblemRegister,
    save_flow_problems,
)
from portfolio.nfr_config import (
    RUNWAY_BUILDING,
    RUNWAY_GAP,
    RUNWAY_IN_PLACE,
    STATUS_AT_RISK,
    STATUS_MET,
    STATUS_VIOLATED,
    Nfr,
    NfrRegister,
    RunwayItem,
    save_nfr,
)
from portfolio.risks_config import (
    IMPACT_HIGH,
    IMPACT_LOW,
    IMPACT_MEDIUM,
    ROAM_ACCEPTED,
    ROAM_MITIGATED,
    ROAM_OWNED,
    ROAM_RESOLVED,
    Risk,
    RiskRegister,
    save_risks,
)
from portfolio.slo_config import SloRegister, save_slo
from portfolio.solution_areas_config import SolutionArea, SolutionAreaRegister, save_solution_areas
from portfolio.solution_config import (
    KIND_PORTFOLIO,
    Member,
    SolutionConfig,
    StageMap,
    save_solution_config,
)
from portfolio.themes_config import (
    EPIC_DONE,
    EPIC_IN_PROGRESS,
    Epic,
    StrategicTheme,
    ThemesRegister,
    save_themes,
)
from sources.base import DoraRecord, QualityRecord, SloRecord
from testdata_generator.register_gen import (
    DEFAULT_SCALE,
    populate_registers,
)
from transform_data.processor import process_issues
from transform_data.workflow import parse_workflow
from transform_data.writers import write_cfd, write_issue_times, write_transitions

from .generator import (
    PATTERN_BATCH,
    PATTERN_CLUSTER,
    PATTERN_FLAT_TRIANGLE,
    PATTERN_NONE,
    PATTERN_TRIANGLE,
    GeneratorConfig,
    generate,
)
from .source_inputs import write_source_inputs
from .story import (
    ALL_EVENTS,
    EVENT_BLOCKED,
    EVENT_CROSS_SOLUTION,
    EVENT_HOST_PATTERNS,
    EVENT_NEW_RISK,
    EVENT_OUTLIER,
    EVENT_ROADMAPS,
    EVENT_SEAM,
    EVENT_SLO_BREACH,
    EVENT_WEAK_DECAY,
    EVENT_WEAK_SOURCE,
    ROLE_OUTLIER_ART,
    ROLE_WEAK_SOURCE_ART,
    STORY_TEMPLATES,
    RoleBinding,
    Story,
    bind_roles,
    save_story,
    story_for,
)
from .story import (
    TEMPLATE_STANDARD as STORY_STANDARD,
)
from .structure import (
    REGISTER_NAMES,
    TEMPLATE_STANDARD,
    WORKFLOW_CLASSIC,
    WORKFLOW_STAGE_MAP,
    PortfolioSpec,
    SolutionSpec,
    Structure,
    save_structure,
    structure_template,
    validate,
)

#: Workflow der Alpha-ARTs (klassische Namen; Solution Alpha nutzt den
#: Default-Pooling-Pfad über classify_stages).
_WORKFLOW_ALPHA = "\n".join([
    "Funnel",
    "Analysis",
    "Implementing",
    "Review",
    "Done",
    "<First>Implementing",
    "<Closed>Done",
])

#: Workflow der Beta-ARTs (abweichende Namen; Solution Beta zeigt dafür die
#: eigene stage_map aus A4).
_WORKFLOW_BETA = "\n".join([
    "Backlog",
    "Refinement",
    "Dev",
    "Test",
    "Released",
    "<First>Dev",
    "<Closed>Released",
])

#: Die stage_map der Solution Beta — kanonische Stages mit CFD-Grenzmarkern.
_BETA_STAGE_MAP = StageMap(
    stages={
        "Vorlauf": ["Backlog", "Refinement"],
        "Umsetzung": ["Dev", "Test"],
        "Fertig": ["Released"],
    },
    first_stage="Umsetzung",
    closed_stage="Fertig",
)


@dataclass
class _ArtProfile:
    """Generator profile for one demo ART (the built-in story per source).

    Trägt seit dem ART-Profile-Feature dieselben Regler wie die
    Einzel-ART-Erzeugung; per ``art_profiles`` in
    build_portfolio_scenario() sind sie je ART übersteuerbar.
    """
    name: str
    workflow_text: str
    mean_cycle_days: float
    completion_rate: float = 0.7
    todo_rate: float = 0.15
    stale_days: int = 0      # shift the data window back → old data_as_of
    write_cfd: bool = True   # False = source without CFD data
    issue_count: int = 120
    std_cycle_days: float | None = None   # None = 30 % vom Mittel
    backflow_prob: float = 0.1
    pattern: str = PATTERN_NONE
    pattern_strength: float = 0.5
    pi_duration_weeks: int = 12
    #: Untidiness of the stage paths (0.38.0); the demo ARTs look like real
    #: ones by default — a straight chain is a lie about any ART.
    realism: float = 0.6


#: Je ART übersteuerbare Profil-Felder (GUI-Dialog, CLI --art-profiles).
ART_PROFILE_FIELDS = ("issue_count", "mean_cycle_days", "std_cycle_days",
                      "completion_rate", "todo_rate", "backflow_prob",
                      "pattern", "pattern_strength", "pi_duration_weeks",
                      "realism")

_PATTERNS = (PATTERN_NONE, PATTERN_TRIANGLE, PATTERN_FLAT_TRIANGLE,
             PATTERN_CLUSTER, PATTERN_BATCH)

_INT_FIELDS = {"issue_count", "pi_duration_weeks"}


def _coerce_profile_value(key: str, value):
    """Coerce a GUI/JSON value to the profile field's type (validated).

    pattern_strength follows the user-facing 0–100 convention of the
    single-ART CLI/GUI and is stored as 0–1 internally.
    """
    if key == "pattern":
        value = str(value).strip().lower()
        if value not in _PATTERNS:
            raise ValueError(
                f"Unknown pattern '{value}' — expected one of "
                f"{', '.join(_PATTERNS)}.")
        return value
    try:
        number = int(value) if key in _INT_FIELDS else float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Invalid value for '{key}': {value!r} (number expected).") from exc
    if key in ("pattern_strength", "realism"):
        if not 0 <= number <= 100:
            raise ValueError(
                f"{key} must be 0–100, got {value!r}.")
        return number / 100.0
    return number


def apply_art_overrides(
    profiles: list[tuple[str, _ArtProfile]],
    art_profiles: dict[str, dict] | None,
) -> list[tuple[str, _ArtProfile]]:
    """
    Merge per-ART overrides onto the default demo profiles.

    Keys are the ART short names ("Alpha-1" … "Beta-3"); values map
    ART_PROFILE_FIELDS to new values (numbers may arrive as strings —
    GUI fields and JSON files). Explicit overrides win in BOTH stands
    (now and prev); everything not overridden keeps its story value.

    Raises:
        ValueError: Unknown ART name, unknown field, or invalid value.
    """
    if not art_profiles:
        return profiles
    known = {profile.name for _, profile in profiles}
    unknown = set(art_profiles) - known
    if unknown:
        raise ValueError(
            f"Unknown ART name(s) {', '.join(sorted(unknown))} — known: "
            f"{', '.join(sorted(known))}.")
    out: list[tuple[str, _ArtProfile]] = []
    for solution_key, profile in profiles:
        overrides = art_profiles.get(profile.name) or {}
        bad = set(overrides) - set(ART_PROFILE_FIELDS)
        if bad:
            raise ValueError(
                f"Unknown profile field(s) {', '.join(sorted(bad))} for "
                f"'{profile.name}' — allowed: "
                f"{', '.join(ART_PROFILE_FIELDS)}.")
        coerced = {k: _coerce_profile_value(k, v)
                   for k, v in overrides.items()}
        out.append((solution_key,
                    dataclasses.replace(profile, **coerced)
                    if coerced else profile))
    return out


def _fmt_num(value: float) -> str:
    """Compact display of a profile number (12.0 -> "12")."""
    return f"{value:g}"


def default_art_profile_rows() -> dict[str, dict[str, str]]:
    """
    Display strings of the default demo profiles, per ART — the
    prefill of the GUI dialog "ART-Profile …". pattern_strength is
    shown on the user-facing 0–100 scale; an empty std_cycle_days
    means "30 % of the mean" (the generator default).
    """
    rows: dict[str, dict[str, str]] = {}
    for _solution_key, profile in _profiles():
        rows[profile.name] = {
            "issue_count": str(profile.issue_count),
            "mean_cycle_days": _fmt_num(profile.mean_cycle_days),
            "std_cycle_days": ("" if profile.std_cycle_days is None
                               else _fmt_num(profile.std_cycle_days)),
            "completion_rate": _fmt_num(profile.completion_rate),
            "todo_rate": _fmt_num(profile.todo_rate),
            "backflow_prob": _fmt_num(profile.backflow_prob),
            "pattern": profile.pattern,
            "pattern_strength": str(int(round(
                profile.pattern_strength * 100))),
            "pi_duration_weeks": str(profile.pi_duration_weeks),
            "realism": str(int(round(profile.realism * 100))),
        }
    return rows


def parse_art_profile_entries(
    entries: dict[str, dict[str, str]],
) -> dict[str, dict]:
    """
    Diff dialog entries against the defaults and validate the result.

    Only fields whose display string differs from the default become
    overrides — an unchanged dialog yields {} and every story tweak
    (incl. Beta-3's prev variant) stays untouched. Values are validated
    via apply_art_overrides, so errors surface at OK time.

    Returns:
        {art_name: {field: raw value}} — ready for
        build_portfolio_scenario(art_profiles=...).

    Raises:
        ValueError: Unknown ART/field or invalid value.
    """
    defaults = default_art_profile_rows()
    overrides: dict[str, dict] = {}
    for name, fields in entries.items():
        if name not in defaults:
            raise ValueError(
                f"Unknown ART name(s) {name} — known: "
                f"{', '.join(sorted(defaults))}.")
        changed = {
            key: value.strip()
            for key, value in fields.items()
            if value.strip() != defaults[name].get(key, "")
            and value.strip() != ""
        }
        if changed:
            overrides[name] = changed
    apply_art_overrides(_profiles(), overrides)  # validate; raises ValueError
    return overrides


STORY_NOW = "now"
STORY_PREV = "prev"

#: Step-wise progress of a build: (step id, state, detail). The ids are the
#: nine steps of the UI prototype (see dataspace.STEPS); states are
#: "running" and "done". None = no reporting (temp stand builds).
ProgressHook = Callable[[str, str, str], None]


def _emit(progress: ProgressHook | None, step: str, state: str, detail: str = "") -> None:
    if progress is not None:
        progress(step, state, detail)


#: Series of stands (E3, 26.10.2026): the data room ships N stands, two
#: weeks apart, the last one being the reference date; snapshot_prev/now
#: stay as aliases of the last two. Every earlier stand is the same story
#: two weeks younger: fewer issues (PREV_ISSUE_FACTOR per step) and the
#: register state before the "now" events.
DEFAULT_STANDS = 6
MIN_STANDS = 2
MAX_STANDS = 12
STAND_INTERVAL_DAYS = 14
PREV_ISSUE_FACTOR = 0.88

#: Cycle-time means of the ordinary ARTs in order of appearance
#: (solution j, ART i -> pool[(2·j + i) % len]); reproduces the demo
#: portfolio's 12/16 (Alpha-1/-2) and 14/18 (Beta-1/-2).
_CYCLE_POOL = (12, 16, 14, 18, 15, 13, 17, 11, 19, 10)
#: The outlier's mean cycle time (~3x its sister ARTs).
_OUTLIER_CYCLE_DAYS = 45


def _workflow_text(kind: str) -> str:
    return _WORKFLOW_BETA if kind == WORKFLOW_STAGE_MAP else _WORKFLOW_ALPHA


def _profiles(
    story: str = STORY_NOW,
    art_profiles: dict[str, dict] | None = None,
    portfolio: PortfolioSpec | None = None,
    binding: RoleBinding | None = None,
    issue_scale: float | None = None,
    active: frozenset[str] | None = None,
) -> list[tuple[str, _ArtProfile]]:
    """
    (solution key, profile) pairs for every ART of the portfolio.

    Without ``portfolio`` the standard structure (2 solutions × 3 ARTs) is
    used — the demo portfolio of all releases so far. The roles from
    ``binding`` (bind_roles) decide the story profiles: the outlier gets
    the ~3x cycle time, the weak source the data gaps (few first dates,
    no CFD, data 60 days stale, fewer issues); everything else draws its
    mean from _CYCLE_POOL by position.

    ``art_profiles`` overrides individual fields per ART (see
    apply_art_overrides) — explicit overrides win in both stands.
    ``active`` names the story events in force at this stand (Schnitt 2):
    EVENT_OUTLIER gives the outlier its ~3x cycle time, EVENT_WEAK_SOURCE
    the weak source its data gaps (few first dates, no CFD, stale, fewer
    issues) and EVENT_WEAK_DECAY the final decay (80 % without first date
    -> confidence low; before: 45 % -> medium). None derives the set from
    ``story``: STORY_NOW = every event, STORY_PREV = the standard story's
    start events — the two stands of the old Delta-Briefing demo.
    ``story=STORY_PREV`` also scales the issues (``issue_scale`` of the
    possibly overridden count, default PREV_ISSUE_FACTOR = one step of two
    weeks).
    """
    portfolio = portfolio or structure_template(TEMPLATE_STANDARD).portfolios[0]
    binding = binding or bind_roles(portfolio)
    if active is None:
        active = (ALL_EVENTS if story != STORY_PREV
                  else story_for(STORY_STANDARD, binding, stands=2).active_events(1))
    outlier = binding.art(ROLE_OUTLIER_ART) if EVENT_OUTLIER in active else None
    weak = binding.art(ROLE_WEAK_SOURCE_ART) if EVENT_WEAK_SOURCE in active else None
    base: list[tuple[str, _ArtProfile]] = []
    for j, solution in enumerate(portfolio.solutions):
        wf = _workflow_text(solution.workflow)
        for i, art in enumerate(solution.arts):
            if art == outlier:
                # Der Ausreißer: Cycle Time ~3x der Schwester-ARTs (A3).
                profile = _ArtProfile(art, wf,
                                      mean_cycle_days=_OUTLIER_CYCLE_DAYS)
            elif art == weak:
                # Die schwache Quelle: kaum begonnene Issues (kein First
                # Date), kein CFD, Datenstand 60 Tage alt (A1-Ampel low);
                # vor dem Verfall (EVENT_WEAK_DECAY) noch 45 % -> medium.
                profile = _ArtProfile(
                    art, wf, mean_cycle_days=15, completion_rate=0.15,
                    todo_rate=0.8 if EVENT_WEAK_DECAY in active else 0.45,
                    stale_days=60, write_cfd=False, issue_count=60)
            else:
                profile = _ArtProfile(
                    art, wf,
                    mean_cycle_days=_CYCLE_POOL[(2 * j + i) % len(_CYCLE_POOL)])
            base.append((solution.key, profile))
    merged = apply_art_overrides(base, art_profiles)
    if story != STORY_PREV:
        return merged
    scale_factor = PREV_ISSUE_FACTOR if issue_scale is None else issue_scale
    return [(solution_key, dataclasses.replace(
                profile, issue_count=max(1, int(profile.issue_count * scale_factor))))
            for solution_key, profile in merged]


# --- Story anchors, bound to roles -------------------------------------------

@dataclass(frozen=True)
class _Names:
    """
    Names and ID tag of one solution as the anchors see them.

    ``art(i)`` clamps to the last ART, so a two-ART solution still gets
    every anchor; ``mid`` is a middle ART distinct from first and last
    (None for fewer than three ARTs) for list entries that must not repeat.
    """
    short: str
    solution: str
    tag: str
    arts: tuple[str, ...]

    def art(self, i: int) -> str:
        return self.arts[i] if i < 0 else self.arts[min(i, len(self.arts) - 1)]

    @property
    def first(self) -> str:
        return self.arts[0]

    @property
    def last(self) -> str:
        return self.arts[-1]

    @property
    def plain_last(self) -> str:
        return self.last.removeprefix("ART ")

    @property
    def mid(self) -> str | None:
        return self.arts[1] if len(self.arts) >= 3 else None

    @property
    def pairs_ok(self) -> bool:
        return len(self.arts) >= 2


def _uniq(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def _solution_tags(portfolio: PortfolioSpec) -> dict[str, str]:
    """Short name -> register ID tag: first letter, disambiguated by index."""
    tags: dict[str, str] = {}
    used: set[str] = set()
    for index, solution in enumerate(portfolio.solutions):
        letter = solution.short[:1].upper() or "S"
        tag = letter if letter not in used else f"{letter}{index + 1}"
        used.add(tag)
        tags[solution.short] = tag
    return tags


def _names(solution: SolutionSpec, tag: str) -> _Names:
    return _Names(short=solution.short, solution=solution.display_name,
                  tag=tag, arts=tuple(solution.member_names))


def _host_risks(reference: date, h: _Names,
                active: frozenset[str] = ALL_EVENTS) -> RiskRegister:
    """ROAM register of the host solution: healthy spread; with EVENT_HOST_PATTERNS
    one aging owned risk."""
    t = h.tag
    patterns = EVENT_HOST_PATTERNS in active
    return RiskRegister(risks=[
        Risk(f"{t}R-1", "Test environment for PI 4 not ordered yet",
             ROAM_OWNED, owner="System Team", impact=IMPACT_HIGH,
             status_since=reference - timedelta(days=45 if patterns else 5),
             notes=("Aging: owned for over a month without visible movement."
                    if patterns else "Ordered last week; delivery date confirmed.")),
        Risk(f"{t}R-2", "Key supplier interface spec still in draft",
             ROAM_OWNED, owner=h.mid or h.first, impact=IMPACT_MEDIUM,
             status_since=reference - timedelta(days=10)),
        Risk(f"{t}R-3", "Legacy migration effort underestimated",
             ROAM_MITIGATED, owner=h.last, impact=IMPACT_MEDIUM,
             status_since=reference - timedelta(days=20),
             notes="Scope cut agreed; buffer feature moved to next PI."),
        Risk(f"{t}R-4", "License audit finding on reporting library",
             ROAM_RESOLVED, owner="System Team", impact=IMPACT_LOW,
             status_since=reference - timedelta(days=5)),
        Risk(f"{t}R-5", "Peak-load capacity above target only with new cluster",
             ROAM_ACCEPTED, owner=h.first, impact=IMPACT_LOW,
             status_since=reference - timedelta(days=30)),
    ])


def _second_risks(reference: date, s: _Names,
                  active: frozenset[str] = ALL_EVENTS) -> RiskRegister:
    """
    ROAM register of the second solution: with EVENT_WEAK_SOURCE the second
    aging owned risk lives here; EVENT_NEW_RISK adds {tag}R-2 (the risk the
    Delta-Briefing shows as new).
    """
    t = s.tag
    weak = EVENT_WEAK_SOURCE in active
    risks = [
        Risk(f"{t}R-1", f"Data quality of {s.last} blocks solution reporting",
             ROAM_OWNED if weak else ROAM_MITIGATED, owner=s.last, impact=IMPACT_HIGH,
             status_since=reference - timedelta(days=50 if weak else 6),
             notes=("Aging: matches the weak-source story of this scenario." if weak
                    else "Export fixed; monitoring the next two extracts.")),
        Risk(f"{t}R-3", "Vendor API rate limits during nightly sync",
             ROAM_ACCEPTED, owner=s.first, impact=IMPACT_MEDIUM,
             status_since=reference - timedelta(days=15)),
        Risk(f"{t}R-4", "Duplicate effort with platform team clarified",
             ROAM_RESOLVED, owner=s.mid or s.first, impact=IMPACT_LOW,
             status_since=reference - timedelta(days=12)),
    ]
    if EVENT_NEW_RISK in active:
        risks.insert(1, Risk(
            f"{t}R-2", "Security review for release milestone not scheduled",
            ROAM_MITIGATED, owner="Shared Services", impact=IMPACT_HIGH,
            status_since=reference - timedelta(days=7),
            notes="Interim: external reviewer booked for next sprint."))
    return RiskRegister(risks=risks)


def _host_capabilities(reference: date, h: _Names,
                       active: frozenset[str] = ALL_EVENTS) -> CapabilityMap:
    """Capability map of the host solution: solid; EVENT_OUTLIER puts billing
    at risk, EVENT_HOST_PATTERNS leaves one capability uncovered."""
    t = h.tag
    return CapabilityMap(capabilities=[
        Capability(f"{t}C-1", "Order management", HEALTH_HEALTHY,
                   arts=_uniq([h.first, h.mid or h.first]), owner=h.first,
                   assessed_on=reference - timedelta(days=14)),
        Capability(f"{t}C-2", "Billing & invoicing",
                   HEALTH_AT_RISK if EVENT_OUTLIER in active else HEALTH_HEALTHY,
                   arts=[h.last], owner=h.last,
                   assessed_on=reference - timedelta(days=14),
                   notes=("Depends on the outlier ART's delivery pace."
                          if EVENT_OUTLIER in active else "")),
        # Uncovered: business value nobody delivers — the ARTs cell is flagged.
        Capability(f"{t}C-3", "Partner self-service", HEALTH_HEALTHY,
                   arts=[] if EVENT_HOST_PATTERNS in active else [h.first],
                   owner="System Team",
                   assessed_on=reference - timedelta(days=45),
                   notes=("Planned; no ART assigned yet."
                          if EVENT_HOST_PATTERNS in active else "")),
    ])


def _second_capabilities(reference: date, s: _Names,
                         active: frozenset[str] = ALL_EVENTS) -> CapabilityMap:
    """Capability map of the second solution: with EVENT_WEAK_SOURCE the
    critical capability lives here."""
    t = s.tag
    weak = EVENT_WEAK_SOURCE in active
    return CapabilityMap(capabilities=[
        Capability(f"{t}C-1", "Data insights & reporting",
                   HEALTH_CRITICAL if weak else HEALTH_HEALTHY,
                   arts=[s.last], owner=s.last,
                   assessed_on=reference - timedelta(days=7),
                   notes=("Matches the weak-source story: data quality blocks it."
                          if weak else "")),
        Capability(f"{t}C-2", "Customer onboarding", HEALTH_HEALTHY,
                   arts=_uniq([s.first, s.mid or s.first]), owner=s.first,
                   assessed_on=reference - timedelta(days=7)),
        Capability(f"{t}C-3", "Payment processing", HEALTH_HEALTHY,
                   arts=[s.mid or s.first], owner=s.mid or s.first,
                   assessed_on=reference - timedelta(days=7)),
    ])


def _host_themes(h: _Names, active: frozenset[str] = ALL_EVENTS) -> ThemesRegister:
    """
    Themes/roadmap of the host solution: with EVENT_HOST_PATTERNS one orphan
    theme, with EVENT_ROADMAPS the zombie epic (EP-{tag}9 loses its theme —
    one of the 'updated roadmaps' changes of the Delta-Briefing).
    """
    zombie = EVENT_ROADMAPS in active
    orphan = EVENT_HOST_PATTERNS in active
    t = h.tag
    return ThemesRegister(
        themes=[
            StrategicTheme(f"T-{t}1", "Digital ordering end-to-end",
                           "Order intake to billing without media breaks."),
            # Deklariert und vergessen: kein einziges Epic zahlt ein.
            StrategicTheme(f"T-{t}2", "Green operations",
                           "Energy-aware runtime operations."),
        ],
        epics=[
            Epic(f"EP-{t}1", "Self-service order portal", h.first,
                 "P1", theme=f"T-{t}1", status=EPIC_IN_PROGRESS),
            Epic(f"EP-{t}2", "Billing integration", h.mid or h.first,
                 "P2", theme=f"T-{t}1"),
            Epic(f"EP-{t}3", "Order analytics", h.first,
                 "Y1", theme=f"T-{t}1" if orphan else f"T-{t}2"),
            # Die Zombie-Initiative: vor EVENT_ROADMAPS noch mit Theme.
            Epic(f"EP-{t}9", "Legacy portal rewrite", h.last,
                 "Y1", theme="" if zombie else f"T-{t}1"),
        ],
    )


def _second_themes(s: _Names, active: frozenset[str] = ALL_EVENTS) -> ThemesRegister:
    """
    Themes/roadmap of the second solution: before EVENT_ROADMAPS the
    data-quality epic is parked in P2 — pulling it into P1 is the second
    'updated roadmaps' change.
    """
    pulled = EVENT_ROADMAPS in active
    t = s.tag
    return ThemesRegister(
        themes=[
            StrategicTheme(f"T-{t}1", "Trusted reporting",
                           "One reporting truth across the solution."),
        ],
        epics=[
            Epic(f"EP-{t}1", "Vendor sync hardening", s.first,
                 "P1", theme=f"T-{t}1", status=EPIC_DONE),
            Epic(f"EP-{t}2", f"{s.plain_last} data-quality remediation", s.last,
                 "P1" if pulled else "P2", theme=f"T-{t}1",
                 status=EPIC_IN_PROGRESS),
            Epic(f"EP-{t}3", "Cross-solution reporting hub", s.mid or s.first,
                 "Y2", theme=f"T-{t}1"),
        ],
    )


def _host_decision_points(reference: date, h: _Names) -> DecisionPointRegister:
    """
    The host's agreed alarms (D4): one triggered (the outlier's P85 above the
    agreed 30 days), one relative change that needs a previous stand, one
    below threshold (blocked dependencies), one not agreed yet (no threshold).
    """
    agreed = reference - timedelta(days=14)
    t = h.tag
    return DecisionPointRegister(points=[
        DecisionPoint(f"DP-{t}1",
                      f"P85 cycle time of {h.plain_last} above the agreed 30 days",
                      f"S1/units({h.last}).p85_ct", ">=", 30.0, "",
                      question=f"Cut the scope of {h.plain_last} in the next PI?",
                      reaction=f"Lead team of {h.plain_last} brings a proposal "
                               f"to the next VSC",
                      team=h.last, agreed_on=agreed),
        DecisionPoint(f"DP-{t}2", "Open items grow faster than 10 % between stands",
                      "D/total.open", ">=", 10.0, "%",
                      question="Introduce a WIP limit at solution level?",
                      reaction="Solution train engineer prepares a WIP proposal",
                      team=h.solution, agreed_on=agreed),
        DecisionPoint(f"DP-{t}3", "Two or more dependencies blocked",
                      "S1/governance.dependencies.count(blocked)", ">=", 2.0, "",
                      question="Escalate the blocked seams to the VSC?",
                      reaction="Dependency owners report within two days",
                      team=h.solution, agreed_on=agreed),
        DecisionPoint(f"DP-{t}4", "Median cycle time of the solution",
                      "S1/total.median_ct", ">=", None, "",
                      question="Which median would make us act?",
                      reaction="Threshold still to be agreed in the next VSC",
                      team=h.solution),
    ])


def _second_decision_points(reference: date, s: _Names) -> DecisionPointRegister:
    """One agreed point in the second solution, below threshold."""
    return DecisionPointRegister(points=[
        DecisionPoint(f"DP-{s.tag}1", "Solution grows beyond 500 items in the window",
                      "S1/total.items", ">=", 500.0, "",
                      question="Split the solution?",
                      reaction="Architecture board reviews the cut",
                      team=s.solution, agreed_on=reference - timedelta(days=30)),
    ])


def _host_solution_areas(reference: date, h: _Names,
                         active: frozenset[str] = ALL_EVENTS) -> SolutionAreaRegister:
    """
    Solution areas of the host: the same seam first × last ART opened a third
    time for the same topic — the EA signal (P5). The third opening comes
    with EVENT_SEAM, so the delta documents the signal coming on.
    """
    if not h.pairs_ok:
        return SolutionAreaRegister()
    t = h.tag
    seam = [h.first, h.last]
    areas = [
        SolutionArea(f"SA-{t}1", "Shared test environment for order flow",
                     "test environment", list(seam),
                     opened_on=reference - timedelta(days=220),
                     closed_on=reference - timedelta(days=190)),
        SolutionArea(f"SA-{t}2", "Shared test environment, second round",
                     "test environment", list(seam),
                     opened_on=reference - timedelta(days=120),
                     closed_on=reference - timedelta(days=95),
                     notes="Same seam, same topic: second time."),
        SolutionArea(f"SA-{t}4", "Checkout latency task force", "latency",
                     _uniq([h.first, h.mid or h.last]),
                     opened_on=reference - timedelta(days=60),
                     closed_on=reference - timedelta(days=35)),
    ]
    if EVENT_SEAM in active:
        areas.insert(2, SolutionArea(
            f"SA-{t}3", "Shared test environment, third round",
            "test environment", list(seam),
            opened_on=reference - timedelta(days=9),
            notes="Third time at the same seam - the EA signal: this is a cut or "
                  "architecture problem, not a team problem."))
    return SolutionAreaRegister(areas=areas)


def _second_solution_areas(reference: date, s: _Names) -> SolutionAreaRegister:
    """One active area in the second solution - rare, as it should be."""
    if not s.pairs_ok:
        return SolutionAreaRegister()
    return SolutionAreaRegister(areas=[
        SolutionArea(f"SA-{s.tag}1", "Export quality working group",
                     "export quality", [s.first, s.last],
                     opened_on=reference - timedelta(days=20)),
    ])


def _host_flow_problems(reference: date, h: _Names,
                        active: frozenset[str] = ALL_EVENTS) -> FlowProblemRegister:
    """Flow problems of the host: with EVENT_HOST_PATTERNS one has survived
    three conferences."""
    t = h.tag
    survivor = EVENT_HOST_PATTERNS in active
    return FlowProblemRegister(problems=[
        # Das Workshop-Muster: geloggt, nie mitigiert, taucht wieder auf.
        FlowProblem(f"FP-{t}1", "Test-environment provisioning takes weeks",
                    FLOW_OPEN if survivor else FLOW_COMMITTED,
                    value_streams=list(h.arts),
                    source="VSC", owner="System Team",
                    raised_on=reference - timedelta(days=140 if survivor else 30),
                    conferences=3 if survivor else 1,
                    resolution_commitment=("" if survivor
                                           else "Self-service environments in PI 5"),
                    notes=("Survivor: raised at three conferences, still open."
                           if survivor else "")),
        FlowProblem(f"FP-{t}2", "Review bottleneck at architecture board",
                    FLOW_COMMITTED,
                    value_streams=[h.mid or h.first],
                    source=h.mid or h.first, owner="System Team",
                    raised_on=reference - timedelta(days=40),
                    conferences=1,
                    resolution_commitment="Second review slot per week",
                    follow_up_pi="PI 5"),
    ])


def _second_flow_problems(reference: date, s: _Names,
                          active: frozenset[str] = ALL_EVENTS) -> FlowProblemRegister:
    """Flow problems of the second solution: with EVENT_WEAK_SOURCE the weak
    source blocks two streams."""
    t = s.tag
    weak = EVENT_WEAK_SOURCE in active
    return FlowProblemRegister(problems=[
        FlowProblem(f"FP-{t}1",
                    f"{s.plain_last} export quality blocks solution reporting",
                    FLOW_OPEN if weak else FLOW_RESOLVED,
                    value_streams=_uniq([s.first, s.last]),
                    source="VSC", owner=s.last,
                    raised_on=reference - timedelta(days=200),
                    conferences=4 if weak else 2,
                    resolution_commitment="" if weak else "Export job rebuilt",
                    notes=("Cross-VS survivor: matches the weak-source story."
                           if weak else "")),
        FlowProblem(f"FP-{t}2", "Shared staging window conflicts",
                    FLOW_RESOLVED,
                    value_streams=_uniq([s.first, s.mid or s.first]),
                    source=s.first, owner=s.mid or s.first,
                    raised_on=reference - timedelta(days=90),
                    conferences=2,
                    resolution_commitment="Calendar-based slot booking"),
    ])


def _host_slo(reference: date, active: frozenset[str] = ALL_EVENTS) -> SloRegister:
    """SLOs of the host solution: healthy; with EVENT_HOST_PATTERNS one budget
    running low."""
    src = "demo-scenario"
    at = reference.isoformat()
    return SloRegister(records=[
        SloRecord("Order API", "p95 latency < 200 ms", 99.9, sli_pct=99.97,
                  source=src, fetched_at=at),
        # Budget fast aufgebraucht: SLI knapp ueber Ziel -> at_risk.
        SloRecord("Checkout", "availability", 99.5,
                  sli_pct=99.55 if EVENT_HOST_PATTERNS in active else 99.9,
                  source=src, fetched_at=at),
        SloRecord("Search", "p99 latency < 800 ms", 99.0, sli_pct=99.8,
                  source=src, fetched_at=at),
    ])


def _second_slo(reference: date, active: frozenset[str] = ALL_EVENTS) -> SloRegister:
    """SLOs of the second solution: with EVENT_SLO_BREACH the sync service has
    burned its budget."""
    src = "demo-scenario"
    at = reference.isoformat()
    return SloRegister(records=[
        # Die Geschichte: der Sync-Dienst (Umfeld der schwachen Quelle)
        # reisst sein SLO.
        SloRecord("Order Sync API", "availability", 99.5,
                  sli_pct=99.1 if EVENT_SLO_BREACH in active else 99.7,
                  source=src, fetched_at=at),
        SloRecord("Reporting", "p95 latency < 500 ms", 99.0, sli_pct=99.6,
                  source=src, fetched_at=at),
    ])


def _host_delivery(reference: date, h: _Names,
                   active: frozenset[str] = ALL_EVENTS) -> DeliveryRegister:
    """Delivery health of the host: solid; with EVENT_OUTLIER the outlier
    ships slowly."""
    src = "demo-scenario"
    at = reference.isoformat()
    slow = EVENT_OUTLIER in active
    dora = [
        DoraRecord(h.first, deployments_per_day=1.4,
                   lead_time_hours=18.0, change_failure_rate_pct=4.0,
                   time_to_restore_hours=0.8, source=src, fetched_at=at),
    ]
    if h.mid:
        dora.append(DoraRecord(h.mid, deployments_per_day=0.6,
                               lead_time_hours=40.0, change_failure_rate_pct=8.0,
                               time_to_restore_hours=6.0, source=src,
                               fetched_at=at))
    if h.pairs_ok:
        # Der Ausreisser liefert auch selten und langsam.
        dora.append(DoraRecord(h.last, deployments_per_day=0.05 if slow else 0.7,
                               lead_time_hours=520.0 if slow else 36.0,
                               change_failure_rate_pct=14.0 if slow else 7.0,
                               time_to_restore_hours=20.0 if slow else 4.0, source=src,
                               fetched_at=at))
    quality = [
        QualityRecord(h.first, coverage_pct=78.0,
                      maintainability="A", critical_issues=0,
                      source=src, fetched_at=at),
    ]
    if h.pairs_ok:
        quality.append(QualityRecord(h.last, coverage_pct=55.0 if slow else 70.0,
                                     maintainability="C" if slow else "B",
                                     critical_issues=2 if slow else 1,
                                     source=src, fetched_at=at))
    return DeliveryRegister(dora=dora, quality=quality)


def _second_delivery(reference: date, s: _Names,
                     active: frozenset[str] = ALL_EVENTS) -> DeliveryRegister:
    """Delivery health of the second solution: with EVENT_WEAK_SOURCE the weak
    source is low tier."""
    src = "demo-scenario"
    at = reference.isoformat()
    weak = EVENT_WEAK_SOURCE in active
    dora = []
    if s.pairs_ok:
        dora.append(DoraRecord(s.first, deployments_per_day=0.9,
                               lead_time_hours=30.0, change_failure_rate_pct=6.0,
                               time_to_restore_hours=3.0, source=src,
                               fetched_at=at))
    # Die Geschichte: die schwache Quelle auch im Delivery-Bild low.
    dora.append(DoraRecord(s.last, deployments_per_day=0.02 if weak else 0.8,
                           lead_time_hours=800.0 if weak else 32.0,
                           change_failure_rate_pct=38.0 if weak else 7.0,
                           time_to_restore_hours=30.0 if weak else 3.5,
                           source=src, fetched_at=at))
    return DeliveryRegister(
        dora=dora,
        quality=[
            QualityRecord(s.last, coverage_pct=31.0 if weak else 72.0,
                          maintainability="D" if weak else "B",
                          critical_issues=7 if weak else 1,
                          source=src, fetched_at=at),
        ],
    )


def _host_decisions(reference: date, h: _Names) -> DecisionLog:
    """Decision log of the host: a superseded chain plus a confirmed assumption."""
    t = h.tag
    return DecisionLog(entries=[
        LogEntry(f"ADR-{t}2", KIND_DECISION,
                 "Pool ARTs via fixed three-group mapping",
                 DECISION_SUPERSEDED, owner="System Team",
                 logged_on=reference - timedelta(days=120)),
        LogEntry(f"ADR-{t}1", KIND_DECISION,
                 "Pool ARTs via custom stage map (schema 2)",
                 DECISION_ACCEPTED, owner="System Team",
                 logged_on=reference - timedelta(days=60),
                 supersedes=f"ADR-{t}2",
                 notes="Keeps heterogeneous workflows comparable."),
        LogEntry(f"AS-{t}1", KIND_ASSUMPTION,
                 "All ARTs keep exporting weekly Jira snapshots",
                 ASSUMPTION_CONFIRMED, owner=h.first,
                 logged_on=reference - timedelta(days=90),
                 review_by=reference + timedelta(days=90)),
    ])


def _second_decisions(reference: date, s: _Names,
                      active: frozenset[str] = ALL_EVENTS) -> DecisionLog:
    """Decision log of the second solution: with EVENT_WEAK_SOURCE the overdue
    open assumption lives here."""
    t = s.tag
    weak = EVENT_WEAK_SOURCE in active
    return DecisionLog(entries=[
        LogEntry(f"ADR-{t}1", KIND_DECISION,
                 "Buy vendor sync service instead of building",
                 DECISION_ACCEPTED, owner=s.first,
                 logged_on=reference - timedelta(days=150),
                 notes=f"Trade-off: rate limits accepted (see dependency {t}D-1)."),
        # Die Geschichte: eine offene Annahme mit überschrittenem Prüfdatum —
        # genau die Sorte Selbstberuhigung, die ein Premortem aufdecken soll.
        LogEntry(f"AS-{t}1", KIND_ASSUMPTION,
                 f"{s.plain_last} data quality will fix itself with the next "
                 f"Jira rollout",
                 ASSUMPTION_OPEN if weak else ASSUMPTION_CONFIRMED, owner=s.last,
                 logged_on=reference - timedelta(days=70),
                 review_by=reference - timedelta(days=10 if weak else -80),
                 notes=("Review due: matches the weak-source story." if weak
                        else "Confirmed after the export job was rebuilt.")),
    ])


def _host_dependencies(
    reference: date, h: _Names, o: _Names | None,
    active: frozenset[str] = ALL_EVENTS,
) -> DependencyRegister:
    """
    Dependencies of the host: the overdue blocked one lives here.

    {tag}D-1 is at risk while the outlier under-delivers (EVENT_OUTLIER) and
    blocked with EVENT_BLOCKED — the status transition the Delta-Briefing
    shows. {tag}D-4 is the second seam towards the second solution and
    carries the same idea for the decision-point indicator: at risk with
    EVENT_CROSS_SOLUTION. Without a second solution (``o`` None) that seam
    does not exist.
    """
    t = h.tag
    deps: list[Dependency] = []
    if h.pairs_ok:
        # Die Geschichte: der Ausreißer liefert nicht — blockiert und
        # überfällig, springt in der Heatmap rot an.
        pressure = EVENT_BLOCKED in active or EVENT_OUTLIER in active
        deps.append(Dependency(
            f"{t}D-1", "Billing API contract for order flow",
            from_art=h.first, to_art=h.last,
            status=(DEP_BLOCKED if EVENT_BLOCKED in active
                    else DEP_AT_RISK if EVENT_OUTLIER in active else DEP_ON_TRACK),
            due=reference - timedelta(days=15 if pressure else -20),
            notes=("Overdue: matches the outlier story of this scenario."
                   if pressure else "")))
    if h.mid:
        deps.append(Dependency(
            f"{t}D-2", "Shared test fixtures for the order domain",
            from_art=h.mid, to_art=h.first,
            status=DEP_ON_TRACK, due=reference + timedelta(days=25)))
    deps.append(Dependency(
        f"{t}D-3", "SSO integration with platform services",
        from_art=h.mid or h.first, to_art="Platform Services",
        status=DEP_ON_TRACK, due=reference + timedelta(days=40),
        notes="External integration point outside the solution."))
    if o is not None:
        # Zweite Naht zwischen den Value Streams, Gegenrichtung zu {o}D-1:
        # laengst ueberfaellig — der schwerste Posten des Wecker-Indikators.
        cross = EVENT_CROSS_SOLUTION in active
        overdue = cross or EVENT_HOST_PATTERNS in active   # one of the silent patterns
        deps.append(Dependency(
            f"{t}D-4", f"Customer master data feed for {o.short} reporting",
            from_art=h.first, to_art=o.mid or o.last,
            status=DEP_AT_RISK if cross else DEP_ON_TRACK,
            due=reference - timedelta(days=35 if overdue else -30),
            notes=f"Cross-solution seam towards {o.solution}."))
    return DependencyRegister(dependencies=deps)


def _second_dependencies(
    reference: date, s: _Names, o: _Names,
    active: frozenset[str] = ALL_EVENTS,
) -> DependencyRegister:
    """
    Dependencies of the second solution: the seam towards the host lives here.

    Together with the host's {tag}D-4 these make the decision point
    demonstrable: with EVENT_CROSS_SOLUTION the pressure between the two
    value streams rises visibly between stands, while every single train
    looks unremarkable on its own.
    """
    t = s.tag
    cross = EVENT_CROSS_SOLUTION in active
    deps = [
        # Cross-Solution-Integration: die zweite Solution braucht die
        # Order-Events des Hosts — sichtbar nur im Portfolio-Report.
        Dependency(f"{t}D-1", "Order events feed for reporting",
                   from_art=s.first, to_art=o.first,
                   status=(DEP_AT_RISK if cross or EVENT_WEAK_SOURCE in active
                           else DEP_ON_TRACK),
                   due=reference + timedelta(days=10),
                   notes=f"Cross-solution integration with {o.solution}."),
    ]
    if s.pairs_ok:
        deps.append(Dependency(
            f"{t}D-2", "Sync-service schema migration",
            from_art=s.mid or s.first, to_art=s.last,
            status=DEP_DONE, due=reference - timedelta(days=30)))
    # Die Naht eskaliert: vor zwei Wochen gefaehrdet, jetzt blockiert.
    # Das Faelligkeitsdatum ist in beiden Staenden dasselbe (beide teilen
    # das Referenzdatum) — es steigt allein das Statusgewicht.
    deps.append(Dependency(
        f"{t}D-3", "Shared identity claims for order events",
        from_art=s.last, to_art=o.mid or o.first,
        status=(DEP_BLOCKED if cross
                else DEP_AT_RISK if EVENT_WEAK_SOURCE in active else DEP_ON_TRACK),
        due=reference - timedelta(days=12 if cross or EVENT_WEAK_SOURCE in active else -15),
        notes=f"Cross-solution integration with {o.solution}."))
    return DependencyRegister(dependencies=deps)


def _host_nfr(reference: date, h: _Names) -> NfrRegister:
    """NFR/runway register of the host: healthy, one NFR at risk."""
    t = h.tag
    return NfrRegister(
        nfrs=[
            Nfr(f"{t}N-1", "Report generation time", target="< 30 s for 10k issues",
                actual="18 s", status=STATUS_MET, owner="System Team"),
            Nfr(f"{t}N-2", "Availability of the reporting service",
                target=">= 99.5 % per quarter", actual="99.7 %",
                status=STATUS_MET, owner="System Team"),
            Nfr(f"{t}N-3", "Peak concurrent report users", target="50 users",
                actual="42 users tested", status=STATUS_AT_RISK,
                owner=h.first,
                notes="Load test above 42 users pending new cluster."),
        ],
        runway=[
            RunwayItem(f"{t}RW-1", "Central data lake connection",
                       status=RUNWAY_IN_PLACE, owner="System Team"),
            RunwayItem(f"{t}RW-2", "Self-service test environment",
                       status=RUNWAY_BUILDING,
                       needed_by=reference + timedelta(days=40),
                       owner="System Team"),
        ])


def _second_nfr(reference: date, s: _Names,
                active: frozenset[str] = ALL_EVENTS) -> NfrRegister:
    """NFR/runway register of the second solution: with EVENT_SLO_BREACH one
    violated NFR and one overdue runway gap."""
    t = s.tag
    second = s.mid or s.first
    breach = EVENT_SLO_BREACH in active
    return NfrRegister(
        nfrs=[
            Nfr(f"{t}N-1", "API response time", target="p95 < 200 ms",
                actual="p95 = 340 ms" if breach else "p95 = 170 ms",
                status=STATUS_VIOLATED if breach else STATUS_MET,
                owner=s.first,
                notes="Regression since the vendor library update." if breach else ""),
            Nfr(f"{t}N-2", "Data retention compliance", target="Delete after 180 days",
                actual="Job active", status=STATUS_MET, owner="Shared Services"),
            Nfr(f"{t}N-3", "Recovery time objective", target="RTO < 4 h",
                actual="Not measured since failover test",
                status=STATUS_AT_RISK, owner=second),
        ],
        runway=[
            # 10 Tage überfällig: vor 14 Tagen noch nicht — im Delta-Briefing
            # taucht die Lücke als „newly overdue" auf (B2- + D2-Story).
            RunwayItem(f"{t}RW-1", "Automated failover for the sync service",
                       status=RUNWAY_GAP if breach else RUNWAY_BUILDING,
                       needed_by=reference - timedelta(days=10 if breach else -25),
                       owner=second,
                       notes="Overdue: needed before the last release." if breach else ""),
            RunwayItem(f"{t}RW-2", "Contract test suite against vendor API",
                       status=RUNWAY_BUILDING,
                       needed_by=reference + timedelta(days=30),
                       owner=s.first),
        ])


def _empty_registers() -> dict[str, object]:
    return {"risks": RiskRegister(), "nfr": NfrRegister(),
            "capabilities": CapabilityMap(),
            "dependencies": DependencyRegister(), "decisions": DecisionLog(),
            "slo": SloRegister(), "dora": DeliveryRegister(),
            "flow_problems": FlowProblemRegister(), "themes": ThemesRegister(),
            "solution_areas": SolutionAreaRegister(),
            "decision_points": DecisionPointRegister()}


def _anchor_registers(index: int, names: _Names, host: _Names,
                      second: _Names | None, reference: date,
                      active: frozenset[str]) -> dict[str, object]:
    """
    Story anchors of one solution by its position (E2: roles, not names).

    Position 0 hosts the outlier story (its cross-solution seam needs the
    ``second`` solution), position 1 the weak-source story (its seams point
    at ``host``); every further solution gets empty registers — the seeded
    base population (register_gen) fills them.
    """
    if index == 0:
        return {
            "risks": _host_risks(reference, names, active),
            "nfr": _host_nfr(reference, names),
            "capabilities": _host_capabilities(reference, names, active),
            "dependencies": _host_dependencies(reference, names, second, active),
            "decisions": _host_decisions(reference, names),
            "slo": _host_slo(reference, active),
            "dora": _host_delivery(reference, names, active),
            "flow_problems": _host_flow_problems(reference, names, active),
            "themes": _host_themes(names, active),
            "solution_areas": _host_solution_areas(reference, names, active),
            "decision_points": _host_decision_points(reference, names),
        }
    if index == 1:
        return {
            "risks": _second_risks(reference, names, active),
            "nfr": _second_nfr(reference, names, active),
            "capabilities": _second_capabilities(reference, names, active),
            "dependencies": _second_dependencies(reference, names, host, active),
            "decisions": _second_decisions(reference, names, active),
            "slo": _second_slo(reference, active),
            "dora": _second_delivery(reference, names, active),
            "flow_problems": _second_flow_problems(reference, names, active),
            "themes": _second_themes(names, active),
            "solution_areas": _second_solution_areas(reference, names),
            "decision_points": _second_decision_points(reference, names),
        }
    return _empty_registers()


_SAVERS: dict[str, Callable] = {
    "risks": save_risks, "nfr": save_nfr,
    "capabilities": save_capabilities, "dependencies": save_dependencies,
    "decisions": save_decisions, "slo": save_slo, "dora": save_delivery,
    "flow_problems": save_flow_problems, "themes": save_themes,
    "solution_areas": save_solution_areas,
    "decision_points": save_decision_points,
}

#: Legacy aliases of the returned path keys (flow_alpha, areas_beta, …).
_KEY_ALIASES = {"flow": "flow_problems", "areas": "solution_areas",
                "points": "decision_points"}


def _write_pi_config(path: Path, reference: date, window_days: int) -> None:
    quarters = []
    q_start = reference - timedelta(days=window_days)
    n = 1
    while q_start < reference:
        q_end = min(q_start + timedelta(days=90), reference)
        quarters.append({"name": f"PI {n}",
                         "from": q_start.isoformat(), "to": q_end.isoformat()})
        q_start = q_end + timedelta(days=1)
        n += 1
    path.write_text(json.dumps({"mode": "date", "intervals": quarters}, indent=2),
                    encoding="utf-8")


def _readme_text(spec: PortfolioSpec, story_data: Story, seed: int,
                 reference: date, scale: str,
                 stand_dates: list[date] | None = None,
                 sources_info: dict[str, dict[str, Any]] | None = None) -> str:
    """The README of one portfolio data room, told from structure and story."""
    first_art = spec.arts[0]
    workflow_label = {WORKFLOW_CLASSIC: "klassischer Workflow (Default-Pfad)",
                      WORKFLOW_STAGE_MAP: "eigene stage_map (Schema 2)"}
    lines = [
        f"# {spec.name} (generierter Demo-Datenraum)",
        "",
        f"Erzeugt mit `python -m testdata_generator --scenario portfolio` "
        f"(Seed {seed}, Referenzdatum {reference.isoformat()}, Skala {scale}, "
        f"Geschichte „{story_data.title}\").",
        "",
        "Direkt verwendbar: `python -m portfolio portfolio.json` bzw. die",
        "Solution-Configs einzeln. **Der Ordner ist ein Portfolio-Datenraum**:",
        "alle Pfade in den Configs sind relativ zur jeweiligen Config-Datei —",
        "der Ordner kann als Ganzes verschoben, kopiert oder gezippt werden.",
        "",
        "    structure.json · story.json  Struktur und Geschichte als Daten",
        "    portfolio.json            Einstieg (Portfolio)",
        "    solutions/<name>/         je Solution: solution.json,",
        "                              arts/ (IssueTimes/Transitions/CFD),",
        "                              registers/ (" + ", ".join(
            f"{r}.json" for r in REGISTER_NAMES[:4]) + ",",
        "                              " + ", ".join(
            f"{r}.json" for r in REGISTER_NAMES[4:]) + ")",
        "    workflows/  raw/  pi_config.json",
        "    snapshots/                snapshot_<nn>_<datum>.json je Stand, stands.json,",
        "                              snapshot_prev/now.json = die letzten beiden",
        "    deltas/                   delta_<nn>-<nn+1>.md/.html je Folgepaar",
        "    sources/<name>/           Provider-Rohdaten (Replay-Dateien im Systemformat)",
        "                              + sources-Configs je Solution",
        "",
        "## Struktur",
        "",
    ]
    for solution in spec.solutions:
        lines.append(f"- **{solution.display_name}** — "
                     f"{workflow_label[solution.workflow]}: "
                     + ", ".join(solution.member_names))
    lines += [
        "",
        "Die Register bestehen aus festen **Story-Ankern** (unten) plus",
        "einer seed-generierten Grundmenge; `--scale s|m|l` steuert deren",
        "Umfang je Solution (s = nur Anker, m = Standard, l = Stresstest).",
        "Die Anker und ihre Geschichten sind auf jeder Skala identisch.",
        "Die Statuswege der ARTs sind unordentlich wie in echten ARTs",
        "(Realismus 60: Sprünge, Abbrüche, Schleifen, Wiedereröffnung).",
        "Je ART lassen sich die Generator-Regler übersteuern (GUI-Dialog",
        "„ART-Profile…“ bzw. `--art-profiles datei.json`); Overrides gelten",
        "in beiden Delta-Ständen, alles andere behält seinen Story-Wert.",
        "",
        f"## Geschichte „{story_data.title}\" (story.json)",
        "",
    ]
    lines += [f"{s}" for s in story_data.summary]
    lines.append("")
    for event in story_data.events:
        if not event.enabled:
            lines.append(f"- **{event.event_id}** _(aus)_ {event.title}")
            continue
        last = story_data.stands
        if event.stand_from <= 1 and (event.stand_to is None or event.stand_to >= last):
            when = "in allen Ständen"
        elif event.stand_to is None or event.stand_to >= last:
            when = (f"ab Stand {event.stand_from:02d}" if event.stand_from < last
                    else "nur im letzten Stand")
        else:
            when = (f"Stand {event.stand_from:02d}" if event.stand_from == event.stand_to
                    else f"Stand {event.stand_from:02d} bis {event.stand_to:02d}")
        lines.append(f"- **{event.event_id}** {event.title} _({when})_  ")
        lines.append(f"  {event.effect}")
    if story_data.notices:
        lines += ["", "Hinweise der Rollenbindung:", ""]
        lines += [f"- {n}" for n in story_data.notices]
    if stand_dates:
        lines += ["", "## Stände", "",
                  f"{len(stand_dates)} Stände im Abstand von {STAND_INTERVAL_DAYS} Tagen "
                  f"— jeder Stand ein Snapshot, jedes Folgepaar ein fertiges "
                  f"Delta-Briefing. Die „jetzt\"-Ereignisse der Geschichte gelten ab "
                  f"dem letzten Stand; davor zeigt die Reihe die Lage davor "
                  f"(weniger Vorgänge, Register ohne die späten Wendungen).", ""]
        for k, day in enumerate(stand_dates, start=1):
            marker = ("  ← snapshot_now" if k == len(stand_dates)
                      else "  ← snapshot_prev" if k == len(stand_dates) - 1 else "")
            lines.append(f"- Stand {k:02d}: {day.isoformat()}"
                         f" (`snapshots/{_snapshot_name(k, day)}`){marker}")
        lines += ["", "Delta-Briefings: " + ", ".join(
            f"`deltas/delta_{k:02d}-{k + 1:02d}.html`" for k in range(1, len(stand_dates)))]
    if sources_info:
        lines += ["", "## Quellen (Provider-Rohdaten, Weg 2)", "",
                  "Je Solution liegen unter `sources/<name>/` die Rohdaten, wie die Systeme sie",
                  "liefern würden — Prometheus-Instant-Queries, GitHub-Deployments/PRs/Issues",
                  "oder GitLab-DORA-Tageswerte, SonarQube-Measures, eine SLO-CSV — als",
                  "Replay-Dateien, dazu die passenden `sources`-Configs. `python -m sources",
                  "fetch` läuft darauf ohne Netz (`\"replay\"` in der Config) und liefert, was",
                  "auch in `registers/` steht; GitHub-DORA kommt näherungsweise (Zählungen),",
                  "GitLab exakt. Pfade in den Configs gelten relativ zur Config-Datei.", ""]
        for key, info in sources_info.items():
            if not info.get("configs"):
                lines.append(f"- `{key}`: keine Register mit Einträgen — keine Rohdaten.")
                continue
            provider = info.get("dora_provider")
            lines.append(f"- `{key}`: " + ", ".join(sorted(info["configs"]))
                         + (f" (DORA über {provider})" if provider else ""))
        first = next((k for k, i in sources_info.items() if i.get("configs")), None)
        if first:
            lines += ["", "```bash",
                      f"python -m sources fetch --kind slo --config sources/{first}/slo_sources.json "
                      f"--output sources/{first}/fetched_slo.json",
                      f"python -m sources fetch --kind dora --config sources/{first}/dora_sources.json "
                      f"--output sources/{first}/fetched_dora.json",
                      f"python -m sources fetch --kind quality --config sources/{first}/quality_sources.json "
                      f"--output sources/{first}/fetched_quality.json",
                      "```"]
    lines += [
        "",
        "## Weitere Wege",
        "",
        "- **Delta-Briefing (D2)**: `snapshots/snapshot_prev.json` (Stand vor",
        "  14 Tagen) und `snapshots/snapshot_now.json` liegen bei —",
        "  `python -m portfolio --delta snapshots/snapshot_prev.json",
        "  snapshots/snapshot_now.json`; jedes andere Paar genauso.",
        "- **KI-Narration (D2 Teil 2)**: `--narrate mock` ergänzt das",
        "  Briefing um den gekennzeichneten Abschnitt „Narration (Entwurf)\"",
        "  — ohne Modell oder Installation (Attrappe); der Nachweis landet",
        "  in `llm_audit.jsonl`.",
        "- **Konferenzmappe**: `python -m portfolio portfolio.json --conference mappe.html`.",
        f"- **Export-Prüfung (Weg 2)**: `python -m get_data check raw/{first_art}_jira.json`;",
        "  die Roh-JSONs unter `raw/` sind zugleich Demo-Futter für get_data.",
        "- **Delivery-Register**: erzeugt/austauschbar über `python -m sources fetch`",
        "  (Provider: file, prometheus, github, gitlab, sonarqube — kombinierbar).",
        "",
    ]
    return "\n".join(lines)


def _snapshot_name(index: int, day: date) -> str:
    return f"snapshot_{index:02d}_{day.isoformat()}.json"


def write_stand_delta(snapshots_dir: Path, deltas_dir: Path, k: int,
                      lang: str = DEFAULT_LANG) -> tuple[Path, Path]:
    """
    Render the Delta-Briefing between stand ``k`` and ``k + 1`` of a data
    room (Markdown + HTML) into ``deltas/``; returns both paths.

    Reads the stand files through ``stands.json``.
    """
    import shutil  # noqa: F401  (kept local: the module avoids a top-level import)

    from portfolio.delta import compute_delta, delta_to_markdown, render_delta_html
    from portfolio.snapshot import load_snapshot

    index = json.loads((snapshots_dir / "stands.json").read_text(encoding="utf-8"))
    by_index = {int(s["index"]): snapshots_dir / s["file"] for s in index["stands"]}
    delta = compute_delta(load_snapshot(by_index[k]), load_snapshot(by_index[k + 1]))
    deltas_dir.mkdir(exist_ok=True)
    md = deltas_dir / f"delta_{k:02d}-{k + 1:02d}.md"
    html = deltas_dir / f"delta_{k:02d}-{k + 1:02d}.html"
    md.write_text(delta_to_markdown(delta), encoding="utf-8")
    html.write_text(render_delta_html(delta, lang=lang), encoding="utf-8")
    return md, html


def write_stands_index(snapshots_dir: Path, entries: list[tuple[int, date, str]]) -> Path:
    """Write ``snapshots/stands.json`` (schema 1) and return its path."""
    path = snapshots_dir / "stands.json"
    path.write_text(json.dumps({
        "schema": 1,
        "interval_days": STAND_INTERVAL_DAYS,
        "stands": [{"index": k, "as_of": day.isoformat(), "file": name}
                   for k, day, name in entries],
    }, indent=2) + "\n", encoding="utf-8")
    return path


def _build_stand_series(
    out: Path,
    spec: PortfolioSpec,
    seed: int,
    reference: date,
    window_days: int,
    scale: str,
    art_profiles: dict[str, dict] | None,
    stands: int,
    stand_dates: list[date],
    lang: str,
    log: Callable[[str], None],
    template: str = STORY_STANDARD,
    switches: dict[str, bool] | None = None,
    progress: ProgressHook | None = None,
) -> dict[str, Any]:
    """
    Freeze the N stands of the data room and render the N-1 Delta-Briefings.

    Stand N is the data room itself (as of ``reference``). Every earlier
    stand k is the same story (STAND_INTERVAL_DAYS × (N-k)) days younger:
    built into a temp folder with PREV_ISSUE_FACTOR**(N-k) of the issues
    and the registers in the state the story template prescribes for stand
    k, frozen as of its stand date, then discarded. snapshot_prev/now.json
    are copies of stands N-1 and N (the aliases the GUI, the tutorials and
    the continuation use).
    """
    import shutil
    import tempfile

    from portfolio.snapshot import build_snapshot, save_snapshot
    from portfolio.solution_config import load_solution_config

    snapshots_dir = out / "snapshots"
    deltas_dir = out / "deltas"
    log(f"  Stände-Reihe: {stands} Stände im {STAND_INTERVAL_DAYS}-Tage-Rhythmus ...")
    _emit(progress, "stands", "running", f"{stands} Stände")
    entries: list[tuple[int, date, str]] = []
    snapshot_paths: list[Path] = []
    for k, day in enumerate(stand_dates, start=1):
        name = _snapshot_name(k, day)
        target = snapshots_dir / name
        if k == stands:
            save_snapshot(target, build_snapshot(
                load_solution_config(out / "portfolio.json"), as_of=day,
                log=lambda m: None))
        else:
            with tempfile.TemporaryDirectory(prefix=f"scenario_stand{k:02d}_") as tmp:
                prev_paths = _build_portfolio(
                    Path(tmp), spec, seed=seed, reference=reference,
                    window_days=window_days, log=lambda m: None,
                    story=STORY_PREV, scale=scale, art_profiles=art_profiles,
                    stands=stands, lang=lang,
                    issue_scale=PREV_ISSUE_FACTOR ** (stands - k),
                    template=template, switches=switches, stand_index=k)
                save_snapshot(target, build_snapshot(
                    load_solution_config(prev_paths["portfolio"]), as_of=day,
                    log=lambda m: None))
        entries.append((k, day, name))
        snapshot_paths.append(target)
        log(f"    Stand {k:02d}: {day.isoformat()}")
    shutil.copyfile(snapshot_paths[-2], snapshots_dir / "snapshot_prev.json")
    shutil.copyfile(snapshot_paths[-1], snapshots_dir / "snapshot_now.json")
    stands_index = write_stands_index(snapshots_dir, entries)
    _emit(progress, "stands", "done", f"{stands} Stände, {stand_dates[0]} bis {stand_dates[-1]}")
    _emit(progress, "deltas", "running", f"{stands - 1} Folgepaare")
    deltas: list[tuple[Path, Path]] = []
    for k in range(1, stands):
        deltas.append(write_stand_delta(snapshots_dir, deltas_dir, k, lang))
    log(f"  Delta-Briefings: {len(deltas)} Folgepaare unter deltas/")
    _emit(progress, "deltas", "done", f"{len(deltas)} Delta-Briefings (md + html)")
    return {"stands": stands_index, "snapshots": snapshot_paths, "deltas": deltas}


def _generate_arts(
    out: Path,
    spec: PortfolioSpec,
    workflow_files: dict[str, Path],
    profiles: list[tuple[str, _ArtProfile]],
    seed: int,
    reference: date,
    window_days: int,
    log: Callable[[str], None],
) -> dict[str, list[Member]]:
    """
    Generate every ART's raw Jira export and its IssueTimes/Transitions/CFD
    workbooks; returns the solution members (paths relative to solution.json).
    """
    members: dict[str, list[Member]] = {s.key: [] for s in spec.solutions}
    for i, (solution_key, profile) in enumerate(profiles):
        wf_file = workflow_files[solution_key]
        workflow = parse_workflow(wf_file)

        to_date = reference - timedelta(days=profile.stale_days)
        from_date = to_date - timedelta(days=window_days - profile.stale_days)
        config = GeneratorConfig(
            project_key=profile.name.replace("-", ""),
            issue_count=profile.issue_count,
            from_date=from_date,
            to_date=to_date,
            completion_rate=profile.completion_rate,
            todo_rate=profile.todo_rate,
            backflow_prob=profile.backflow_prob,
            seed=seed + i,
            mean_cycle_days=profile.mean_cycle_days,
            std_cycle_days=profile.std_cycle_days,
            pattern=profile.pattern,
            pattern_strength=profile.pattern_strength,
            pi_duration_weeks=profile.pi_duration_weeks,
            realism=profile.realism,
        )
        raw = out / "raw" / f"{profile.name}_jira.json"
        raw.write_text(json.dumps(generate(workflow, config), indent=2),
                       encoding="utf-8")

        reference_dt = datetime.combine(
            to_date + timedelta(days=1), datetime.min.time(), tzinfo=UTC)
        records, unmapped = process_issues(raw, workflow, reference_dt=reference_dt)
        if unmapped:
            log(f"  WARNING [{profile.name}]: unmapped statuses {sorted(unmapped)}")

        arts_dir = out / "solutions" / solution_key / "arts"
        issue_times = arts_dir / f"{profile.name}_IssueTimes.xlsx"
        transitions = arts_dir / f"{profile.name}_Transitions.xlsx"
        write_issue_times(records, workflow, issue_times)
        write_transitions(records, transitions)
        cfd = ""
        if profile.write_cfd:
            write_cfd(records, workflow,
                      arts_dir / f"{profile.name}_CFD.xlsx",
                      reference_dt=reference_dt)
            cfd = f"arts/{profile.name}_CFD.xlsx"

        # Pfade RELATIV zur solution.json — der Datenraum ist verschiebbar.
        members[solution_key].append(Member(
            name=f"ART {profile.name}",
            issue_times=f"arts/{profile.name}_IssueTimes.xlsx",
            cfd=cfd,
            workflow=f"../../workflows/{solution_key}.txt",
            transitions=f"arts/{profile.name}_Transitions.xlsx",
        ))
        log(f"  {profile.name}: {len(records)} issues"
            f"{' (kein CFD, Datenstand -' + str(profile.stale_days) + 'd)' if profile.stale_days else ''}")
    return members


def _build_portfolio(
    out: Path,
    spec: PortfolioSpec,
    seed: int,
    reference: date,
    window_days: int,
    log: Callable[[str], None],
    story: str,
    scale: str,
    art_profiles: dict[str, dict] | None,
    stands: int = DEFAULT_STANDS,
    lang: str = DEFAULT_LANG,
    issue_scale: float | None = None,
    template: str = STORY_STANDARD,
    switches: dict[str, bool] | None = None,
    stand_index: int | None = None,
    progress: ProgressHook | None = None,
) -> dict[str, Any]:
    """
    Generate one portfolio's data room into ``out`` (see build_portfolio_scenario).

    ``stand_index`` is the stand this build represents (1..stands; None =
    the last). The story template and the switches decide which events are
    in force at that stand — profiles and register anchors follow them;
    ``story`` (STORY_PREV) only still scales the issues of earlier stands.
    """
    out.mkdir(parents=True, exist_ok=True)
    (out / "workflows").mkdir(exist_ok=True)
    (out / "raw").mkdir(exist_ok=True)
    (out / "snapshots").mkdir(exist_ok=True)
    for solution in spec.solutions:
        (out / "solutions" / solution.key / "arts").mkdir(parents=True, exist_ok=True)
        (out / "solutions" / solution.key / "registers").mkdir(parents=True,
                                                               exist_ok=True)

    workflow_files: dict[str, Path] = {}
    for solution in spec.solutions:
        wf_file = out / "workflows" / f"{solution.key}.txt"
        wf_file.write_text(_workflow_text(solution.workflow), encoding="utf-8")
        workflow_files[solution.key] = wf_file

    _emit(progress, "story", "running", spec.name)
    binding = bind_roles(spec)
    tags = _solution_tags(spec)
    story_data = story_for(template, binding, tags, stands, switches)
    this_stand = stands if stand_index is None else stand_index
    active = story_data.active_events(this_stand)
    _emit(progress, "story", "done",
          f"{spec.name}: {story_data.title}, {len(spec.solutions)} Solutions, "
          f"{len(spec.arts)} ARTs")
    _emit(progress, "arts", "running", f"{len(spec.arts)} ARTs")
    members = _generate_arts(
        out, spec, workflow_files,
        _profiles(story, art_profiles, spec, binding, issue_scale, active),
        seed, reference, window_days, log)
    _emit(progress, "arts", "done", f"{len(spec.arts)} Jira-Exporte, Arbeitsmappen")

    # Story-Anker (rollengebunden, Position 0 und 1) + seed-generierte
    # Grundmenge (register_gen, Skala S/M/L) je Solution.
    host_names = _names(spec.solutions[0], tags[spec.solutions[0].short])
    second_names = (_names(spec.solutions[1], tags[spec.solutions[1].short])
                    if len(spec.solutions) > 1 else None)
    _emit(progress, "registers", "running", f"{len(spec.solutions)} Solutions")
    register_paths: dict[str, Path] = {}
    registers_by_key: dict[str, dict[str, object]] = {}
    for index, solution in enumerate(spec.solutions):
        names = _names(solution, tags[solution.short])
        regs = _anchor_registers(index, names, host_names, second_names,
                                 reference, active)
        registers_by_key[solution.key] = regs
        populate_registers(
            regs, solution.key,
            art_names=[m.name for m in members[solution.key]],
            reference=reference, seed=seed, scale=scale,
            prev=(story == STORY_PREV), tag=names.tag)
        for name in REGISTER_NAMES:
            target = out / "solutions" / solution.key / "registers" / f"{name}.json"
            _SAVERS[name](target, regs[name])
            register_paths[f"{name}_{solution.key}"] = target

    _emit(progress, "registers", "done",
          f"{len(REGISTER_NAMES) * len(spec.solutions)} Register")
    _emit(progress, "configs", "running")
    _registers = {r: f"registers/{r}.json" for r in REGISTER_NAMES}
    solution_paths: dict[str, Path] = {}
    for solution in spec.solutions:
        cfg_path = out / "solutions" / solution.key / "solution.json"
        save_solution_config(cfg_path, SolutionConfig(
            name=solution.display_name, members=members[solution.key],
            from_date=reference - timedelta(days=window_days), to_date=reference,
            stage_map=(_BETA_STAGE_MAP if solution.workflow == WORKFLOW_STAGE_MAP
                       else None),
            **_registers))
        solution_paths[solution.key] = cfg_path

    portfolio_cfg = out / "portfolio.json"
    save_solution_config(portfolio_cfg, SolutionConfig(
        name=spec.name, kind=KIND_PORTFOLIO,
        members=[Member(name=s.display_name,
                        template=f"solutions/{s.key}/solution.json")
                 for s in spec.solutions],
        from_date=reference - timedelta(days=window_days), to_date=reference))

    pi_cfg = out / "pi_config.json"
    _write_pi_config(pi_cfg, reference, window_days)

    structure_path = out / "structure.json"
    save_structure(structure_path, Structure([spec]))
    story_path = out / "story.json"
    save_story(story_path, story_data)
    _emit(progress, "configs", "done",
          "portfolio.json, solution.json je Solution, pi_config, structure, story")
    if story == STORY_NOW:
        for notice in story_data.notices:
            log(f"  Hinweis: {notice}")

    stand_dates = [reference - timedelta(days=STAND_INTERVAL_DAYS * (stands - k))
                   for k in range(1, stands + 1)]
    sources_info: dict[str, dict[str, Any]] = {}
    if story == STORY_NOW:
        # E4: Provider-Rohdaten in Systemformaten + sources-Configs je Solution.
        _emit(progress, "sources", "running")
        sources_info = write_source_inputs(out, spec, registers_by_key, reference, log)
        _emit(progress, "sources", "done",
              f"{sum(1 for i in sources_info.values() if i.get('configs'))} Solutions mit Rohdaten")
    _emit(progress, "readme", "running")
    readme = out / "README.md"
    readme.write_text(_readme_text(spec, story_data, seed, reference, scale,
                                   stand_dates if story == STORY_NOW else [],
                                   sources_info),
                      encoding="utf-8")
    _emit(progress, "readme", "done", "README.md")

    snapshot_prev = out / "snapshots" / "snapshot_prev.json"
    snapshot_now = out / "snapshots" / "snapshot_now.json"
    series: dict[str, Any] = {"stands": None, "snapshots": [], "deltas": []}
    if story == STORY_NOW:
        series = _build_stand_series(
            out, spec, seed, reference, window_days, scale, art_profiles,
            stands, stand_dates, lang, log, template, switches, progress)

    paths: dict[str, Any] = {
        "portfolio": portfolio_cfg, "pi_config": pi_cfg, "readme": readme,
        "structure": structure_path, "story": story_path,
        "snapshot_prev": snapshot_prev, "snapshot_now": snapshot_now,
        "stands": series["stands"], "snapshots": series["snapshots"],
        "deltas": series["deltas"],
        "sources": sources_info,
        "solutions": solution_paths,
    }
    for key, cfg_path in solution_paths.items():
        paths[f"solution_{key}"] = cfg_path
        for name in REGISTER_NAMES:
            paths[f"{name}_{key}"] = register_paths[f"{name}_{key}"]
        for alias, name in _KEY_ALIASES.items():
            paths[f"{alias}_{key}"] = register_paths[f"{name}_{key}"]
    return paths


def build_portfolio_scenario(
    output_dir: Path,
    seed: int = 42,
    reference: date | None = None,
    window_days: int = 365,
    log: Callable[[str], None] = print,
    story: str = STORY_NOW,
    scale: str = DEFAULT_SCALE,
    art_profiles: dict[str, dict] | None = None,
    structure: Structure | None = None,
    stands: int = DEFAULT_STANDS,
    lang: str = DEFAULT_LANG,
    template: str = STORY_STANDARD,
    switches: dict[str, bool] | None = None,
    progress: ProgressHook | None = None,
) -> dict[str, Any]:
    """
    Generate the complete demo data room into ``output_dir``.

    Args:
        output_dir:  Target directory (created if missing).
        seed:        Base RNG seed; each ART uses seed + index, so the whole
                     scenario is reproducible for a fixed reference date.
        reference:   End of the data window (default: today). The window
                     spans ``window_days`` back from here; the weak source's
                     window ends ``stale_days`` earlier.
        window_days: Length of the data window in days.
        log:         Progress callback.
        story:       STORY_NOW (default) builds the current state including
                     the two Delta-Briefing snapshots; STORY_PREV builds the
                     same world two weeks earlier (used internally for the
                     prev snapshot — no snapshots of its own).
        scale:       Register volume per solution ("s", "m", "l").
        art_profiles: Per-ART generator overrides (see apply_art_overrides).
        structure:   The data-room structure (E2a). None = the standard
                     template (1 portfolio · 2 solutions · 3 ARTs each),
                     which yields exactly the demo portfolio of before.
        stands:      Number of stands in the series (E3; MIN_STANDS to
                     MAX_STANDS, default DEFAULT_STANDS), two weeks apart,
                     the last one on ``reference``; every consecutive pair
                     gets a rendered Delta-Briefing under deltas/.
        lang:        Language of the rendered Delta-Briefing pages.
        template:    Story template (E2, Schnitt 2): "calm", "standard",
                     "escalation" or "recovery" — decides which events the
                     stands show and when they switch on or off.
        switches:    Per-event overrides of the template ({"E3": False}).
        progress:    Step hook (step id, "running"|"done", detail) — the UI's
                     progress list; None = none.

    Returns:
        One portfolio: the key output paths — "portfolio", "pi_config",
        "readme", "structure", "story", "snapshot_prev", "snapshot_now",
        "stands" (stands.json), "snapshots" (one path per stand), "deltas"
        ([(md, html)] per consecutive pair),
        "solutions" ({key: solution.json}), plus "solution_<key>" and
        "<register>_<key>" for every solution (aliases flow_/areas_/points_).
        Several portfolios: "structure", "readme" and "portfolios"
        ({key: the per-portfolio dict above}); each portfolio lives in its
        own sub-folder and is a complete data room by itself.

    Raises:
        ValueError: invalid structure (see structure.validate), a stand
            count outside MIN_STANDS..MAX_STANDS, or an unknown template.
    """
    reference = reference or date.today()
    out = Path(output_dir)
    structure = structure or structure_template(TEMPLATE_STANDARD)
    validate(structure)
    if not MIN_STANDS <= stands <= MAX_STANDS:
        raise ValueError(f"stands must be {MIN_STANDS}..{MAX_STANDS}, got {stands}.")
    if template not in STORY_TEMPLATES:
        raise ValueError(f"Unknown story template '{template}' — expected one of "
                         f"{', '.join(STORY_TEMPLATES)}.")
    stand_index = stands - 1 if story == STORY_PREV else None

    if len(structure.portfolios) == 1:
        paths = _build_portfolio(out, structure.portfolios[0], seed, reference,
                                 window_days, log, story, scale, art_profiles,
                                 stands=stands, lang=lang, template=template,
                                 switches=switches, stand_index=stand_index,
                                 progress=progress)
        log(f"Szenario komplett: {out}")
        return paths

    out.mkdir(parents=True, exist_ok=True)
    per_portfolio: dict[str, dict[str, Any]] = {}
    for spec in structure.portfolios:
        log(f"Portfolio {spec.name} -> {spec.key}/")
        # Overrides are keyed by ART short name; each portfolio knows only its own.
        own = {k: v for k, v in (art_profiles or {}).items() if k in spec.arts} or None
        per_portfolio[spec.key] = _build_portfolio(
            out / spec.key, spec, seed, reference, window_days, log, story,
            scale, own, stands=stands, lang=lang, template=template,
            switches=switches, stand_index=stand_index, progress=progress)
    structure_path = out / "structure.json"
    save_structure(structure_path, structure)
    readme = out / "README.md"
    readme.write_text("\n".join([
        "# Demo-Datenraum mit mehreren Portfolios",
        "",
        f"Erzeugt mit `python -m testdata_generator --scenario portfolio` "
        f"(Seed {seed}, Referenzdatum {reference.isoformat()}, "
        f"{structure.describe()}).",
        "",
        "Jeder Unterordner ist ein vollständiger Portfolio-Datenraum mit",
        "eigener `portfolio.json`, eigenen Ständen und eigener README:",
        "",
    ] + [f"- `{spec.key}/` — {spec.name}: "
         + ", ".join(s.display_name for s in spec.solutions)
         for spec in structure.portfolios]
      + ["", "Ein Lagebild über mehrere Portfolios hinweg ist heute kein",
         "Feature; die Daten dafür liegen hier bereits nebeneinander.", ""]),
        encoding="utf-8")
    log(f"Szenario komplett: {out} ({structure.describe()})")
    return {"structure": structure_path, "readme": readme,
            "portfolios": per_portfolio}
