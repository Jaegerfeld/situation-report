# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       02.09.2026
# Geändert:       02.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Portfolio-Szenario: erzeugt ein vollständiges, konsistentes Demo-Portfolio
#   (2 Solutions × 3 ARTs) mit allen Artefakten der Kette — Workflow-Dateien,
#   Jira-JSON (Generator), IssueTimes/CFD/Transitions (transform_data),
#   Solution-Configs (eine mit stage_map, Schema 2), Portfolio-Config und
#   PI-Config. Deterministisch über Seed; die Daten liegen relativ zu einem
#   Referenzdatum (Standard: heute), damit die Konfidenz-Ampel des
#   Portfolio-Reports nicht alles als veraltet einstuft.
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


#: Je ART übersteuerbare Profil-Felder (GUI-Dialog, CLI --art-profiles).
ART_PROFILE_FIELDS = ("issue_count", "mean_cycle_days", "std_cycle_days",
                      "completion_rate", "todo_rate", "backflow_prob",
                      "pattern", "pattern_strength", "pi_duration_weeks")

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
    if key == "pattern_strength":
        if not 0 <= number <= 100:
            raise ValueError(
                f"pattern_strength must be 0–100, got {value!r}.")
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


def _profiles(
    story: str = STORY_NOW,
    art_profiles: dict[str, dict] | None = None,
) -> list[tuple[str, _ArtProfile]]:
    """
    (solution key, profile) pairs for the six demo ARTs.

    ``art_profiles`` overrides individual fields per ART (see
    apply_art_overrides) — explicit overrides win in both stands.
    ``story=STORY_PREV`` yields the same world two weeks earlier for the
    Delta-Briefing demo (D2): fewer issues per ART (the throughput
    since; 88 % of the possibly overridden count), and Beta-3's data
    gaps were smaller back then (confidence medium — the decay to low is
    part of the story; skipped when todo_rate is overridden).
    """
    base = [
        ("alpha", _ArtProfile("Alpha-1", _WORKFLOW_ALPHA,
                              mean_cycle_days=12)),
        ("alpha", _ArtProfile("Alpha-2", _WORKFLOW_ALPHA,
                              mean_cycle_days=16)),
        # Der Ausreißer: Cycle Time ~3x der Schwester-ARTs (A3-Hervorhebung).
        ("alpha", _ArtProfile("Alpha-3", _WORKFLOW_ALPHA,
                              mean_cycle_days=45)),
        ("beta", _ArtProfile("Beta-1", _WORKFLOW_BETA, mean_cycle_days=14)),
        ("beta", _ArtProfile("Beta-2", _WORKFLOW_BETA, mean_cycle_days=18)),
        # Die schwache Quelle: kaum begonnene Issues (kein First Date), kein
        # CFD, Datenstand 60 Tage alt (A1-Ampel low, Abdeckung < 100 %).
        ("beta", _ArtProfile("Beta-3", _WORKFLOW_BETA, mean_cycle_days=15,
                             completion_rate=0.15, todo_rate=0.8,
                             stale_days=60, write_cfd=False,
                             issue_count=60)),
    ]
    merged = apply_art_overrides(base, art_profiles)
    if story != STORY_PREV:
        return merged
    result: list[tuple[str, _ArtProfile]] = []
    for solution_key, profile in merged:
        updates: dict = {"issue_count": int(profile.issue_count * 0.88)}
        if (profile.name == "Beta-3"
                and "todo_rate" not in (art_profiles or {}).get(
                    "Beta-3", {})):
            updates["todo_rate"] = 0.45
        result.append((solution_key,
                       dataclasses.replace(profile, **updates)))
    return result


def _alpha_risks(reference: date) -> RiskRegister:
    """ROAM register of Solution Alpha: healthy spread, one aging owned risk."""
    return RiskRegister(risks=[
        Risk("AR-1", "Test environment for PI 4 not ordered yet",
             ROAM_OWNED, owner="System Team", impact=IMPACT_HIGH,
             status_since=reference - timedelta(days=45),
             notes="Aging: owned for over a month without visible movement."),
        Risk("AR-2", "Key supplier interface spec still in draft",
             ROAM_OWNED, owner="ART Alpha-2", impact=IMPACT_MEDIUM,
             status_since=reference - timedelta(days=10)),
        Risk("AR-3", "Legacy migration effort underestimated",
             ROAM_MITIGATED, owner="ART Alpha-3", impact=IMPACT_MEDIUM,
             status_since=reference - timedelta(days=20),
             notes="Scope cut agreed; buffer feature moved to next PI."),
        Risk("AR-4", "License audit finding on reporting library",
             ROAM_RESOLVED, owner="System Team", impact=IMPACT_LOW,
             status_since=reference - timedelta(days=5)),
        Risk("AR-5", "Peak-load capacity above target only with new cluster",
             ROAM_ACCEPTED, owner="ART Alpha-1", impact=IMPACT_LOW,
             status_since=reference - timedelta(days=30)),
    ])


