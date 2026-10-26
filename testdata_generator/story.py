# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       26.10.2026
# Geändert:       26.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Die Geschichte des Demo-Datenraums als Daten (Beta, Schnitt 1a + 2,
#   Entscheidung E2 vom 26.10.2026). Ereignisse adressieren ROLLEN
#   (Ausreißer-ART, schwache Quelle, blockierte Abhängigkeit, Cross-
#   Solution-Naht …), nicht feste Namen; bind_roles() ordnet die Rollen
#   auf die konkrete Struktur zu (Positionen: letzter ART der ersten
#   Solution ist der Ausreißer, letzter ART der zweiten Solution die
#   schwache Quelle …). Was die Struktur nicht hergibt, entfällt mit
#   Hinweis statt Fehler.
#
#   Schnitt 2: vier Vorlagen — Ruhig, Standard-Lage, Eskalation, Erholung.
#   Jedes Ereignis hat einen Schalter (enabled) und ein Stand-Fenster aus
#   Phasen (start, early, mid, late, end), das story_for() für die gewählte
#   Zahl der Stände in Stand-Indizes auflöst. active_events(story, k) sagt
#   dem Generator, welche Ereignisse in Stand k gelten; die Anker der
#   Register und die ART-Profile richten sich danach. Unplausible
#   Schalterkombinationen (Verfall ohne schwache Quelle) werden mit Hinweis
#   durchgelassen, das abhängige Ereignis bleibt aus.
# =============================================================================

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .structure import PortfolioSpec

STORY_SCHEMA = 2

TEMPLATE_CALM = "calm"
TEMPLATE_STANDARD = "standard"
TEMPLATE_ESCALATION = "escalation"
TEMPLATE_RECOVERY = "recovery"
STORY_TEMPLATES = (TEMPLATE_CALM, TEMPLATE_STANDARD, TEMPLATE_ESCALATION, TEMPLATE_RECOVERY)
TEMPLATE_TITLES = {TEMPLATE_CALM: "Ruhig", TEMPLATE_STANDARD: "Standard-Lage",
                   TEMPLATE_ESCALATION: "Eskalation", TEMPLATE_RECOVERY: "Erholung"}
#: Stands a template suggests when the caller names none (E3: Ruhig = ein PI).
SUGGESTED_STANDS = {TEMPLATE_CALM: 3, TEMPLATE_STANDARD: 6,
                    TEMPLATE_ESCALATION: 6, TEMPLATE_RECOVERY: 6}

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

#: Phases of a series of stands; resolved to stand indices per series length.
PHASE_START = "start"
PHASE_EARLY = "early"
PHASE_MID = "mid"
PHASE_LATE = "late"
PHASE_END = "end"
PHASES = (PHASE_START, PHASE_EARLY, PHASE_MID, PHASE_LATE, PHASE_END)
_PHASE_FRACTION = {PHASE_START: 0.0, PHASE_EARLY: 0.25, PHASE_MID: 0.5,
                   PHASE_LATE: 0.75, PHASE_END: 1.0}

#: Event ids of the catalogue (stable: the registers' anchors key on them).
EVENT_OUTLIER = "E1"
EVENT_WEAK_SOURCE = "E2"
EVENT_BLOCKED = "E3"
EVENT_CROSS_SOLUTION = "E4"
EVENT_SEAM = "E5"
EVENT_SLO_BREACH = "E6"
EVENT_HOST_PATTERNS = "E7"
EVENT_WEAK_DECAY = "E8"
EVENT_NEW_RISK = "E9"
EVENT_ROADMAPS = "E10"
EVENT_IDS = (EVENT_OUTLIER, EVENT_WEAK_SOURCE, EVENT_BLOCKED, EVENT_CROSS_SOLUTION,
             EVENT_SEAM, EVENT_SLO_BREACH, EVENT_HOST_PATTERNS, EVENT_WEAK_DECAY,
             EVENT_NEW_RISK, EVENT_ROADMAPS)
#: An event that only makes sense while another one is on.
EVENT_REQUIRES = {EVENT_WEAK_DECAY: EVENT_WEAK_SOURCE}

#: Everything on — the "now" stand of the standard story (anchors' default).
ALL_EVENTS: frozenset[str] = frozenset(EVENT_IDS)


