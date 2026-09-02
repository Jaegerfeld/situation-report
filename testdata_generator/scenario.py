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
# =============================================================================

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

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
from portfolio.solution_config import (
    KIND_PORTFOLIO,
    Member,
    SolutionConfig,
    StageMap,
    save_solution_config,
)
from transform_data.processor import process_issues
from transform_data.workflow import parse_workflow
from transform_data.writers import write_cfd, write_issue_times, write_transitions

from .generator import GeneratorConfig, generate

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
    """Generator profile for one demo ART (the built-in story per source)."""
    name: str
    workflow_text: str
    mean_cycle_days: float
    completion_rate: float = 0.7
    todo_rate: float = 0.15
    stale_days: int = 0      # shift the data window back → old data_as_of
    write_cfd: bool = True   # False = source without CFD data
    issue_count: int = 120


def _profiles() -> list[tuple[str, _ArtProfile]]:
    """(solution key, profile) pairs for the six demo ARTs."""
    return [
        ("alpha", _ArtProfile("Alpha-1", _WORKFLOW_ALPHA, mean_cycle_days=12)),
        ("alpha", _ArtProfile("Alpha-2", _WORKFLOW_ALPHA, mean_cycle_days=16)),
        # Der Ausreißer: Cycle Time ~3x der Schwester-ARTs (A3-Hervorhebung).
        ("alpha", _ArtProfile("Alpha-3", _WORKFLOW_ALPHA, mean_cycle_days=45)),
        ("beta", _ArtProfile("Beta-1", _WORKFLOW_BETA, mean_cycle_days=14)),
        ("beta", _ArtProfile("Beta-2", _WORKFLOW_BETA, mean_cycle_days=18)),
        # Die schwache Quelle: kaum begonnene Issues (kein First Date), kein
        # CFD, Datenstand 60 Tage alt (A1-Ampel low, Abdeckung < 100 %).
        ("beta", _ArtProfile("Beta-3", _WORKFLOW_BETA, mean_cycle_days=15,
                             completion_rate=0.15, todo_rate=0.8,
                             stale_days=60, write_cfd=False, issue_count=60)),
    ]


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