def _beta_risks(reference: date, story: str = STORY_NOW) -> RiskRegister:
    """
    ROAM register of Solution Beta: the second aging owned risk lives here.

    In the prev story (two weeks earlier), BR-2 does not exist yet — it shows
    up as a *new* risk in the Delta-Briefing demo.
    """
    risks = [
        Risk("BR-1", "Data quality of ART Beta-3 blocks solution reporting",
             ROAM_OWNED, owner="ART Beta-3", impact=IMPACT_HIGH,
             status_since=reference - timedelta(days=50),
             notes="Aging: matches the weak-source story of this scenario."),
        Risk("BR-3", "Vendor API rate limits during nightly sync",
             ROAM_ACCEPTED, owner="ART Beta-1", impact=IMPACT_MEDIUM,
             status_since=reference - timedelta(days=15)),
        Risk("BR-4", "Duplicate effort with platform team clarified",
             ROAM_RESOLVED, owner="ART Beta-2", impact=IMPACT_LOW,
             status_since=reference - timedelta(days=12)),
    ]
    if story != STORY_PREV:
        risks.insert(1, Risk(
            "BR-2", "Security review for release milestone not scheduled",
            ROAM_MITIGATED, owner="Shared Services", impact=IMPACT_HIGH,
            status_since=reference - timedelta(days=7),
            notes="Interim: external reviewer booked for next sprint."))
    return RiskRegister(risks=risks)


def _alpha_capabilities(reference: date) -> CapabilityMap:
    """Capability map of Solution Alpha: solid, one uncovered capability."""
    return CapabilityMap(capabilities=[
        Capability("AC-1", "Order management", HEALTH_HEALTHY,
                   arts=["ART Alpha-1", "ART Alpha-2"], owner="ART Alpha-1",
                   assessed_on=reference - timedelta(days=14)),
        Capability("AC-2", "Billing & invoicing", HEALTH_AT_RISK,
                   arts=["ART Alpha-3"], owner="ART Alpha-3",
                   assessed_on=reference - timedelta(days=14),
                   notes="Depends on the outlier ART's delivery pace."),
        # Uncovered: business value nobody delivers — the ARTs cell is flagged.
        Capability("AC-3", "Partner self-service", HEALTH_HEALTHY,
                   arts=[], owner="System Team",
                   assessed_on=reference - timedelta(days=45),
                   notes="Planned; no ART assigned yet."),
    ])


def _beta_capabilities(reference: date) -> CapabilityMap:
    """Capability map of Solution Beta: the critical capability lives here."""
    return CapabilityMap(capabilities=[
        Capability("BC-1", "Data insights & reporting", HEALTH_CRITICAL,
                   arts=["ART Beta-3"], owner="ART Beta-3",
                   assessed_on=reference - timedelta(days=7),
                   notes="Matches the weak-source story: data quality blocks it."),
        Capability("BC-2", "Customer onboarding", HEALTH_HEALTHY,
                   arts=["ART Beta-1", "ART Beta-2"], owner="ART Beta-1",
                   assessed_on=reference - timedelta(days=7)),
        Capability("BC-3", "Payment processing", HEALTH_HEALTHY,
                   arts=["ART Beta-2"], owner="ART Beta-2",
                   assessed_on=reference - timedelta(days=7)),
    ])


def _alpha_themes(story: str = STORY_NOW) -> ThemesRegister:
    """
    Themes/roadmap of Solution Alpha: one orphan theme, one zombie epic.

    Prev story (Delta demo): EP-A9 still had its theme two weeks ago —
    losing the strategic home is one of the 'updated roadmaps' changes.
    """
    prev = story == STORY_PREV
    return ThemesRegister(
        themes=[
            StrategicTheme("T-A1", "Digital ordering end-to-end",
                           "Order intake to billing without media breaks."),
            # Deklariert und vergessen: kein einziges Epic zahlt ein.
            StrategicTheme("T-A2", "Green operations",
                           "Energy-aware runtime operations."),
        ],
        epics=[
            Epic("EP-A1", "Self-service order portal", "ART Alpha-1",
                 "P1", theme="T-A1", status=EPIC_IN_PROGRESS),
            Epic("EP-A2", "Billing integration", "ART Alpha-2",
                 "P2", theme="T-A1"),
            Epic("EP-A3", "Order analytics", "ART Alpha-1",
                 "Y1", theme="T-A1"),
            # Die Zombie-Initiative: im Prev-Stand noch mit Theme.
            Epic("EP-A9", "Legacy portal rewrite", "ART Alpha-3",
                 "Y1", theme="T-A1" if prev else ""),
        ],
    )