def stand_for_phase(phase: str, stands: int) -> int:
    """1-based stand index of a phase in a series of ``stands`` stands."""
    if phase not in _PHASE_FRACTION:
        raise ValueError(f"Unknown phase '{phase}' — expected one of {', '.join(PHASES)}.")
    return 1 + int((stands - 1) * _PHASE_FRACTION[phase] + 0.5)


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
    """
    One event of the story, bound to a role.

    ``onset``/``until`` are phases; ``stand_from``/``stand_to`` the stand
    indices they resolve to for the story's series (``stand_to`` None =
    through the last stand). ``enabled`` is the switch of the template or
    the user; a disabled event stays in the list so the switch is visible.
    """
    event_id: str
    role: str
    title: str
    effect: str = ""
    enabled: bool = True
    onset: str = PHASE_START
    until: str | None = None
    stand_from: int = 1
    stand_to: int | None = None

    def active_at(self, stand: int) -> bool:
        if not self.enabled or stand < self.stand_from:
            return False
        return self.stand_to is None or stand <= self.stand_to


@dataclass
class Story:
    """The story of one portfolio's data room, resolved against its structure."""
    template: str
    title: str
    summary: list[str]
    stands: int = 6
    roles: dict[str, Any] = field(default_factory=dict)
    notices: list[str] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)
    schema: int = STORY_SCHEMA

    def active_events(self, stand: int) -> frozenset[str]:
        return frozenset(e.event_id for e in self.events if e.active_at(stand))


def active_events(story: Story, stand: int) -> frozenset[str]:
    """Event ids in force at stand ``stand`` (1-based)."""
    return story.active_events(stand)


# --- Templates ---------------------------------------------------------------

#: Per template: event id -> (enabled, onset phase, until phase | None).
_TIMING: dict[str, dict[str, tuple[bool, str, str | None]]] = {
    TEMPLATE_CALM: {eid: (False, PHASE_START, None) for eid in EVENT_IDS},
    TEMPLATE_STANDARD: {
        EVENT_OUTLIER: (True, PHASE_START, None),
        EVENT_WEAK_SOURCE: (True, PHASE_START, None),
        EVENT_SLO_BREACH: (True, PHASE_START, None),
        EVENT_HOST_PATTERNS: (True, PHASE_START, None),
        EVENT_BLOCKED: (True, PHASE_END, None),
        EVENT_CROSS_SOLUTION: (True, PHASE_END, None),
        EVENT_SEAM: (True, PHASE_END, None),
        EVENT_WEAK_DECAY: (True, PHASE_END, None),
        EVENT_NEW_RISK: (True, PHASE_END, None),
        EVENT_ROADMAPS: (True, PHASE_END, None),
    },
    TEMPLATE_ESCALATION: {
        EVENT_OUTLIER: (True, PHASE_START, None),
        EVENT_WEAK_SOURCE: (True, PHASE_START, None),
        EVENT_HOST_PATTERNS: (True, PHASE_START, None),
        EVENT_SLO_BREACH: (True, PHASE_EARLY, None),
        EVENT_BLOCKED: (True, PHASE_MID, None),
        EVENT_WEAK_DECAY: (True, PHASE_LATE, None),
        EVENT_CROSS_SOLUTION: (True, PHASE_LATE, None),
        EVENT_SEAM: (True, PHASE_LATE, None),
        EVENT_NEW_RISK: (True, PHASE_END, None),
        EVENT_ROADMAPS: (True, PHASE_END, None),
    },
    TEMPLATE_RECOVERY: {
        EVENT_OUTLIER: (True, PHASE_START, PHASE_MID),
        EVENT_WEAK_SOURCE: (True, PHASE_START, PHASE_LATE),
        EVENT_BLOCKED: (True, PHASE_START, PHASE_EARLY),
        EVENT_CROSS_SOLUTION: (True, PHASE_START, PHASE_MID),
        EVENT_SEAM: (True, PHASE_START, PHASE_START),
        EVENT_SLO_BREACH: (True, PHASE_START, PHASE_EARLY),
        EVENT_HOST_PATTERNS: (True, PHASE_START, None),
        EVENT_WEAK_DECAY: (False, PHASE_START, None),
        EVENT_NEW_RISK: (False, PHASE_START, None),
        EVENT_ROADMAPS: (False, PHASE_START, None),
    },
}

