# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       26.10.2026
# Geändert:       26.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Die Geschichte des Demo-Datenraums als Daten (Beta, Schnitt 1a,
#   Entscheidung E2 vom 26.10.2026). Ereignisse adressieren ROLLEN
#   (Ausreißer-ART, schwache Quelle, blockierte Abhängigkeit, Cross-
#   Solution-Naht …), nicht feste Namen; bind_roles() ordnet die Rollen
#   auf die konkrete Struktur zu (Positionen: letzter ART der ersten
#   Solution ist der Ausreißer, letzter ART der zweiten Solution die
#   schwache Quelle …). Was die Struktur nicht hergibt (eine Solution ->
#   keine Cross-Solution-Naht), entfällt mit Hinweis statt Fehler.
#
#   Schnitt 1a trägt die heutige Geschichte als einzige Vorlage
#   („Standard-Lage"); Ruhig, Eskalation, Erholung und die Ereignis-
#   Schalter folgen in Schnitt 2. `story.json` liegt im Datenraum neben
#   `structure.json` und ist die Quelle der README-Erzählung.
# =============================================================================

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .structure import PortfolioSpec

STORY_SCHEMA = 1

TEMPLATE_STANDARD = "standard"
STORY_TEMPLATES = (TEMPLATE_STANDARD,)

ROLE_HOST_SOLUTION = "host_solution"
ROLE_SECOND_SOLUTION = "second_solution"
ROLE_OUTLIER_ART = "outlier_art"
ROLE_WEAK_SOURCE_ART = "weak_source_art"
ROLE_BLOCKED_DEPENDENCY = "blocked_dependency"
ROLE_CROSS_SOLUTION_DEPENDENCY = "cross_solution_dependency"
ROLE_RECURRING_SEAM = "recurring_seam"
ROLE_SLO_BREACH_SOLUTION = "slo_breach_solution"
ROLES = (ROLE_HOST_SOLUTION, ROLE_SECOND_SOLUTION, ROLE_OUTLIER_ART,
         ROLE_WEAK_SOURCE_ART, ROLE_BLOCKED_DEPENDENCY,
         ROLE_CROSS_SOLUTION_DEPENDENCY, ROLE_RECURRING_SEAM,
         ROLE_SLO_BREACH_SOLUTION)

#: When an event is visible: in every stand, or only from the latest one
#: (the prev stand of the Delta-Briefing does not have it yet).
WHEN_ALWAYS = "always"
WHEN_NOW = "now"


@dataclass
class RoleBinding:
    """Resolved roles of one portfolio (short names) plus the notices."""
    roles: dict[str, Any] = field(default_factory=dict)
    notices: list[str] = field(default_factory=list)

    def get(self, role: str) -> Any:
        return self.roles.get(role)

    def has(self, role: str) -> bool:
        return self.roles.get(role) is not None

    def art(self, role: str) -> str | None:
        """Short ART name of a single-ART role, or None."""
        value = self.roles.get(role)
        return value if isinstance(value, str) else None

    def pair(self, role: str) -> tuple[str, str] | None:
        value = self.roles.get(role)
        if isinstance(value, list) and len(value) == 2:
            return value[0], value[1]
        return None


def bind_roles(portfolio: PortfolioSpec) -> RoleBinding:
    """
    Map the story roles onto a concrete portfolio structure.

    Positions, not names: the first solution hosts the outlier (its last
    ART, needs >= 2 ARTs), the blocked dependency and the recurring seam
    (first -> last ART); the second solution hosts the weak source (its
    last ART), the SLO breach and the cross-solution dependency (its first
    ART -> the host's first ART). Missing positions are reported as
    notices and leave the role unbound.
    """
    b = RoleBinding()
    if not portfolio.solutions:
        b.notices.append("Portfolio ohne Solution — keine Geschichte.")
        return b
    host = portfolio.solutions[0]
    b.roles[ROLE_HOST_SOLUTION] = host.short
    if len(host.arts) >= 2:
        b.roles[ROLE_OUTLIER_ART] = host.arts[-1]
        b.roles[ROLE_BLOCKED_DEPENDENCY] = [host.arts[0], host.arts[-1]]
        b.roles[ROLE_RECURRING_SEAM] = [host.arts[0], host.arts[-1]]
    else:
        b.notices.append(
            f"{host.display_name} hat nur einen ART — kein Ausreißer, keine "
            f"blockierte Abhängigkeit, keine wiederkehrende Naht.")
    if len(portfolio.solutions) >= 2:
        second = portfolio.solutions[1]
        b.roles[ROLE_SECOND_SOLUTION] = second.short
        b.roles[ROLE_WEAK_SOURCE_ART] = second.arts[-1]
        b.roles[ROLE_SLO_BREACH_SOLUTION] = second.short
        b.roles[ROLE_CROSS_SOLUTION_DEPENDENCY] = [second.arts[0], host.arts[0]]
        if len(second.arts) < 2:
            b.notices.append(
                f"{second.display_name} hat nur einen ART — er ist zugleich "
                f"die schwache Quelle und der Partner der Cross-Solution-Naht.")
    else:
        b.notices.append(
            "Nur eine Solution — keine schwache Quelle, kein SLO-Bruch in "
            "einer zweiten Solution, keine Cross-Solution-Abhängigkeit.")
    if len(portfolio.solutions) > 2:
        others = ", ".join(s.display_name for s in portfolio.solutions[2:])
        b.notices.append(
            f"Ohne Story-Anker (nur seed-erzeugte Grundmenge): {others}.")
    return b