def _beta_themes(story: str = STORY_NOW) -> ThemesRegister:
    """
    Themes/roadmap of Solution Beta.

    Prev story: the data-quality epic was still parked in P2 — pulling it
    into P1 is the second 'updated roadmaps' change.
    """
    prev = story == STORY_PREV
    return ThemesRegister(
        themes=[
            StrategicTheme("T-B1", "Trusted reporting",
                           "One reporting truth across the solution."),
        ],
        epics=[
            Epic("EP-B1", "Vendor sync hardening", "ART Beta-1",
                 "P1", theme="T-B1", status=EPIC_DONE),
            Epic("EP-B2", "Beta-3 data-quality remediation", "ART Beta-3",
                 "P2" if prev else "P1", theme="T-B1",
                 status=EPIC_IN_PROGRESS),
            Epic("EP-B3", "Cross-solution reporting hub", "ART Beta-2",
                 "Y2", theme="T-B1"),
        ],
    )


def _alpha_flow_problems(reference: date) -> FlowProblemRegister:
    """Flow problems of Solution Alpha: one has survived three conferences."""
    return FlowProblemRegister(problems=[
        # Das Workshop-Muster: geloggt, nie mitigiert, taucht wieder auf.
        FlowProblem("FP-A1", "Test-environment provisioning takes weeks",
                    FLOW_OPEN,
                    value_streams=["ART Alpha-1", "ART Alpha-2",
                                   "ART Alpha-3"],
                    source="VSC", owner="System Team",
                    raised_on=reference - timedelta(days=140),
                    conferences=3,
                    notes="Survivor: raised at three conferences, still open."),
        FlowProblem("FP-A2", "Review bottleneck at architecture board",
                    FLOW_COMMITTED,
                    value_streams=["ART Alpha-2"],
                    source="ART Alpha-2", owner="System Team",
                    raised_on=reference - timedelta(days=40),
                    conferences=1,
                    resolution_commitment="Second review slot per week",
                    follow_up_pi="PI 5"),
    ])


def _beta_flow_problems(reference: date) -> FlowProblemRegister:
    """Flow problems of Solution Beta: the weak source blocks two streams."""
    return FlowProblemRegister(problems=[
        FlowProblem("FP-B1", "Beta-3 export quality blocks solution reporting",
                    FLOW_OPEN,
                    value_streams=["ART Beta-1", "ART Beta-3"],
                    source="VSC", owner="ART Beta-3",
                    raised_on=reference - timedelta(days=200),
                    conferences=4,
                    notes="Cross-VS survivor: matches the weak-source story."),
        FlowProblem("FP-B2", "Shared staging window conflicts",
                    FLOW_RESOLVED,
                    value_streams=["ART Beta-1", "ART Beta-2"],
                    source="ART Beta-1", owner="ART Beta-2",
                    raised_on=reference - timedelta(days=90),
                    conferences=2,
                    resolution_commitment="Calendar-based slot booking"),
    ])


def _alpha_slo(reference: date) -> SloRegister:
    """SLOs of Solution Alpha: healthy, one budget running low."""
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


def _beta_slo(reference: date) -> SloRegister:
    """SLOs of Solution Beta: the sync service has burned its budget."""
    src = "demo-scenario"
    at = reference.isoformat()
    return SloRegister(records=[
        # Die Geschichte: der Sync-Dienst (Beta-3-Umfeld) reisst sein SLO.
        SloRecord("Order Sync API", "availability", 99.5, sli_pct=99.1,
                  source=src, fetched_at=at),
        SloRecord("Reporting", "p95 latency < 500 ms", 99.0, sli_pct=99.6,
                  source=src, fetched_at=at),
    ])


def _alpha_delivery(reference: date) -> DeliveryRegister:
    """Delivery health of Solution Alpha: solid, the outlier ships slowly."""
    src = "demo-scenario"
    at = reference.isoformat()
    return DeliveryRegister(
        dora=[
            DoraRecord("ART Alpha-1", deployments_per_day=1.4,
                       lead_time_hours=18.0, change_failure_rate_pct=4.0,
                       time_to_restore_hours=0.8, source=src, fetched_at=at),
            DoraRecord("ART Alpha-2", deployments_per_day=0.6,
                       lead_time_hours=40.0, change_failure_rate_pct=8.0,
                       time_to_restore_hours=6.0, source=src, fetched_at=at),
            # Der Ausreisser liefert auch selten und langsam.
            DoraRecord("ART Alpha-3", deployments_per_day=0.05,
                       lead_time_hours=520.0, change_failure_rate_pct=14.0,
                       time_to_restore_hours=20.0, source=src, fetched_at=at),
        ],
        quality=[
            QualityRecord("ART Alpha-1", coverage_pct=78.0,
                          maintainability="A", critical_issues=0,
                          source=src, fetched_at=at),
            QualityRecord("ART Alpha-3", coverage_pct=55.0,
                          maintainability="C", critical_issues=2,
                          source=src, fetched_at=at),
        ],
    )