_SUMMARIES: dict[str, Callable[[str | None, str | None], list[str]]] = {
    TEMPLATE_CALM: lambda outlier, weak: [
        "Ein Portfolio ohne Wendungen: alle ARTs liefern gleichmäßig, die Register tragen "
        "Grundmenge und gesunde Anker.",
        "Die Reihe zeigt Durchsatz und kleine Bewegungen — die Übung ist, ein Lagebild zu lesen, "
        "das nichts Dramatisches sagt.",
        "Wer hier Alarm schlägt, hat das Bild überlesen.",
    ],
    TEMPLATE_STANDARD: lambda outlier, weak: [
        "Ein Portfolio, das auf den ersten Blick ruhig wirkt.",
        (f"Darunter ein Ausreißer-ART ({outlier}), " if outlier else "Darunter ")
        + (f"eine schwache Datenquelle ({weak}) " if weak else "")
        + "und Nähte zwischen den Value Streams, die mit dem letzten Stand sichtbar unter Druck "
          "geraten.",
        "Die Register erzählen dieselbe Lage aus jeder Richtung — Risiken, Abhängigkeiten, "
        "Annahmen, SLOs und Wecker zeigen auf dieselben Stellen.",
    ],
    TEMPLATE_ESCALATION: lambda outlier, weak: [
        "Eine Lage, die sich Stand für Stand verschärft.",
        (f"Zuerst reißt ein SLO, dann blockiert der Ausreißer ({outlier}) seine Naht, " if outlier
         else "Zuerst reißt ein SLO, dann blockiert eine Naht, ")
        + (f"dann verfällt die Datenqualität von {weak} und die Cross-Solution-Nähte kippen."
           if weak else "dann kippen die Nähte zwischen den Value Streams."),
        "Am Ende kommen ein neues Sicherheitsrisiko und geänderte Roadmaps dazu — der Wecker hätte "
        "früher klingeln müssen.",
    ],
    TEMPLATE_RECOVERY: lambda outlier, weak: [
        "Eine Lage, die schlecht beginnt und sich erholt.",
        (f"Stand 1 zeigt den Ausreißer ({outlier}), " if outlier else "Stand 1 zeigt ")
        + "blockierte und gefährdete Nähte, ein gerissenes SLO"
        + (f" und die schwache Quelle {weak}." if weak else "."),
        "Dann werden Nähte gelöst, das SLO hält wieder, der Ausreißer findet seinen Takt, zuletzt "
        "heilt die Datenquelle — nur die stillen Muster der ersten Solution bleiben.",
    ],
}


def _art(name: str) -> str:
    return f"ART {name}"