@dataclass
class Event:
    """One event of the story, bound to a role."""
    event_id: str
    role: str
    when: str
    title: str
    effect: str = ""


@dataclass
class Story:
    """The story of one portfolio's data room, resolved against its structure."""
    template: str
    title: str
    summary: list[str]
    roles: dict[str, Any] = field(default_factory=dict)
    notices: list[str] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)
    schema: int = STORY_SCHEMA


def _art(name: str) -> str:
    return f"ART {name}"


def standard_story(binding: RoleBinding,
                   tags: dict[str, str] | None = None) -> Story:
    """
    The built-in story of the demo portfolio („Standard-Lage"), written
    against the bound roles. Events whose role is unbound are left out;
    the binding's notices say why.

    Args:
        binding: Result of bind_roles().
        tags:    Solution short name -> register ID tag ("A", "B"); used to
                 quote the anchor IDs trainers will meet in the registers.
    """
    tags = tags or {}
    host = binding.get(ROLE_HOST_SOLUTION) or ""
    second = binding.get(ROLE_SECOND_SOLUTION) or ""
    ht = tags.get(host, "A")
    st = tags.get(second, "B")
    outlier = binding.art(ROLE_OUTLIER_ART)
    weak = binding.art(ROLE_WEAK_SOURCE_ART)
    blocked = binding.pair(ROLE_BLOCKED_DEPENDENCY)
    cross = binding.pair(ROLE_CROSS_SOLUTION_DEPENDENCY)
    seam = binding.pair(ROLE_RECURRING_SEAM)
    slo_sol = binding.get(ROLE_SLO_BREACH_SOLUTION)

    events: list[Event] = []
    if outlier:
        events.append(Event(
            "E1", ROLE_OUTLIER_ART, WHEN_ALWAYS,
            f"{_art(outlier)} ist der Ausreißer (Cycle Time etwa 3×).",
            f"Comparison-Report: Median/P95 rot markiert; Wecker DP-{ht}1 (P85 "
            f"über 30 Tagen) ausgelöst; Delivery-Bild selten und langsam; "
            f"Epic EP-{ht}9 verliert im neuesten Stand sein Theme (Zombie)."))
    if weak:
        events.append(Event(
            "E2", ROLE_WEAK_SOURCE_ART, WHEN_ALWAYS,
            f"{_art(weak)} liefert schwache Daten (kein CFD, kaum First Dates, "
            f"Datenstand 60 Tage alt).",
            f"Konfidenz medium (Stand davor) → low (jetzt); Risiko {st}R-1 altert "
            f"(50 Tage); Capability {st}C-1 kritisch; Flussproblem FP-{st}1 überlebt "
            f"vier Konferenzen; Annahme AS-{st}1 überschreitet ihr Prüfdatum; "
            f"Epic EP-{st}2 von P2 nach P1 gezogen; DORA/Qualität low."))
    if blocked:
        events.append(Event(
            "E3", ROLE_BLOCKED_DEPENDENCY, WHEN_NOW,
            f"{_art(blocked[0])} → {_art(blocked[1])} ist blockiert und überfällig.",
            f"Abhängigkeit {ht}D-1: at_risk (Stand davor) → blocked (jetzt); "
            f"Heatmap rot; Wecker DP-{ht}3 (zwei blockierte) unterschwellig."))
    if cross:
        events.append(Event(
            "E4", ROLE_CROSS_SOLUTION_DEPENDENCY, WHEN_NOW,
            f"{_art(cross[0])} → {_art(cross[1])} ist eine Cross-Solution-Naht; "
            f"der Druck zwischen den Value Streams steigt.",
            f"{st}D-1 at_risk, {st}D-3 at_risk → blocked, {ht}D-4 on_track → "
            f"at_risk — nur im Portfolio-Report sichtbar; Grundlage des "
            f"Entscheidungspunkt-Indikators (P4)."))
    if seam:
        events.append(Event(
            "E5", ROLE_RECURRING_SEAM, WHEN_NOW,
            f"Die Naht {_art(seam[0])} × {_art(seam[1])} öffnet zum dritten Mal "
            f"eine Solution Area zum selben Thema (test environment).",
            f"SA-{ht}1, SA-{ht}2 geschlossen, SA-{ht}3 neu im jetzigen Stand — das "
            f"EA-Signal (P5): Schnitt oder Architektur prüfen, nicht die Teams."))
    if slo_sol:
        events.append(Event(
            "E6", ROLE_SLO_BREACH_SOLUTION, WHEN_ALWAYS,
            f"„Order Sync API“ in Solution {slo_sol} reißt sein SLO.",
            f"SLO-Register: breached; NFR {st}N-1 (API response time) verletzt; "
            f"Runway-Lücke {st}RW-1 im jetzigen Stand frisch überfällig; Risiko "
            f"{st}R-2 neu."))
    if host:
        events.append(Event(
            "E7", ROLE_HOST_SOLUTION, WHEN_ALWAYS,
            f"Solution {host} wirkt gesund — mit den stillen Mustern.",
            f"Risiko {ht}R-1 seit 45 Tagen owned (Aging); Theme T-{ht}2 ohne Epic "
            f"(„declared & forgotten“); Flussproblem FP-{ht}1 überlebt drei "
            f"Konferenzen; Capability {ht}C-3 ohne ART (uncovered); SLO "
            f"„Checkout“ at risk; Entscheidung ADR-{ht}1 ersetzt ADR-{ht}2."))

    summary = [
        "Ein Portfolio, das auf den ersten Blick ruhig wirkt.",
        (f"Darunter ein Ausreißer-ART ({outlier}), " if outlier else "Darunter ")
        + (f"eine schwache Datenquelle ({weak}) " if weak else "")
        + "und Nähte zwischen den Value Streams, die zwischen zwei Ständen "
          "sichtbar unter Druck geraten.",
        "Die Register erzählen dieselbe Lage aus jeder Richtung — Risiken, "
        "Abhängigkeiten, Annahmen, SLOs und Wecker zeigen auf dieselben Stellen.",
    ]
    return Story(template=TEMPLATE_STANDARD, title="Standard-Lage",
                 summary=summary, roles=dict(binding.roles),
                 notices=list(binding.notices), events=events)