def _beta_delivery(reference: date) -> DeliveryRegister:
    """Delivery health of Solution Beta: the weak source is low tier."""
    src = "demo-scenario"
    at = reference.isoformat()
    return DeliveryRegister(
        dora=[
            DoraRecord("ART Beta-1", deployments_per_day=0.9,
                       lead_time_hours=30.0, change_failure_rate_pct=6.0,
                       time_to_restore_hours=3.0, source=src, fetched_at=at),
            # Die Geschichte: Beta-3 auch im Delivery-Bild low.
            DoraRecord("ART Beta-3", deployments_per_day=0.02,
                       lead_time_hours=800.0, change_failure_rate_pct=38.0,
                       time_to_restore_hours=30.0, source=src, fetched_at=at),
        ],
        quality=[
            QualityRecord("ART Beta-3", coverage_pct=31.0,
                          maintainability="D", critical_issues=7,
                          source=src, fetched_at=at),
        ],
    )


def _alpha_decisions(reference: date) -> DecisionLog:
    """Decision log of Solution Alpha: a superseded chain plus a confirmed assumption."""
    return DecisionLog(entries=[
        LogEntry("ADR-A2", KIND_DECISION,
                 "Pool ARTs via fixed three-group mapping",
                 DECISION_SUPERSEDED, owner="System Team",
                 logged_on=reference - timedelta(days=120)),
        LogEntry("ADR-A1", KIND_DECISION,
                 "Pool ARTs via custom stage map (schema 2)",
                 DECISION_ACCEPTED, owner="System Team",
                 logged_on=reference - timedelta(days=60),
                 supersedes="ADR-A2",
                 notes="Keeps heterogeneous workflows comparable."),
        LogEntry("AS-A1", KIND_ASSUMPTION,
                 "All ARTs keep exporting weekly Jira snapshots",
                 ASSUMPTION_CONFIRMED, owner="ART Alpha-1",
                 logged_on=reference - timedelta(days=90),
                 review_by=reference + timedelta(days=90)),
    ])


def _beta_decisions(reference: date) -> DecisionLog:
    """Decision log of Solution Beta: the overdue open assumption lives here."""
    return DecisionLog(entries=[
        LogEntry("ADR-B1", KIND_DECISION,
                 "Buy vendor sync service instead of building",
                 DECISION_ACCEPTED, owner="ART Beta-1",
                 logged_on=reference - timedelta(days=150),
                 notes="Trade-off: rate limits accepted (see dependency BD-1)."),
        # Die Geschichte: eine offene Annahme mit überschrittenem Prüfdatum —
        # genau die Sorte Selbstberuhigung, die ein Premortem aufdecken soll.
        LogEntry("AS-B1", KIND_ASSUMPTION,
                 "Beta-3 data quality will fix itself with the next Jira rollout",
                 ASSUMPTION_OPEN, owner="ART Beta-3",
                 logged_on=reference - timedelta(days=70),
                 review_by=reference - timedelta(days=10),
                 notes="Review due: matches the weak-source story."),
    ])


def _alpha_dependencies(
    reference: date, story: str = STORY_NOW
) -> DependencyRegister:
    """
    Dependencies of Solution Alpha: the overdue blocked one lives here.

    In the prev story, AD-1 was still at risk — the escalation to blocked is
    the status transition the Delta-Briefing demo shows.
    """
    return DependencyRegister(dependencies=[
        # Die Geschichte: der Ausreißer Alpha-3 liefert nicht — blockiert
        # und überfällig, springt in der Heatmap rot an.
        Dependency("AD-1", "Billing API contract for order flow",
                   from_art="ART Alpha-1", to_art="ART Alpha-3",
                   status=DEP_AT_RISK if story == STORY_PREV else DEP_BLOCKED,
                   due=reference - timedelta(days=15),
                   notes="Overdue: matches the outlier story of this scenario."),
        Dependency("AD-2", "Shared test fixtures for the order domain",
                   from_art="ART Alpha-2", to_art="ART Alpha-1",
                   status=DEP_ON_TRACK, due=reference + timedelta(days=25)),
        Dependency("AD-3", "SSO integration with platform services",
                   from_art="ART Alpha-2", to_art="Platform Services",
                   status=DEP_ON_TRACK, due=reference + timedelta(days=40),
                   notes="External integration point outside the solution."),
    ])


