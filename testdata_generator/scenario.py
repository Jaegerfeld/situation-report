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
from .story import (
    ROLE_OUTLIER_ART,
    ROLE_WEAK_SOURCE_ART,
    WHEN_NOW,
    RoleBinding,
    Story,
    bind_roles,
    save_story,
    standard_story,
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
    ``story=STORY_PREV`` yields the same world two weeks earlier for the
    Delta-Briefing demo (D2): fewer issues per ART (88 % of the possibly
    overridden count), and the weak source's data gaps were smaller back
    then (confidence medium — the decay to low is part of the story;
    skipped when todo_rate is overridden).
    """
    portfolio = portfolio or structure_template(TEMPLATE_STANDARD).portfolios[0]
    binding = binding or bind_roles(portfolio)
    outlier = binding.art(ROLE_OUTLIER_ART)
    weak = binding.art(ROLE_WEAK_SOURCE_ART)
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
                # Date), kein CFD, Datenstand 60 Tage alt (A1-Ampel low).
                profile = _ArtProfile(art, wf, mean_cycle_days=15,
                                      completion_rate=0.15, todo_rate=0.8,
                                      stale_days=60, write_cfd=False,
                                      issue_count=60)
            else:
                profile = _ArtProfile(
                    art, wf,
                    mean_cycle_days=_CYCLE_POOL[(2 * j + i) % len(_CYCLE_POOL)])
            base.append((solution.key, profile))
    merged = apply_art_overrides(base, art_profiles)
    if story != STORY_PREV:
        return merged
    result: list[tuple[str, _ArtProfile]] = []
    for solution_key, profile in merged:
        updates: dict = {"issue_count": int(profile.issue_count * 0.88)}
        if (weak is not None and profile.name == weak
                and "todo_rate" not in (art_profiles or {}).get(weak, {})):
            updates["todo_rate"] = 0.45
        result.append((solution_key,
                       dataclasses.replace(profile, **updates)))
    return result


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


def _host_risks(reference: date, h: _Names) -> RiskRegister:
    """ROAM register of the host solution: healthy spread, one aging owned risk."""
    t = h.tag
    return RiskRegister(risks=[
        Risk(f"{t}R-1", "Test environment for PI 4 not ordered yet",
             ROAM_OWNED, owner="System Team", impact=IMPACT_HIGH,
             status_since=reference - timedelta(days=45),
             notes="Aging: owned for over a month without visible movement."),
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
                  story: str = STORY_NOW) -> RiskRegister:
    """
    ROAM register of the second solution: the second aging owned risk lives here.

    In the prev story (two weeks earlier), {tag}R-2 does not exist yet — it
    shows up as a *new* risk in the Delta-Briefing demo.
    """
    t = s.tag
    risks = [
        Risk(f"{t}R-1", f"Data quality of {s.last} blocks solution reporting",
             ROAM_OWNED, owner=s.last, impact=IMPACT_HIGH,
             status_since=reference - timedelta(days=50),
             notes="Aging: matches the weak-source story of this scenario."),
        Risk(f"{t}R-3", "Vendor API rate limits during nightly sync",
             ROAM_ACCEPTED, owner=s.first, impact=IMPACT_MEDIUM,
             status_since=reference - timedelta(days=15)),
        Risk(f"{t}R-4", "Duplicate effort with platform team clarified",
             ROAM_RESOLVED, owner=s.mid or s.first, impact=IMPACT_LOW,
             status_since=reference - timedelta(days=12)),
    ]
    if story != STORY_PREV:
        risks.insert(1, Risk(
            f"{t}R-2", "Security review for release milestone not scheduled",
            ROAM_MITIGATED, owner="Shared Services", impact=IMPACT_HIGH,
            status_since=reference - timedelta(days=7),
            notes="Interim: external reviewer booked for next sprint."))
    return RiskRegister(risks=risks)


def _host_capabilities(reference: date, h: _Names) -> CapabilityMap:
    """Capability map of the host solution: solid, one uncovered capability."""
    t = h.tag
    return CapabilityMap(capabilities=[
        Capability(f"{t}C-1", "Order management", HEALTH_HEALTHY,
                   arts=_uniq([h.first, h.mid or h.first]), owner=h.first,
                   assessed_on=reference - timedelta(days=14)),
        Capability(f"{t}C-2", "Billing & invoicing", HEALTH_AT_RISK,
                   arts=[h.last], owner=h.last,
                   assessed_on=reference - timedelta(days=14),
                   notes="Depends on the outlier ART's delivery pace."),
        # Uncovered: business value nobody delivers — the ARTs cell is flagged.
        Capability(f"{t}C-3", "Partner self-service", HEALTH_HEALTHY,
                   arts=[], owner="System Team",
                   assessed_on=reference - timedelta(days=45),
                   notes="Planned; no ART assigned yet."),
    ])


def _second_capabilities(reference: date, s: _Names) -> CapabilityMap:
    """Capability map of the second solution: the critical capability lives here."""
    t = s.tag
    return CapabilityMap(capabilities=[
        Capability(f"{t}C-1", "Data insights & reporting", HEALTH_CRITICAL,
                   arts=[s.last], owner=s.last,
                   assessed_on=reference - timedelta(days=7),
                   notes="Matches the weak-source story: data quality blocks it."),
        Capability(f"{t}C-2", "Customer onboarding", HEALTH_HEALTHY,
                   arts=_uniq([s.first, s.mid or s.first]), owner=s.first,
                   assessed_on=reference - timedelta(days=7)),
        Capability(f"{t}C-3", "Payment processing", HEALTH_HEALTHY,
                   arts=[s.mid or s.first], owner=s.mid or s.first,
                   assessed_on=reference - timedelta(days=7)),
    ])


def _host_themes(h: _Names, story: str = STORY_NOW) -> ThemesRegister:
    """
    Themes/roadmap of the host solution: one orphan theme, one zombie epic.

    Prev story (Delta demo): EP-{tag}9 still had its theme two weeks ago —
    losing the strategic home is one of the 'updated roadmaps' changes.
    """
    prev = story == STORY_PREV
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
                 "Y1", theme=f"T-{t}1"),
            # Die Zombie-Initiative: im Prev-Stand noch mit Theme.
            Epic(f"EP-{t}9", "Legacy portal rewrite", h.last,
                 "Y1", theme=f"T-{t}1" if prev else ""),
        ],
    )


def _second_themes(s: _Names, story: str = STORY_NOW) -> ThemesRegister:
    """
    Themes/roadmap of the second solution.

    Prev story: the data-quality epic was still parked in P2 — pulling it
    into P1 is the second 'updated roadmaps' change.
    """
    prev = story == STORY_PREV
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
                 "P2" if prev else "P1", theme=f"T-{t}1",
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
                         story: str = STORY_NOW) -> SolutionAreaRegister:
    """
    Solution areas of the host: the same seam first × last ART opened a third
    time for the same topic — the EA signal (P5). The third opening is only
    in the now stand, so the delta documents the signal coming on.
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
    if story == STORY_NOW:
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


def _host_flow_problems(reference: date, h: _Names) -> FlowProblemRegister:
    """Flow problems of the host: one has survived three conferences."""
    t = h.tag
    return FlowProblemRegister(problems=[
        # Das Workshop-Muster: geloggt, nie mitigiert, taucht wieder auf.
        FlowProblem(f"FP-{t}1", "Test-environment provisioning takes weeks",
                    FLOW_OPEN,
                    value_streams=list(h.arts),
                    source="VSC", owner="System Team",
                    raised_on=reference - timedelta(days=140),
                    conferences=3,
                    notes="Survivor: raised at three conferences, still open."),
        FlowProblem(f"FP-{t}2", "Review bottleneck at architecture board",
                    FLOW_COMMITTED,
                    value_streams=[h.mid or h.first],
                    source=h.mid or h.first, owner="System Team",
                    raised_on=reference - timedelta(days=40),
                    conferences=1,
                    resolution_commitment="Second review slot per week",
                    follow_up_pi="PI 5"),
    ])


def _second_flow_problems(reference: date, s: _Names) -> FlowProblemRegister:
    """Flow problems of the second solution: the weak source blocks two streams."""
    t = s.tag
    return FlowProblemRegister(problems=[
        FlowProblem(f"FP-{t}1",
                    f"{s.plain_last} export quality blocks solution reporting",
                    FLOW_OPEN,
                    value_streams=_uniq([s.first, s.last]),
                    source="VSC", owner=s.last,
                    raised_on=reference - timedelta(days=200),
                    conferences=4,
                    notes="Cross-VS survivor: matches the weak-source story."),
        FlowProblem(f"FP-{t}2", "Shared staging window conflicts",
                    FLOW_RESOLVED,
                    value_streams=_uniq([s.first, s.mid or s.first]),
                    source=s.first, owner=s.mid or s.first,
                    raised_on=reference - timedelta(days=90),
                    conferences=2,
                    resolution_commitment="Calendar-based slot booking"),
    ])


def _host_slo(reference: date) -> SloRegister:
    """SLOs of the host solution: healthy, one budget running low."""
    src = "demo-scenario"
    at = reference.isoformat()
    return SloRegister(records=[
        SloRecord("Order API", "p95 latency < 200 ms", 99.9, sli_pct=99.97,
                  source=src, fetched_at=at),
        # Budget fast aufgebraucht: SLI knapp ueber Ziel -> at_risk.
        SloRecord("Checkout", "availability", 99.5, sli_pct=99.55,
                  source=src, fetched_at=at),
        SloRecord("Search", "p99 latency < 800 ms", 99.0, sli_pct=99.8,
                  source=src, fetched_at=at),
    ])


def _second_slo(reference: date) -> SloRegister:
    """SLOs of the second solution: the sync service has burned its budget."""
    src = "demo-scenario"
    at = reference.isoformat()
    return SloRegister(records=[
        # Die Geschichte: der Sync-Dienst (Umfeld der schwachen Quelle)
        # reisst sein SLO.
        SloRecord("Order Sync API", "availability", 99.5, sli_pct=99.1,
                  source=src, fetched_at=at),
        SloRecord("Reporting", "p95 latency < 500 ms", 99.0, sli_pct=99.6,
                  source=src, fetched_at=at),
    ])


def _host_delivery(reference: date, h: _Names) -> DeliveryRegister:
    """Delivery health of the host: solid, the outlier ships slowly."""
    src = "demo-scenario"
    at = reference.isoformat()
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
        dora.append(DoraRecord(h.last, deployments_per_day=0.05,
                               lead_time_hours=520.0, change_failure_rate_pct=14.0,
                               time_to_restore_hours=20.0, source=src,
                               fetched_at=at))
    quality = [
        QualityRecord(h.first, coverage_pct=78.0,
                      maintainability="A", critical_issues=0,
                      source=src, fetched_at=at),
    ]
    if h.pairs_ok:
        quality.append(QualityRecord(h.last, coverage_pct=55.0,
                                     maintainability="C", critical_issues=2,
                                     source=src, fetched_at=at))
    return DeliveryRegister(dora=dora, quality=quality)


def _second_delivery(reference: date, s: _Names) -> DeliveryRegister:
    """Delivery health of the second solution: the weak source is low tier."""
    src = "demo-scenario"
    at = reference.isoformat()
    dora = []
    if s.pairs_ok:
        dora.append(DoraRecord(s.first, deployments_per_day=0.9,
                               lead_time_hours=30.0, change_failure_rate_pct=6.0,
                               time_to_restore_hours=3.0, source=src,
                               fetched_at=at))
    # Die Geschichte: die schwache Quelle auch im Delivery-Bild low.
    dora.append(DoraRecord(s.last, deployments_per_day=0.02,
                           lead_time_hours=800.0, change_failure_rate_pct=38.0,
                           time_to_restore_hours=30.0, source=src, fetched_at=at))
    return DeliveryRegister(
        dora=dora,
        quality=[
            QualityRecord(s.last, coverage_pct=31.0,
                          maintainability="D", critical_issues=7,
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


def _second_decisions(reference: date, s: _Names) -> DecisionLog:
    """Decision log of the second solution: the overdue open assumption lives here."""
    t = s.tag
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
                 ASSUMPTION_OPEN, owner=s.last,
                 logged_on=reference - timedelta(days=70),
                 review_by=reference - timedelta(days=10),
                 notes="Review due: matches the weak-source story."),
    ])


def _host_dependencies(
    reference: date, h: _Names, o: _Names | None, story: str = STORY_NOW
) -> DependencyRegister:
    """
    Dependencies of the host: the overdue blocked one lives here.

    In the prev story, {tag}D-1 was still at risk — the escalation to blocked
    is the status transition the Delta-Briefing demo shows. {tag}D-4 is the
    second seam towards the second solution and carries the same idea for
    the decision-point indicator: it was on track two weeks ago. Without a
    second solution (``o`` None) that seam does not exist.
    """
    t = h.tag
    deps: list[Dependency] = []
    if h.pairs_ok:
        # Die Geschichte: der Ausreißer liefert nicht — blockiert und
        # überfällig, springt in der Heatmap rot an.
        deps.append(Dependency(
            f"{t}D-1", "Billing API contract for order flow",
            from_art=h.first, to_art=h.last,
            status=DEP_AT_RISK if story == STORY_PREV else DEP_BLOCKED,
            due=reference - timedelta(days=15),
            notes="Overdue: matches the outlier story of this scenario."))
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
        deps.append(Dependency(
            f"{t}D-4", f"Customer master data feed for {o.short} reporting",
            from_art=h.first, to_art=o.mid or o.last,
            status=DEP_ON_TRACK if story == STORY_PREV else DEP_AT_RISK,
            due=reference - timedelta(days=35),
            notes=f"Cross-solution seam towards {o.solution}."))
    return DependencyRegister(dependencies=deps)


def _second_dependencies(
    reference: date, s: _Names, o: _Names, story: str = STORY_NOW
) -> DependencyRegister:
    """
    Dependencies of the second solution: the seam towards the host lives here.

    Together with the host's {tag}D-4 these make the decision point
    demonstrable: the pressure between the two value streams rises visibly
    between the two stands, while every single train looks unremarkable on
    its own.
    """
    t = s.tag
    deps = [
        # Cross-Solution-Integration: die zweite Solution braucht die
        # Order-Events des Hosts — sichtbar nur im Portfolio-Report.
        Dependency(f"{t}D-1", "Order events feed for reporting",
                   from_art=s.first, to_art=o.first,
                   status=DEP_AT_RISK, due=reference + timedelta(days=10),
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
        status=DEP_AT_RISK if story == STORY_PREV else DEP_BLOCKED,
        due=reference - timedelta(days=12),
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


def _second_nfr(reference: date, s: _Names) -> NfrRegister:
    """NFR/runway register of the second solution: one violated NFR, one overdue gap."""
    t = s.tag
    second = s.mid or s.first
    return NfrRegister(
        nfrs=[
            Nfr(f"{t}N-1", "API response time", target="p95 < 200 ms",
                actual="p95 = 340 ms", status=STATUS_VIOLATED,
                owner=s.first,
                notes="Regression since the vendor library update."),
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
                       status=RUNWAY_GAP,
                       needed_by=reference - timedelta(days=10),
                       owner=second,
                       notes="Overdue: needed before the last release."),
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
                      story: str) -> dict[str, object]:
    """
    Story anchors of one solution by its position (E2: roles, not names).

    Position 0 hosts the outlier story (its cross-solution seam needs the
    ``second`` solution), position 1 the weak-source story (its seams point
    at ``host``); every further solution gets empty registers — the seeded
    base population (register_gen) fills them.
    """
    if index == 0:
        return {
            "risks": _host_risks(reference, names),
            "nfr": _host_nfr(reference, names),
            "capabilities": _host_capabilities(reference, names),
            "dependencies": _host_dependencies(reference, names, second, story),
            "decisions": _host_decisions(reference, names),
            "slo": _host_slo(reference),
            "dora": _host_delivery(reference, names),
            "flow_problems": _host_flow_problems(reference, names),
            "themes": _host_themes(names, story),
            "solution_areas": _host_solution_areas(reference, names, story),
            "decision_points": _host_decision_points(reference, names),
        }
    if index == 1:
        return {
            "risks": _second_risks(reference, names, story),
            "nfr": _second_nfr(reference, names),
            "capabilities": _second_capabilities(reference, names),
            "dependencies": _second_dependencies(reference, names, host, story),
            "decisions": _second_decisions(reference, names),
            "slo": _second_slo(reference),
            "dora": _second_delivery(reference, names),
            "flow_problems": _second_flow_problems(reference, names),
            "themes": _second_themes(names, story),
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
                 reference: date, scale: str) -> str:
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
        "    snapshots/                snapshot_prev.json, snapshot_now.json",
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
        when = ("nur im jetzigen Stand" if event.when == WHEN_NOW
                else "in beiden Ständen")
        lines.append(f"- **{event.event_id}** {event.title} _({when})_  ")
        lines.append(f"  {event.effect}")
    if story_data.notices:
        lines += ["", "Hinweise der Rollenbindung:", ""]
        lines += [f"- {n}" for n in story_data.notices]
    lines += [
        "",
        "## Weitere Wege",
        "",
        "- **Delta-Briefing (D2)**: `snapshots/snapshot_prev.json` (Stand vor",
        "  14 Tagen) und `snapshots/snapshot_now.json` liegen bei —",
        "  `python -m portfolio --delta snapshots/snapshot_prev.json",
        "  snapshots/snapshot_now.json`.",
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
) -> dict[str, Any]:
    """Generate one portfolio's data room into ``out`` (see build_portfolio_scenario)."""
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

    binding = bind_roles(spec)
    tags = _solution_tags(spec)
    members: dict[str, list[Member]] = {s.key: [] for s in spec.solutions}
    for i, (solution_key, profile) in enumerate(
            _profiles(story, art_profiles, spec, binding)):
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

    # Story-Anker (rollengebunden, Position 0 und 1) + seed-generierte
    # Grundmenge (register_gen, Skala S/M/L) je Solution.
    host_names = _names(spec.solutions[0], tags[spec.solutions[0].short])
    second_names = (_names(spec.solutions[1], tags[spec.solutions[1].short])
                    if len(spec.solutions) > 1 else None)
    register_paths: dict[str, Path] = {}
    for index, solution in enumerate(spec.solutions):
        names = _names(solution, tags[solution.short])
        regs = _anchor_registers(index, names, host_names, second_names,
                                 reference, story)
        populate_registers(
            regs, solution.key,
            art_names=[m.name for m in members[solution.key]],
            reference=reference, seed=seed, scale=scale,
            prev=(story == STORY_PREV), tag=names.tag)
        for name in REGISTER_NAMES:
            target = out / "solutions" / solution.key / "registers" / f"{name}.json"
            _SAVERS[name](target, regs[name])
            register_paths[f"{name}_{solution.key}"] = target

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
    story_data = standard_story(binding, tags)
    story_path = out / "story.json"
    save_story(story_path, story_data)
    for notice in story_data.notices:
        log(f"  Hinweis: {notice}")

    readme = out / "README.md"
    readme.write_text(_readme_text(spec, story_data, seed, reference, scale),
                      encoding="utf-8")

    snapshot_prev = out / "snapshots" / "snapshot_prev.json"
    snapshot_now = out / "snapshots" / "snapshot_now.json"
    if story == STORY_NOW:
        # Delta-Briefing-Demo (D2): denselben Bau als Prev-Variante in einen
        # Temp-Ordner legen, beide Staende einfrieren, Temp verwerfen.
        import tempfile

        from portfolio.snapshot import build_snapshot, save_snapshot
        from portfolio.solution_config import load_solution_config

        log("  Delta-Briefing: Snapshots (prev/now) werden erzeugt ...")
        save_snapshot(snapshot_now, build_snapshot(
            load_solution_config(portfolio_cfg), as_of=reference,
            log=lambda m: None))
        with tempfile.TemporaryDirectory(prefix="scenario_prev_") as tmp:
            prev_paths = _build_portfolio(
                Path(tmp), spec, seed=seed, reference=reference,
                window_days=window_days, log=lambda m: None,
                story=STORY_PREV, scale=scale, art_profiles=art_profiles)
            save_snapshot(snapshot_prev, build_snapshot(
                load_solution_config(prev_paths["portfolio"]),
                as_of=reference - timedelta(days=14), log=lambda m: None))

    paths: dict[str, Any] = {
        "portfolio": portfolio_cfg, "pi_config": pi_cfg, "readme": readme,
        "structure": structure_path, "story": story_path,
        "snapshot_prev": snapshot_prev, "snapshot_now": snapshot_now,
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

    Returns:
        One portfolio: the key output paths — "portfolio", "pi_config",
        "readme", "structure", "story", "snapshot_prev", "snapshot_now",
        "solutions" ({key: solution.json}), plus "solution_<key>" and
        "<register>_<key>" for every solution (aliases flow_/areas_/points_).
        Several portfolios: "structure", "readme" and "portfolios"
        ({key: the per-portfolio dict above}); each portfolio lives in its
        own sub-folder and is a complete data room by itself.

    Raises:
        ValueError: invalid structure (see structure.validate).
    """
    reference = reference or date.today()
    out = Path(output_dir)
    structure = structure or structure_template(TEMPLATE_STANDARD)
    validate(structure)

    if len(structure.portfolios) == 1:
        paths = _build_portfolio(out, structure.portfolios[0], seed, reference,
                                 window_days, log, story, scale, art_profiles)
        log(f"Szenario komplett: {out}")
        return paths

    out.mkdir(parents=True, exist_ok=True)
    per_portfolio: dict[str, dict[str, Any]] = {}
    for spec in structure.portfolios:
        log(f"Portfolio {spec.name} -> {spec.key}/")
        per_portfolio[spec.key] = _build_portfolio(
            out / spec.key, spec, seed, reference, window_days, log, story,
            scale, art_profiles)
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