def _catalogue(binding: RoleBinding, tags: dict[str, str]) -> list[tuple[str, str, str, str]]:
    """(event id, role, title, effect) for every event the binding can host."""
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

    events: list[tuple[str, str, str, str]] = []
    if outlier:
        events.append((EVENT_OUTLIER, ROLE_OUTLIER_ART,
                       f"{_art(outlier)} ist der Ausreißer (Cycle Time etwa 3×).",
                       f"Comparison-Report: Median/P95 rot markiert; Wecker DP-{ht}1 (P85 über "
                       f"30 Tagen) ausgelöst; Delivery-Bild selten und langsam; Capability "
                       f"{ht}C-2 at risk."))
    if weak:
        events.append((EVENT_WEAK_SOURCE, ROLE_WEAK_SOURCE_ART,
                       f"{_art(weak)} liefert schwache Daten (kein CFD, kaum First Dates, "
                       f"Datenstand 60 Tage alt).",
                       f"Konfidenz medium; Risiko {st}R-1 altert (50 Tage); Capability {st}C-1 "
                       f"kritisch; Flussproblem FP-{st}1 überlebt vier Konferenzen; Annahme "
                       f"AS-{st}1 überschreitet ihr Prüfdatum; DORA/Qualität low."))
    if blocked:
        events.append((EVENT_BLOCKED, ROLE_BLOCKED_DEPENDENCY,
                       f"{_art(blocked[0])} → {_art(blocked[1])} ist blockiert und überfällig.",
                       f"Abhängigkeit {ht}D-1: at_risk → blocked; Heatmap rot; Wecker DP-{ht}3 "
                       f"(zwei blockierte) unterschwellig."))
    if cross:
        events.append((EVENT_CROSS_SOLUTION, ROLE_CROSS_SOLUTION_DEPENDENCY,
                       f"{_art(cross[0])} → {_art(cross[1])} ist eine Cross-Solution-Naht; der "
                       f"Druck zwischen den Value Streams steigt.",
                       f"{st}D-1 at_risk, {st}D-3 at_risk → blocked, {ht}D-4 on_track → at_risk — "
                       f"nur im Portfolio-Report sichtbar; Grundlage des "
                       f"Entscheidungspunkt-Indikators (P4)."))
    if seam:
        events.append((EVENT_SEAM, ROLE_RECURRING_SEAM,
                       f"Die Naht {_art(seam[0])} × {_art(seam[1])} öffnet zum dritten Mal eine "
                       f"Solution Area zum selben Thema (test environment).",
                       f"SA-{ht}1, SA-{ht}2 geschlossen, SA-{ht}3 neu — das EA-Signal (P5): "
                       f"Schnitt oder Architektur prüfen, nicht die Teams."))
    if slo_sol:
        events.append((EVENT_SLO_BREACH, ROLE_SLO_BREACH_SOLUTION,
                       f"„Order Sync API“ in Solution {slo_sol} reißt sein SLO.",
                       f"SLO-Register: breached; NFR {st}N-1 (API response time) verletzt; "
                       f"Runway-Lücke {st}RW-1 überfällig."))
    if host:
        events.append((EVENT_HOST_PATTERNS, ROLE_HOST_SOLUTION,
                       f"Solution {host} wirkt gesund — mit den stillen Mustern.",
                       f"Risiko {ht}R-1 seit 45 Tagen owned (Aging); Theme T-{ht}2 ohne Epic "
                       f"(„declared & forgotten“); Flussproblem FP-{ht}1 überlebt drei "
                       f"Konferenzen; Capability {ht}C-3 ohne ART (uncovered); SLO „Checkout“ "
                       f"at risk."))
    if weak:
        events.append((EVENT_WEAK_DECAY, ROLE_WEAK_SOURCE_ART,
                       f"Die Datenqualität von {_art(weak)} verfällt weiter.",
                       "Anteil der Vorgänge ohne First Date steigt auf 80 % — Konfidenz medium → "
                       "low, Abdeckung im Titel sichtbar."))
    if second:
        events.append((EVENT_NEW_RISK, ROLE_SECOND_SOLUTION,
                       f"Neues Risiko in Solution {second}: Security-Review nicht terminiert.",
                       f"Risiko {st}R-2 (mitigated, hoch) erscheint — im Delta-Briefing als neu."))
    if host:
        events.append((EVENT_ROADMAPS, ROLE_HOST_SOLUTION,
                       "Roadmaps aktualisiert.",
                       f"Epic EP-{ht}9 verliert sein Theme (Zombie-Initiative)"
                       + (f"; Epic EP-{st}2 wird von P2 nach P1 gezogen." if second else ".")))
    return events


def parse_switches(values: list[str] | None) -> dict[str, bool]:
    """
    'E3=off', 'E6=on' -> {"E3": False, "E6": True}.

    Raises:
        ValueError: unknown event id or value.
    """
    switches: dict[str, bool] = {}
    for raw in values or []:
        text = str(raw).strip()
        if "=" not in text:
            raise ValueError(f"event switch '{text}': expected ID=on|off.")
        eid, value = (p.strip() for p in text.split("=", 1))
        if eid.upper() not in EVENT_IDS:
            raise ValueError(f"event switch '{text}': unknown event id — known: "
                             f"{', '.join(EVENT_IDS)}.")
        if value.lower() not in ("on", "off", "true", "false", "1", "0"):
            raise ValueError(f"event switch '{text}': value must be on or off.")
        switches[eid.upper()] = value.lower() in ("on", "true", "1")
    return switches


def story_for(template: str, binding: RoleBinding, tags: dict[str, str] | None = None,
              stands: int = 6, switches: dict[str, bool] | None = None) -> Story:
    """
    Build the story of a template for a bound structure and a series length.

    Events the binding cannot host are left out (the binding's notices say
    why). ``switches`` override the template's enabled flags per event id;
    an event whose prerequisite is off (EVENT_REQUIRES) is switched off
    with a notice instead of raising.

    Raises:
        ValueError: unknown template.
    """
    if template not in STORY_TEMPLATES:
        raise ValueError(f"Unknown story template '{template}' — expected one of "
                         f"{', '.join(STORY_TEMPLATES)}.")
    tags = tags or {}
    switches = switches or {}
    timing = _TIMING[template]
    notices = list(binding.notices)
    events: list[Event] = []
    for eid, role, title, effect in _catalogue(binding, tags):
        enabled, onset, until = timing[eid]
        if eid in switches:
            enabled = switches[eid]
        events.append(Event(eid, role, title, effect, enabled, onset, until,
                            stand_from=stand_for_phase(onset, stands),
                            stand_to=None if until is None else stand_for_phase(until, stands)))
    by_id = {e.event_id: e for e in events}
    for eid, needs in EVENT_REQUIRES.items():
        event = by_id.get(eid)
        if event is not None and event.enabled and not (needs in by_id and by_id[needs].enabled):
            event.enabled = False
            notices.append(f"{eid} braucht {needs} — bleibt aus, weil {needs} nicht aktiv ist.")
    unknown = sorted(set(switches) - set(by_id))
    if unknown:
        notices.append("Schalter ohne Ereignis in dieser Struktur (ignoriert): "
                       + ", ".join(unknown) + ".")
    outlier = binding.art(ROLE_OUTLIER_ART)
    weak = binding.art(ROLE_WEAK_SOURCE_ART)
    return Story(template=template, title=TEMPLATE_TITLES[template],
                 summary=_SUMMARIES[template](outlier, weak), stands=stands,
                 roles=dict(binding.roles), notices=notices, events=events)