def _beta_dependencies(reference: date) -> DependencyRegister:
    """Dependencies of Solution Beta: includes a cross-solution integration."""
    return DependencyRegister(dependencies=[
        # Cross-Solution-Integration: Beta braucht Alphas Order-Events —
        # sichtbar nur im Portfolio-Report.
        Dependency("BD-1", "Order events feed for reporting",
                   from_art="ART Beta-1", to_art="ART Alpha-1",
                   status=DEP_AT_RISK, due=reference + timedelta(days=10),
                   notes="Cross-solution integration with Solution Alpha."),
        Dependency("BD-2", "Sync-service schema migration",
                   from_art="ART Beta-2", to_art="ART Beta-3",
                   status=DEP_DONE, due=reference - timedelta(days=30)),
    ])


def _alpha_nfr(reference: date) -> NfrRegister:
    """NFR/runway register of Solution Alpha: healthy, one NFR at risk."""
    return NfrRegister(
        nfrs=[
            Nfr("AN-1", "Report generation time", target="< 30 s for 10k issues",
                actual="18 s", status=STATUS_MET, owner="System Team"),
            Nfr("AN-2", "Availability of the reporting service",
                target=">= 99.5 % per quarter", actual="99.7 %",
                status=STATUS_MET, owner="System Team"),
            Nfr("AN-3", "Peak concurrent report users", target="50 users",
                actual="42 users tested", status=STATUS_AT_RISK,
                owner="ART Alpha-1",
                notes="Load test above 42 users pending new cluster."),
        ],
        runway=[
            RunwayItem("ARW-1", "Central data lake connection",
                       status=RUNWAY_IN_PLACE, owner="System Team"),
            RunwayItem("ARW-2", "Self-service test environment",
                       status=RUNWAY_BUILDING,
                       needed_by=reference + timedelta(days=40),
                       owner="System Team"),
        ])


def _beta_nfr(reference: date) -> NfrRegister:
    """NFR/runway register of Solution Beta: one violated NFR, one overdue gap."""
    return NfrRegister(
        nfrs=[
            Nfr("BN-1", "API response time", target="p95 < 200 ms",
                actual="p95 = 340 ms", status=STATUS_VIOLATED,
                owner="ART Beta-1",
                notes="Regression since the vendor library update."),
            Nfr("BN-2", "Data retention compliance", target="Delete after 180 days",
                actual="Job active", status=STATUS_MET, owner="Shared Services"),
            Nfr("BN-3", "Recovery time objective", target="RTO < 4 h",
                actual="Not measured since failover test",
                status=STATUS_AT_RISK, owner="ART Beta-2"),
        ],
        runway=[
            # 10 Tage überfällig: vor 14 Tagen noch nicht — im Delta-Briefing
            # taucht die Lücke als „newly overdue" auf (B2- + D2-Story).
            RunwayItem("BRW-1", "Automated failover for the sync service",
                       status=RUNWAY_GAP,
                       needed_by=reference - timedelta(days=10),
                       owner="ART Beta-2",
                       notes="Overdue: needed before the last release."),
            RunwayItem("BRW-2", "Contract test suite against vendor API",
                       status=RUNWAY_BUILDING,
                       needed_by=reference + timedelta(days=30),
                       owner="ART Beta-1"),
        ])