# --- Serialisation ----------------------------------------------------------

def story_to_dict(story: Story) -> dict[str, Any]:
    return {
        "schema": story.schema,
        "template": story.template,
        "title": story.title,
        "summary": list(story.summary),
        "roles": dict(story.roles),
        "notices": list(story.notices),
        "events": [
            {"id": e.event_id, "role": e.role, "when": e.when,
             "title": e.title, "effect": e.effect}
            for e in story.events],
    }


def story_from_dict(data: Any) -> Story:
    """Parse story.json; raises ValueError on malformed input."""
    if not isinstance(data, dict):
        raise ValueError("story must be a JSON object.")
    template = str(data.get("template", ""))
    if template not in STORY_TEMPLATES:
        raise ValueError(f"story template '{template}' unknown — expected "
                         f"one of {', '.join(STORY_TEMPLATES)}.")
    raw_events = data.get("events", [])
    if not isinstance(raw_events, list):
        raise ValueError("'events' must be a list.")
    events: list[Event] = []
    for raw in raw_events:
        if not isinstance(raw, dict):
            raise ValueError("each event must be an object.")
        role = str(raw.get("role", ""))
        if role not in ROLES:
            raise ValueError(f"event '{raw.get('id', '?')}': role '{role}' "
                             f"unknown.")
        when = str(raw.get("when", WHEN_ALWAYS))
        if when not in (WHEN_ALWAYS, WHEN_NOW):
            raise ValueError(f"event '{raw.get('id', '?')}': when '{when}' "
                             f"must be '{WHEN_ALWAYS}' or '{WHEN_NOW}'.")
        events.append(Event(str(raw.get("id", "")), role, when,
                            str(raw.get("title", "")),
                            str(raw.get("effect", ""))))
    roles = data.get("roles", {})
    if not isinstance(roles, dict):
        raise ValueError("'roles' must be an object.")
    summary = data.get("summary", [])
    if not isinstance(summary, list):
        raise ValueError("'summary' must be a list of sentences.")
    return Story(template=template, title=str(data.get("title", "")),
                 summary=[str(s) for s in summary], roles=dict(roles),
                 notices=[str(n) for n in data.get("notices", [])],
                 events=events, schema=int(data.get("schema", STORY_SCHEMA)))


def load_story(path: Path) -> Story:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: not valid JSON ({exc}).") from exc
    return story_from_dict(data)


def save_story(path: Path, story: Story) -> None:
    Path(path).write_text(json.dumps(story_to_dict(story), indent=2,
                                     ensure_ascii=False) + "\n",
                          encoding="utf-8")
