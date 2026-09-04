# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       04.09.2026
# Geändert:       04.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Register-Generatoren des Demo-Szenarios (Datenraum-Konzept Phase 3):
#   erzeugen je Registertyp eine seed-reproduzierbare GRUNDMENGE mit
#   Verteilungen und gemeinsamen Namenspools — in derselben Liga wie die
#   Jira-Generatoren. Die erzählten Story-Anker (BR-2, AD-1, EP-A9 …)
#   bleiben handgeschriebene Fixtures in scenario.py; die Grundmenge wird
#   UM sie herumgelegt und hält Invarianten ein, die die Anker einzigartig
#   lassen: kein zusätzliches verletztes NFR, keine überfällige Lücke,
#   kein überfälliges Blocked, kein zweites breached-SLO, keine weiteren
#   Survivors (Zähler ≤ 2), keine Orphans/Zombies, kein Risiko-Aging
#   > 30 Tage, keine Drift-Warnungen (nur echte ART-Namen). Owner sind
#   stets Teams, nie Personen (Aggregat-Grenze).
#
#   prev/now: Die Grundmenge wird für beide Stände IDENTISCH gewürfelt
#   (alle Zufallszüge geschehen unabhängig vom Drop), dann entscheidet
#   eine deterministische ID-Prüfsummenregel, welche Einträge zwei Wochen
#   vorher „noch nicht existierten“ — das Delta-Briefing zeigt sie als
#   added. Querverweise (supersedes, Epic→Theme) zeigen nur auf
#   drop-sichere Ziele, damit beide Stände valide Register bleiben.
# =============================================================================

from __future__ import annotations

import random
import zlib
from dataclasses import dataclass
from datetime import date, timedelta

from portfolio.capability_config import (
    HEALTH_AT_RISK,
    HEALTH_HEALTHY,
    Capability,
    CapabilityMap,
)
from portfolio.decision_config import (
    ASSUMPTION_CONFIRMED,
    ASSUMPTION_OPEN,
    DECISION_ACCEPTED,
    DECISION_PROPOSED,
    KIND_ASSUMPTION,
    KIND_DECISION,
    DecisionLog,
    LogEntry,
)
from portfolio.dependency_config import (
    DEP_AT_RISK,
    DEP_DONE,
    DEP_ON_TRACK,
    Dependency,
    DependencyRegister,
)
from portfolio.flow_problems_config import (
    FLOW_COMMITTED,
    FLOW_OPEN,
    FLOW_RESOLVED,
    FlowProblem,
    FlowProblemRegister,
)
from portfolio.nfr_config import (
    RUNWAY_BUILDING,
    RUNWAY_IN_PLACE,
    STATUS_AT_RISK,
    STATUS_MET,
    Nfr,
    NfrRegister,
    RunwayItem,
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
)
from portfolio.slo_config import SloRegister
from portfolio.themes_config import (
    EPIC_DONE,
    EPIC_IN_PROGRESS,
    EPIC_PLANNED,
    HORIZONS,
    Epic,
    StrategicTheme,
    ThemesRegister,
)
from sources.base import SloRecord

SCALE_S = "s"
SCALE_M = "m"
SCALE_L = "l"
SCALES = (SCALE_S, SCALE_M, SCALE_L)
DEFAULT_SCALE = SCALE_M  # Entscheidung Robert 04.09.2026


@dataclass(frozen=True)
class ScaleProfile:
    """Base-population sizes per register, PER SOLUTION (anchors add on top)."""
    risks: int
    nfrs: int
    runway: int
    capabilities: int
    dependencies: int
    decisions: int
    assumptions: int
    slos: int
    themes: int
    epics: int
    flow_problems: int