def standard_story(binding: RoleBinding, tags: dict[str, str] | None = None,
                   stands: int = 6) -> Story:
    """The built-in story of the demo portfolio („Standard-Lage")."""
    return story_for(TEMPLATE_STANDARD, binding, tags, stands)


# --- Serialisation ----------------------------------------------------------

def story_to_dict(story: Story) -> dict[str, Any]:
    return {
        "schema": story.schema,
        "template": story.template,
        "title": story.title,
        "stands": story.stands,
        "summary": list(story.summary),
        "roles": dict(story.roles),
        "notices": list(story.notices),
        "events": [
            {"id": e.event_id, "role": e.role, "enabled": e.enabled,
             "onset": e.onset, "until": e.until,
             "stand_from": e.stand_from, "stand_to": e.stand_to,
             "title": e.title, "effect": e.effect}
            for e in story.events],
    }


def story_from_dict(data: Any) -> Story:
    """
    Parse story.json; raises ValueError on malformed input.

    Schema 1 files (one template, ``when`` always|now) are read as well:
    always = start, now = end.
    """
    if not isinstance(data, dict):
        raise ValueError("story must be a JSON object.")
    template = str(data.get("template", ""))
    if template not in STORY_TEMPLATES:
        raise ValueError(f"story template '{template}' unknown — expected "
                         f"one of {', '.join(STORY_TEMPLATES)}.")
    try:
        stands = int(data.get("stands", 6))
    except (TypeError, ValueError) as exc:
        raise ValueError("'stands' must be an integer.") from exc
    raw_events = data.get("events", [])
    if not isinstance(raw_events, list):
        raise ValueError("'events' must be a list.")
    events: list[Event] = []
    for raw in raw_events:
        if not isinstance(raw, dict):
            raise ValueError("each event must be an object.")
        role = str(raw.get("role", ""))
        if role not in ROLES:
            raise ValueError(f"event '{raw.get('id', '?')}': role '{role}' unknown.")
        if "when" in raw and "onset" not in raw:      # schema 1
            when = str(raw.get("when"))
            if when not in ("always", "now"):
                raise ValueError(f"event '{raw.get('id', '?')}': when '{when}' must be "
                                 f"'always' or 'now'.")
            onset: str = PHASE_START if when == "always" else PHASE_END
            until: str | None = None
        else:
            onset = str(raw.get("onset", PHASE_START))
            until_raw = raw.get("until")
            until = None if until_raw in (None, "") else str(until_raw)
            for phase in (onset, until):
                if phase is not None and phase not in PHASES:
                    raise ValueError(f"event '{raw.get('id', '?')}': phase '{phase}' unknown.")
        stand_to_raw = raw.get("stand_to")
        events.append(Event(
            str(raw.get("id", "")), role, str(raw.get("title", "")),
            str(raw.get("effect", "")), bool(raw.get("enabled", True)), onset, until,
            stand_from=int(raw.get("stand_from", stand_for_phase(onset, stands))),
            stand_to=(None if stand_to_raw is None
                      else int(stand_to_raw)) if "stand_to" in raw
            else (None if until is None else stand_for_phase(until, stands))))
    roles = data.get("roles", {})
    if not isinstance(roles, dict):
        raise ValueError("'roles' must be an object.")
    summary = data.get("summary", [])
    if not isinstance(summary, list):
        raise ValueError("'summary' must be a list of sentences.")
    return Story(template=template, title=str(data.get("title", TEMPLATE_TITLES[template])),
                 summary=[str(s) for s in summary], stands=stands, roles=dict(roles),
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