def _beta_risks(reference: date) -> RiskRegister:
    """ROAM register of Solution Beta: the second aging owned risk lives here."""
    return RiskRegister(risks=[
        Risk("BR-1", "Data quality of ART Beta-3 blocks solution reporting",
             ROAM_OWNED, owner="ART Beta-3", impact=IMPACT_HIGH,
             status_since=reference - timedelta(days=50),
             notes="Aging: matches the weak-source story of this scenario."),
        Risk("BR-2", "Security review for release milestone not scheduled",
             ROAM_MITIGATED, owner="Shared Services", impact=IMPACT_HIGH,
             status_since=reference - timedelta(days=7),
             notes="Interim: external reviewer booked for next sprint."),
        Risk("BR-3", "Vendor API rate limits during nightly sync",
             ROAM_ACCEPTED, owner="ART Beta-1", impact=IMPACT_MEDIUM,
             status_since=reference - timedelta(days=15)),
        Risk("BR-4", "Duplicate effort with platform team clarified",
             ROAM_RESOLVED, owner="ART Beta-2", impact=IMPACT_LOW,
             status_since=reference - timedelta(days=12)),
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
            RunwayItem("BRW-1", "Automated failover for the sync service",
                       status=RUNWAY_GAP,
                       needed_by=reference - timedelta(days=20),
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

    Returns:
        Dict with the key output paths (portfolio config, solution configs,
        risk registers, PI config, readme).
    """
    reference = reference or date.today()
    out = Path(output_dir)
    (out / "workflows").mkdir(parents=True, exist_ok=True)
    (out / "raw").mkdir(exist_ok=True)
    (out / "arts").mkdir(exist_ok=True)

    workflow_files = {
        "alpha": out / "workflows" / "alpha.txt",
        "beta": out / "workflows" / "beta.txt",
    }
    workflow_files["alpha"].write_text(_WORKFLOW_ALPHA, encoding="utf-8")
    workflow_files["beta"].write_text(_WORKFLOW_BETA, encoding="utf-8")

    members: dict[str, list[Member]] = {"alpha": [], "beta": []}
    for i, (solution_key, profile) in enumerate(_profiles()):
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
            seed=seed + i,
            mean_cycle_days=profile.mean_cycle_days,
        )
        raw = out / "raw" / f"{profile.name}_jira.json"
        raw.write_text(json.dumps(generate(workflow, config), indent=2),
                       encoding="utf-8")

        reference_dt = datetime.combine(
            to_date + timedelta(days=1), datetime.min.time(), tzinfo=UTC)
        records, unmapped = process_issues(raw, workflow, reference_dt=reference_dt)
        if unmapped:
            log(f"  WARNING [{profile.name}]: unmapped statuses {sorted(unmapped)}")

        issue_times = out / "arts" / f"{profile.name}_IssueTimes.xlsx"
        transitions = out / "arts" / f"{profile.name}_Transitions.xlsx"
        write_issue_times(records, workflow, issue_times)
        write_transitions(records, transitions)
        cfd = ""
        if profile.write_cfd:
            cfd_path = out / "arts" / f"{profile.name}_CFD.xlsx"
            write_cfd(records, workflow, cfd_path, reference_dt=reference_dt)
            cfd = str(cfd_path)

        members[solution_key].append(Member(
            name=f"ART {profile.name}",
            issue_times=str(issue_times),
            cfd=cfd,
            workflow=str(wf_file),
            transitions=str(transitions),
        ))
        log(f"  {profile.name}: {len(records)} issues"
            f"{' (kein CFD, Datenstand -' + str(profile.stale_days) + 'd)' if profile.stale_days else ''}")

    risks_alpha = out / "risks_alpha.json"
    save_risks(risks_alpha, _alpha_risks(reference))
    risks_beta = out / "risks_beta.json"
    save_risks(risks_beta, _beta_risks(reference))
    nfr_alpha = out / "nfr_alpha.json"
    save_nfr(nfr_alpha, _alpha_nfr(reference))
    nfr_beta = out / "nfr_beta.json"
    save_nfr(nfr_beta, _beta_nfr(reference))

    solution_alpha = out / "solution_alpha.json"
    save_solution_config(solution_alpha, SolutionConfig(
        name="Solution Alpha", members=members["alpha"],
        from_date=reference - timedelta(days=window_days), to_date=reference,
        risks=str(risks_alpha), nfr=str(nfr_alpha)))
    solution_beta = out / "solution_beta.json"
    save_solution_config(solution_beta, SolutionConfig(
        name="Solution Beta", members=members["beta"],
        from_date=reference - timedelta(days=window_days), to_date=reference,
        stage_map=_BETA_STAGE_MAP, risks=str(risks_beta), nfr=str(nfr_beta)))

    portfolio_cfg = out / "portfolio.json"
    save_solution_config(portfolio_cfg, SolutionConfig(
        name="Demo Portfolio", kind=KIND_PORTFOLIO,
        members=[
            Member(name="Solution Alpha", template=str(solution_alpha)),
            Member(name="Solution Beta", template=str(solution_beta)),
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
        "Solution-Configs einzeln. Eingebaute Geschichten:",
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
        "  (`risks_alpha.json`/`risks_beta.json`); zwei Owned-Risiken sind",
        "  bewusst alt (45/50 Tage) — das Aging springt im Board rot an.",
        "- **NFR & Runway**: beide Solutions bringen ein NFR-Register mit",
        "  (`nfr_alpha.json`/`nfr_beta.json`); Betas API-NFR ist verletzt und",
        "  ein Runway-Element ist eine überfällige Lücke — Dashboard-Ampel rot.",
        "",
        "Die Pfade in den Configs sind absolut — nach dem Verschieben des",
        "Ordners das Szenario neu erzeugen.",
    ]), encoding="utf-8")

    log(f"Szenario komplett: {out}")
    return {"portfolio": portfolio_cfg, "solution_alpha": solution_alpha,
            "solution_beta": solution_beta, "risks_alpha": risks_alpha,
            "risks_beta": risks_beta, "nfr_alpha": nfr_alpha,
            "nfr_beta": nfr_beta, "pi_config": pi_cfg, "readme": readme}