#: S = anchors only (today's storytelling density); M = realistic demo;
#: L = stress test for sorting, heatmap density and the roadmap matrix.
SCALE_PROFILES: dict[str, ScaleProfile] = {
    SCALE_S: ScaleProfile(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    SCALE_M: ScaleProfile(risks=10, nfrs=6, runway=4, capabilities=6,
                          dependencies=12, decisions=7, assumptions=3,
                          slos=6, themes=3, epics=12, flow_problems=7),
    SCALE_L: ScaleProfile(risks=36, nfrs=16, runway=10, capabilities=16,
                          dependencies=40, decisions=22, assumptions=8,
                          slos=18, themes=7, epics=40, flow_problems=22),
}

# ── Gemeinsame Namenspools (Teams, nie Personen — Aggregat-Grenze) ──────────

_TEAM_POOL = ("Plattform-Team", "Payments-Team", "Data-Team",
              "Mobile-Team", "Integration-Team", "Security-Gilde",
              "SRE-Team", "Frontend-Team")

_RISK_TOPICS = ("Lieferant verschiebt Schnittstellen-Update",
                "Testumgebung teilt Kapazität mit Nachbarprojekt",
                "Lizenzmodell des Monitorings ändert sich",
                "Wissensinsel im Legacy-Abrechnungsmodul",
                "Cloud-Kostenlimit vor Quartalsende erreicht",
                "Zertifikatsrotation nicht automatisiert",
                "Datenmigration braucht Sonderfenster",
                "Externe Prüfung bindet Schlüsselteam",
                "Feature-Toggle-Altlasten wachsen",
                "Onboarding neuer Teams verzögert sich")

_NFR_TOPICS = (("Antwortzeit Suche", "p95 < 300 ms"),
               ("Verfügbarkeit Kernservices", ">= 99,9 % / 30d"),
               ("Wiederanlauf nach Ausfall", "RTO < 30 min"),
               ("Datenexport DSGVO", "< 24 h"),
               ("Barrierefreiheit Portal", "WCAG 2.1 AA"),
               ("Deployment-Dauer", "< 15 min"),
               ("Audit-Log-Vollständigkeit", "100 % der Schreibzugriffe"),
               ("Verschlüsselung ruhender Daten", "AES-256 überall"))

_RUNWAY_TOPICS = ("Event-Bus Mandantentrennung", "Feature-Flag-Service",
                  "Blue-Green-Deployment Pipeline",
                  "Zentrales Secret-Management",
                  "Contract-Testing-Infrastruktur", "Observability-Stack v2")

_CAPABILITY_TOPICS = ("Self-Service-Reporting", "Echtzeit-Bestandsübersicht",
                      "Partner-API-Verwaltung", "Automatisierte Rückerstattung",
                      "Mehrsprachige Storefront", "Vertrags-Lifecycle",
                      "Bonitätsprüfung", "Kampagnen-Steuerung")

_DEP_TOPICS = ("liefert Schnittstellen-Mock", "stellt Testdaten bereit",
               "migriert gemeinsames Schema", "übergibt Betriebsverantwortung",
               "liefert Designsystem-Update", "klärt Datenhoheit",
               "stellt Sandbox-Zugang", "liefert Lastprofil")

_DECISION_TOPICS = ("Standard-Nachrichtenformat vereinheitlichen",
                    "Read-Replicas je Region einführen",
                    "Ende-zu-Ende-Testsuite konsolidieren",
                    "API-Versionierung auf Header umstellen",
                    "Batch-Fenster in Streaming überführen",
                    "Einheitliches Fehlerbudget-Reporting")

_ASSUMPTION_TOPICS = ("Traffic wächst < 20 % pro Quartal",
                      "Legacy-Ablösung bleibt im Zeitplan",
                      "Partner hält API-Kontingent ein",
                      "Team-Besetzung bleibt stabil")

_SERVICE_POOL = ("Search", "Billing", "Notifications", "Catalog",
                 "Customer Profile", "Inventory", "Reporting", "Auth")

_THEME_TOPICS = ("Operational Excellence", "Time-to-Market halbieren",
                 "Datengetriebene Entscheidungen", "Plattform-Konsolidierung",
                 "Partner-Ökosystem ausbauen", "Nachhaltiger Betrieb",
                 "Compliance by Design")

_EPIC_TOPICS = ("Suchrelevanz-Offensive", "Checkout-Vereinfachung",
                "Reporting-Selbstbedienung", "API-Gateway-Ablösung",
                "Bestandsdaten in Echtzeit", "Rechnungsarchiv-Migration",
                "Kundenportal-Relaunch", "Telemetrie-Ausbau",
                "Zahlartenerweiterung", "Altsystem-Abschaltung")

_FLOW_TOPICS = ("Freigaben dauern länger als eine Iteration",
                "Testdaten-Anfragen stauen sich",
                "Umgebungs-Buchungen kollidieren",
                "Übergaben zwischen Teams unklar dokumentiert",
                "Review-Kapazität schwankt stark",
                "Deployment-Fenster zu selten")


def is_new_since_prev(entry_id: str) -> bool:
    """Deterministic prev rule: ~1/8 of base entries are new since prev."""
    return zlib.crc32(entry_id.encode("utf-8")) % 8 == 0


def _pick(rng: random.Random, pool: tuple, index: int) -> str:
    """Stable-ish pick: cycle the pool, shifted by a seeded offset."""
    return pool[(index + rng.randrange(len(pool))) % len(pool)]


def _weighted(rng: random.Random, choices: list[tuple[str, int]]) -> str:
    return rng.choices([c for c, _ in choices],
                       weights=[w for _, w in choices], k=1)[0]


class _Gen:
    """Shared generation context handed to the per-register helpers."""

    def __init__(self, rng: random.Random, tag: str, reference: date,
                 art_names: list[str], profile: ScaleProfile,
                 prev: bool) -> None:
        self.rng = rng
        self.tag = tag
        self.reference = reference
        self.art_names = art_names
        self.profile = profile
        self.prev = prev

    def emit(self, target: list, entry_id: str, entry: object) -> None:
        """Append unless the entry is "new since prev" in the prev stand."""
        if not (self.prev and is_new_since_prev(entry_id)):
            target.append(entry)


def populate_registers(
    registers: dict[str, object],
    solution_key: str,
    art_names: list[str],
    reference: date,
    seed: int,
    scale: str = DEFAULT_SCALE,
    prev: bool = False,
) -> None:
    """
    Extend the story-anchor registers with the seeded base population.

    Every random draw happens UNCONDITIONALLY (independent of ``prev``),
    so both stands share one identical base; the drop rule then only
    decides which finished entries exist in the earlier stand.

    Args:
        registers:    {"risks": RiskRegister, "nfr": NfrRegister, ...} —
                      the anchor fixtures, extended in place.
        solution_key: "alpha" / "beta" (ID prefix + seed stream).
        art_names:    The solution's real ART member names (coherence:
                      dependencies/capabilities/trains only reference
                      these — no drift warnings).
        reference:    Scenario reference date (all dates relative).
        seed:         Scenario seed (per-solution stream, story-agnostic).
        scale:        "s" (anchors only), "m", "l".
        prev:         Build the two-weeks-earlier stand (drop rule).

    Raises:
        ValueError: Unknown scale.
    """
    if scale not in SCALE_PROFILES:
        raise ValueError(
            f"Unknown scale '{scale}' — expected one of {', '.join(SCALES)}.")
    g = _Gen(rng=random.Random(f"{seed}:{solution_key}:registers"),
             tag=solution_key[:1].upper(), reference=reference,
             art_names=art_names, profile=SCALE_PROFILES[scale], prev=prev)
    _gen_risks(g, registers["risks"])
    _gen_nfr(g, registers["nfr"])
    _gen_capabilities(g, registers["capabilities"])
    _gen_dependencies(g, registers["dependencies"])
    _gen_decisions(g, registers["decisions"])
    _gen_slo(g, registers["slo"])
    _gen_flow_problems(g, registers["flow_problems"])
    _gen_themes(g, registers["themes"])


def _gen_risks(g: _Gen, risks: RiskRegister) -> None:
    """ROAM mix; aging always < 30 days (the two old ones stay anchors)."""
    for i in range(g.profile.risks):
        rid = f"R-{g.tag}{100 + i}"
        entry = Risk(
            risk_id=rid, title=_pick(g.rng, _RISK_TOPICS, i),
            roam=_weighted(g.rng, [(ROAM_OWNED, 4), (ROAM_MITIGATED, 3),
                                   (ROAM_ACCEPTED, 2), (ROAM_RESOLVED, 2)]),
            owner=_pick(g.rng, _TEAM_POOL, i),
            impact=_weighted(g.rng, [(IMPACT_HIGH, 2), (IMPACT_MEDIUM, 5),
                                     (IMPACT_LOW, 3)]),
            status_since=g.reference - timedelta(days=g.rng.randrange(1, 25)))
        g.emit(risks.risks, rid, entry)


def _gen_nfr(g: _Gen, nfr: NfrRegister) -> None:
    """Never violated, no overdue gap (both stay Beta's anchors)."""
    for i in range(g.profile.nfrs):
        nid = f"NFR-{g.tag}{100 + i}"
        title, target = _NFR_TOPICS[
            (i + g.rng.randrange(3)) % len(_NFR_TOPICS)]
        entry = Nfr(
            nfr_id=nid, title=title, target=target,
            status=_weighted(g.rng, [(STATUS_MET, 7), (STATUS_AT_RISK, 3)]),
            owner=_pick(g.rng, _TEAM_POOL, i))
        g.emit(nfr.nfrs, nid, entry)
    for i in range(g.profile.runway):
        iid = f"RWY-{g.tag}{100 + i}"
        entry = RunwayItem(
            item_id=iid, title=_pick(g.rng, _RUNWAY_TOPICS, i),
            status=_weighted(g.rng, [(RUNWAY_IN_PLACE, 5),
                                     (RUNWAY_BUILDING, 5)]),
            needed_by=g.reference + timedelta(
                days=g.rng.randrange(30, 220)),
            owner=_pick(g.rng, _TEAM_POOL, i + 2))
        g.emit(nfr.runway, iid, entry)


def _gen_capabilities(g: _Gen, caps: CapabilityMap) -> None:
    """healthy/at_risk only; ART lists strictly from the real members."""
    for i in range(g.profile.capabilities):
        cid = f"CAP-{g.tag}{100 + i}"
        entry = Capability(
            cap_id=cid, title=_pick(g.rng, _CAPABILITY_TOPICS, i),
            health=_weighted(g.rng, [(HEALTH_HEALTHY, 7),
                                     (HEALTH_AT_RISK, 3)]),
            arts=g.rng.sample(g.art_names,
                              k=g.rng.randrange(1, len(g.art_names) + 1)),
            owner=_pick(g.rng, _TEAM_POOL, i),
            assessed_on=g.reference - timedelta(
                days=g.rng.randrange(1, 21)))
        g.emit(caps.capabilities, cid, entry)


def _gen_dependencies(g: _Gen, deps: DependencyRegister) -> None:
    """Real ARTs only; never blocked, never overdue, no cross-solution —
    die blockierte, überfällige AD-1 und die Cross-Integration bleiben
    die einzigen ihrer Art (Anker-Invariante)."""
    for i in range(g.profile.dependencies):
        did = f"D-{g.tag}{100 + i}"
        frm, to = g.rng.sample(g.art_names, k=2)
        entry = Dependency(
            dep_id=did, title=f"{to} {_pick(g.rng, _DEP_TOPICS, i)}",
            from_art=frm, to_art=to,
            status=_weighted(g.rng, [(DEP_ON_TRACK, 5), (DEP_AT_RISK, 3),
                                     (DEP_DONE, 2)]),
            due=g.reference + timedelta(days=g.rng.randrange(7, 150)))
        g.emit(deps.dependencies, did, entry)


def _gen_decisions(g: _Gen, log: DecisionLog) -> None:
    """Basis ohne supersedes — die ADR-Kette der Story bleibt die einzige
    (Anker-Invariante); offene Annahmen sind nie überfällig."""
    for i in range(g.profile.decisions):
        eid = f"ADR-{g.tag}{100 + i}"
        entry = LogEntry(
            entry_id=eid, kind=KIND_DECISION,
            title=_pick(g.rng, _DECISION_TOPICS, i),
            status=_weighted(g.rng, [(DECISION_ACCEPTED, 7),
                                     (DECISION_PROPOSED, 3)]),
            owner=_pick(g.rng, _TEAM_POOL, i),
            logged_on=g.reference - timedelta(
                days=g.rng.randrange(5, 200)))
        g.emit(log.entries, eid, entry)
    for i in range(g.profile.assumptions):
        eid = f"AS-{g.tag}{100 + i}"
        entry = LogEntry(
            entry_id=eid, kind=KIND_ASSUMPTION,
            title=_pick(g.rng, _ASSUMPTION_TOPICS, i),
            status=_weighted(g.rng, [(ASSUMPTION_OPEN, 6),
                                     (ASSUMPTION_CONFIRMED, 4)]),
            owner=_pick(g.rng, _TEAM_POOL, i + 3),
            logged_on=g.reference - timedelta(
                days=g.rng.randrange(5, 120)),
            review_by=g.reference + timedelta(
                days=g.rng.randrange(14, 120)))
        g.emit(log.entries, eid, entry)


def _gen_slo(g: _Gen, slo: SloRegister) -> None:
    """met/at_risk mix, never breached (Order Sync stays the only one)."""
    for i in range(g.profile.slos):
        rid = f"SLO-{g.tag}{100 + i}"
        target = g.rng.choice((99.5, 99.9, 99.95))
        # SLI oberhalb des Ziels: Restbudget 5–95 % — zentrale Budget-Regel
        # ergibt met (>=25 % Rest) oder at_risk, nie breached.
        sli = round(target + (100.0 - target) * g.rng.uniform(0.05, 0.95), 3)
        entry = SloRecord(
            service=f"{_pick(g.rng, _SERVICE_POOL, i)} {g.tag}{i}",
            slo="availability", target_pct=target, sli_pct=sli,
            window="30d", source="generated:demo")
        g.emit(slo.records, rid, entry)


def _gen_flow_problems(g: _Gen, flow: FlowProblemRegister) -> None:
    """Conference counter <= 2 (survivors stay FP-A1/FP-B1)."""
    for i in range(g.profile.flow_problems):
        fid = f"FP-{g.tag}{100 + i}"
        entry = FlowProblem(
            problem_id=fid, title=_pick(g.rng, _FLOW_TOPICS, i),
            status=_weighted(g.rng, [(FLOW_OPEN, 4), (FLOW_COMMITTED, 3),
                                     (FLOW_RESOLVED, 3)]),
            value_streams=[g.rng.choice(g.art_names)],
            source=g.rng.choice(g.art_names),
            owner=_pick(g.rng, _TEAM_POOL, i),
            raised_on=g.reference - timedelta(
                days=g.rng.randrange(10, 120)),
            conferences=g.rng.randrange(1, 3))
        g.emit(flow.problems, fid, entry)


def _gen_themes(g: _Gen, themes: ThemesRegister) -> None:
    """
    Coherent and drop-safe: base themes are never "new since prev"
    (otherwise an epic of both stands would reference a theme missing in
    the prev stand); each base theme gets one fixed paired epic so no
    base orphan can ever appear portfolio-wide. Base epics without a
    theme pool are skipped — an empty theme would be an extra zombie.
    """
    base_theme_ids: list[str] = []
    for i in range(g.profile.themes):
        tid = f"T-{g.tag}{100 + i}"
        title = _pick(g.rng, _THEME_TOPICS, i)
        if is_new_since_prev(tid):
            continue
        themes.themes.append(StrategicTheme(theme_id=tid, title=title))
        base_theme_ids.append(tid)
        themes.epics.append(Epic(
            epic_id=f"EP-{g.tag}9{i:02d}", title=f"{title} — Anschub",
            train=g.rng.choice(g.art_names), horizon=HORIZONS[2],
            theme=tid, status=EPIC_PLANNED))
    anchor_theme_ids = [t.theme_id for t in themes.themes
                        if t.theme_id not in base_theme_ids]
    for i in range(g.profile.epics):
        eid = f"EP-{g.tag}{100 + i}"
        theme_pool = base_theme_ids or anchor_theme_ids
        entry = Epic(
            epic_id=eid, title=_pick(g.rng, _EPIC_TOPICS, i),
            train=g.rng.choice(g.art_names),
            horizon=_weighted(g.rng, [(HORIZONS[0], 3), (HORIZONS[1], 3),
                                      (HORIZONS[2], 2), (HORIZONS[3], 1),
                                      (HORIZONS[4], 1)]),
            theme=g.rng.choice(theme_pool) if theme_pool else "",
            status=_weighted(g.rng, [(EPIC_PLANNED, 4),
                                     (EPIC_IN_PROGRESS, 4),
                                     (EPIC_DONE, 2)]))
        if entry.theme:
            g.emit(themes.epics, eid, entry)