def build_portfolio_scenario(
    output_dir: Path,
    seed: int = 42,
    reference: date | None = None,
    window_days: int = 365,
    log: Callable[[str], None] = print,
    story: str = STORY_NOW,
    scale: str = DEFAULT_SCALE,
    art_profiles: dict[str, dict] | None = None,
) -> dict[str, Path]:
    """
    Generate the complete demo portfolio into ``output_dir``.

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

    Returns:
        Dict with the key output paths (portfolio config, solution configs,
        risk registers, PI config, readme).
    """
    reference = reference or date.today()
    out = Path(output_dir)
    (out / "workflows").mkdir(parents=True, exist_ok=True)
    (out / "raw").mkdir(exist_ok=True)
    (out / "snapshots").mkdir(exist_ok=True)
    for _key in ("alpha", "beta"):
        (out / "solutions" / _key / "arts").mkdir(parents=True, exist_ok=True)
        (out / "solutions" / _key / "registers").mkdir(parents=True,
                                                       exist_ok=True)

    workflow_files = {
        "alpha": out / "workflows" / "alpha.txt",
        "beta": out / "workflows" / "beta.txt",
    }
    workflow_files["alpha"].write_text(_WORKFLOW_ALPHA, encoding="utf-8")
    workflow_files["beta"].write_text(_WORKFLOW_BETA, encoding="utf-8")

    members: dict[str, list[Member]] = {"alpha": [], "beta": []}
    for i, (solution_key, profile) in enumerate(
            _profiles(story, art_profiles)):
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

    # Story-Anker (handgeschriebene Fixtures) + seed-generierte
    # Grundmenge (register_gen, Skala S/M/L) je Solution.
    anchor_registers = {
        "alpha": {
            "risks": _alpha_risks(reference),
            "nfr": _alpha_nfr(reference),
            "capabilities": _alpha_capabilities(reference),
            "dependencies": _alpha_dependencies(reference, story),
            "decisions": _alpha_decisions(reference),
            "slo": _alpha_slo(reference),
            "dora": _alpha_delivery(reference),
            "flow_problems": _alpha_flow_problems(reference),
            "themes": _alpha_themes(story),
        },
        "beta": {
            "risks": _beta_risks(reference, story),
            "nfr": _beta_nfr(reference),
            "capabilities": _beta_capabilities(reference),
            "dependencies": _beta_dependencies(reference),
            "decisions": _beta_decisions(reference),
            "slo": _beta_slo(reference),
            "dora": _beta_delivery(reference),
            "flow_problems": _beta_flow_problems(reference),
            "themes": _beta_themes(story),
        },
    }
    savers = {"risks": save_risks, "nfr": save_nfr,
              "capabilities": save_capabilities,
              "dependencies": save_dependencies,
              "decisions": save_decisions, "slo": save_slo,
              "dora": save_delivery, "flow_problems": save_flow_problems,
              "themes": save_themes}
    register_paths: dict[str, Path] = {}
    for solution_key, regs in anchor_registers.items():
        populate_registers(
            regs, solution_key,
            art_names=[m.name for m in members[solution_key]],
            reference=reference, seed=seed, scale=scale,
            prev=(story == STORY_PREV))
        for name, register in regs.items():
            target = (out / "solutions" / solution_key / "registers"
                      / f"{name}.json")
            savers[name](target, register)
            register_paths[f"{name}_{solution_key}"] = target

    risks_alpha = register_paths["risks_alpha"]
    risks_beta = register_paths["risks_beta"]
    nfr_alpha = register_paths["nfr_alpha"]
    nfr_beta = register_paths["nfr_beta"]
    caps_alpha = register_paths["capabilities_alpha"]
    caps_beta = register_paths["capabilities_beta"]
    deps_alpha = register_paths["dependencies_alpha"]
    deps_beta = register_paths["dependencies_beta"]
    decisions_alpha = register_paths["decisions_alpha"]
    decisions_beta = register_paths["decisions_beta"]
    slo_alpha = register_paths["slo_alpha"]
    slo_beta = register_paths["slo_beta"]
    dora_alpha = register_paths["dora_alpha"]
    dora_beta = register_paths["dora_beta"]
    flow_alpha = register_paths["flow_problems_alpha"]
    flow_beta = register_paths["flow_problems_beta"]
    themes_alpha = register_paths["themes_alpha"]
    themes_beta = register_paths["themes_beta"]

    _registers = {r: f"registers/{r}.json"
                  for r in ("risks", "nfr", "capabilities", "dependencies",
                            "decisions", "slo", "dora", "flow_problems",
                            "themes")}
    solution_alpha = out / "solutions" / "alpha" / "solution.json"
    save_solution_config(solution_alpha, SolutionConfig(
        name="Solution Alpha", members=members["alpha"],
        from_date=reference - timedelta(days=window_days), to_date=reference,
        **_registers))
    solution_beta = out / "solutions" / "beta" / "solution.json"
    save_solution_config(solution_beta, SolutionConfig(
        name="Solution Beta", members=members["beta"],
        from_date=reference - timedelta(days=window_days), to_date=reference,
        stage_map=_BETA_STAGE_MAP, **_registers))

    portfolio_cfg = out / "portfolio.json"
    save_solution_config(portfolio_cfg, SolutionConfig(
        name="Demo Portfolio", kind=KIND_PORTFOLIO,
        members=[
            Member(name="Solution Alpha",
                   template="solutions/alpha/solution.json"),
            Member(name="Solution Beta",
                   template="solutions/beta/solution.json"),
        ],
        from_date=reference - timedelta(days=window_days), to_date=reference))

    pi_cfg = out / "pi_config.json"
    quarters = []
    q_start = reference - timedelta(days=window_days)
    n = 1
    while q_start < reference:
        q_end = min(q_start + timedelta(days=90), reference)
        quarters.append({"name": f"PI {n}",
                         "from": q_start.isoformat(), "to": q_end.isoformat()})
        q_start = q_end + timedelta(days=1)
        n += 1
    pi_cfg.write_text(json.dumps({"mode": "date", "intervals": quarters}, indent=2),
                      encoding="utf-8")

    readme = out / "README.md"
    readme.write_text("\n".join([
        "# Demo Portfolio (generierte Testdaten)",
        "",
        f"Erzeugt mit `python -m testdata_generator --scenario portfolio` "
        f"(Seed {seed}, Referenzdatum {reference.isoformat()}).",
        "",
        "Direkt verwendbar: `python -m portfolio portfolio.json` bzw. die",
        "Solution-Configs einzeln. **Der Ordner ist ein Portfolio-Datenraum**:",
        "alle Pfade in den Configs sind relativ zur jeweiligen Config-Datei —",
        "der Ordner kann als Ganzes verschoben, kopiert oder gezippt werden.",
        "",
        "    portfolio.json            Einstieg (Portfolio)",
        "    solutions/<name>/         je Solution: solution.json,",
        "                              arts/ (IssueTimes/Transitions/CFD),",
        "                              registers/ (Standardnamen: risks.json,",
        "                              nfr.json, capabilities.json,",
        "                              dependencies.json, decisions.json,",
        "                              slo.json, dora.json, flow_problems.json,",
        "                              themes.json)",
        "    workflows/  raw/  pi_config.json",
        "    snapshots/                snapshot_prev.json, snapshot_now.json",
        "",
        "Die Register bestehen aus festen **Story-Ankern** (unten) plus",
        "einer seed-generierten Grundmenge; `--scale s|m|l` steuert deren",
        "Umfang je Solution (s = nur Anker, m = Standard, l = Stresstest).",
        "Die Anker und ihre Geschichten sind auf jeder Skala identisch.",
        "Je ART lassen sich die Generator-Regler übersteuern (GUI-Dialog",
        "„ART-Profile…“ bzw. `--art-profiles datei.json`): Issues, Ø-/σ-CT,",
        "Quoten, Backflow, Muster + Stärke, PI-Wochen — Overrides gelten",
        "in beiden Delta-Ständen, alles andere behält seinen Story-Wert.",
        "",
        "Eingebaute Geschichten:",
        "",
        "- **ART Alpha-3** ist der Ausreißer (Cycle Time ~3x) — im",
        "  Comparison-Report der Solution Alpha markiert die",
        "  Ausreißer-Hervorhebung seine Median-/P95-Zellen rot.",
        "- **ART Beta-3** liefert schwache Daten (kein CFD, kaum First Dates,",
        "  Datenstand 60 Tage alt) — die Qualitätstabelle zeigt ihn als 'low',",
        "  der Titel meldet die Abdeckung.",
        "- **Solution Beta** poolt über eine eigene `stage_map` (Schema 2,",
        "  Vorlauf/Umsetzung/Fertig); Solution Alpha nutzt den Default-Pfad",
        "  (To Do / In Progress / Done).",
        "- **ROAM-Board**: beide Solutions bringen ein Risiko-Register mit",
        "  (`solutions/*/registers/risks.json`); zwei Owned-Risiken sind",
        "  bewusst alt (45/50 Tage) — das Aging springt im Board rot an.",
        "- **NFR & Runway**: beide Solutions bringen ein NFR-Register mit",
        "  (`registers/nfr.json`); Betas API-NFR ist verletzt und",
        "  ein Runway-Element ist eine überfällige Lücke — Dashboard-Ampel rot.",
        "- **Capability-Map**: beide Solutions bringen eine Capability-Map mit",
        "  (`registers/capabilities.json`); Betas",
        "  Data-Insights-Capability ist kritisch (schwache Quelle) und Alphas",
        "  Partner-Self-Service hat keinen beitragenden ART (uncovered).",
        "- **Dependency-Heatmap**: beide Solutions bringen ein",
        "  Dependency-Register mit (`registers/dependencies.json`);",
        "  Alpha-1 → Alpha-3 ist blockiert und",
        "  überfällig (der Ausreißer liefert nicht), Beta-1 → Alpha-1 ist eine",
        "  Cross-Solution-Integration — im Portfolio-Report sichtbar.",
        "- **Decision-Log**: beide Solutions bringen ein Decision-/",
        "  Assumption-Log mit (`registers/decisions.json`);",
        "  Alphas Stage-Map-Entscheidung ersetzt eine ältere (supersedes),",
        "  Betas offene Annahme „Beta-3 heilt sich selbst\" hat ihr Prüfdatum",
        "  überschritten — im Log rot als „review due\" markiert.",
        "- **Flussproblem-Backlog (B6, VSC)**: `registers/flow_problems.json`;",
        "  FP-A1 und FP-B1 haben 3 bzw. 4 Konferenzen überlebt (das",
        "  Workshop-Muster „geloggt, nie mitigiert\" — rot markiert), FP-B1",
        "  ist Cross-VS. Konferenzmappe: `python -m portfolio portfolio.json",
        "  --conference mappe.html`.",
        "- **Strategic Themes & Roadmap (B7, VSC)**: `registers/themes.json`;",
        "  Alphas Theme „Green operations\" ist verwaist (kein Epic —",
        "  „declared & forgotten\"), EP-A9 ist eine Zombie-Initiative ohne",
        "  Theme; die Roadmap-Matrix zeigt Trains × P1·P2·Y1·Y2·Y3. Im",
        "  Delta-Briefing: EP-A9 verlor sein Theme, EP-B2 wurde von P2 nach",
        "  P1 gezogen („updated roadmaps\").",
        "- **SLO & Error-Budgets (C1)**: `registers/slo.json`;",
        "  Betas „Order Sync API\" reißt ihr SLO (breached), Alphas",
        "  „Checkout\" hat sein Budget fast aufgebraucht (at risk).",
        "- **DORA & Code-Qualität (C2)**: `registers/dora.json`;",
        "  ART Beta-3 ist auch im Delivery-Bild low (CFR 38 %, MTTR 30 h,",
        "  Coverage 31 %, Rating D) — die schwache Quelle von allen Seiten.",
        "  Erzeugt/austauschbar über `python -m sources fetch` (Provider:",
        "  file, prometheus, github, gitlab, sonarqube — kombinierbar).",
        "- **Delta-Briefing (D2)**: `snapshots/snapshot_prev.json` (Stand vor",
        "  14 Tagen) und `snapshots/snapshot_now.json` liegen bei —",
        "  `python -m portfolio --delta snapshots/snapshot_prev.json",
        "  snapshots/snapshot_now.json`",
        "  zeigt: Durchsatz im Zeitraum, Beta-3-Konfidenz medium → low,",
        "  AD-1 at_risk → blocked, Risiko BR-2 neu, Runway-Lücke und Annahme",
        "  AS-B1 frisch überfällig.",
        "- **KI-Narration (D2 Teil 2)**: `--narrate mock` ergänzt das",
        "  Briefing um den gekennzeichneten Abschnitt „Narration (Entwurf)\"",
        "  — ohne Modell oder Installation (Attrappe); der Nachweis landet",
        "  in `llm_audit.jsonl`. Mit lokal installiertem Ollama echt:",
        "  `--narrate` (Modell mistral-nemo; Anleitung: Doku-Site →",
        "  Tutorials → „Ollama auf Windows 11\").",
        "",
        "Die Roh-JSONs unter `raw/` sind zugleich Demo-Futter für get_data:",
        "`python -m get_data check raw/Alpha-1_jira.json` zeigt die",
        "Export-Prüfung (Weg 2) am Beispiel.",
    ]), encoding="utf-8")

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
            prev_paths = build_portfolio_scenario(
                Path(tmp), seed=seed, reference=reference,
                window_days=window_days, log=lambda m: None,
                story=STORY_PREV, scale=scale,
                art_profiles=art_profiles)
            save_snapshot(snapshot_prev, build_snapshot(
                load_solution_config(prev_paths["portfolio"]),
                as_of=reference - timedelta(days=14), log=lambda m: None))

    log(f"Szenario komplett: {out}")
    return {"portfolio": portfolio_cfg, "solution_alpha": solution_alpha,
            "solution_beta": solution_beta, "risks_alpha": risks_alpha,
            "risks_beta": risks_beta, "nfr_alpha": nfr_alpha,
            "nfr_beta": nfr_beta, "capabilities_alpha": caps_alpha,
            "capabilities_beta": caps_beta, "dependencies_alpha": deps_alpha,
            "dependencies_beta": deps_beta, "decisions_alpha": decisions_alpha,
            "decisions_beta": decisions_beta, "pi_config": pi_cfg,
            "flow_alpha": flow_alpha, "flow_beta": flow_beta,
            "themes_alpha": themes_alpha, "themes_beta": themes_beta,
            "slo_alpha": slo_alpha, "slo_beta": slo_beta,
            "dora_alpha": dora_alpha, "dora_beta": dora_beta,
            "snapshot_prev": snapshot_prev, "snapshot_now": snapshot_now,
            "readme": readme}
