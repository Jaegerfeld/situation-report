# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       26.10.2026
# Geändert:       30.10.2026
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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .i18n import DEFAULT_LANG, template_title
from .i18n import t as _t
from .structure import PortfolioSpec

STORY_SCHEMA = 2

TEMPLATE_CALM = "calm"
TEMPLATE_STANDARD = "standard"
TEMPLATE_ESCALATION = "escalation"
TEMPLATE_RECOVERY = "recovery"
STORY_TEMPLATES = (TEMPLATE_CALM, TEMPLATE_STANDARD, TEMPLATE_ESCALATION, TEMPLATE_RECOVERY)
#: Titles in the default language (English); ``template_title(id, lang)`` for the others.
TEMPLATE_TITLES = {tpl: template_title(tpl) for tpl in STORY_TEMPLATES}
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


def bind_roles(portfolio: PortfolioSpec, lang: str = DEFAULT_LANG) -> RoleBinding:
    """
    Map the story roles onto a concrete portfolio structure.

    Positions, not names: the first solution hosts the outlier (its last
    ART, needs >= 2 ARTs), the blocked dependency and the recurring seam
    (first -> last ART); the second solution hosts the weak source (its
    last ART), the SLO breach and the cross-solution dependency (its first
    ART -> the host's first ART). Missing positions are reported as
    notices and leave the role unbound. ``lang`` is the language of the
    notices (they end up in story.json and the README).
    """
    b = RoleBinding()
    if not portfolio.solutions:
        b.notices.append(_t("notice.no_solution", lang))
        return b
    host = portfolio.solutions[0]
    b.roles[ROLE_HOST_SOLUTION] = host.short
    if len(host.arts) >= 2:
        b.roles[ROLE_OUTLIER_ART] = host.arts[-1]
        b.roles[ROLE_BLOCKED_DEPENDENCY] = [host.arts[0], host.arts[-1]]
        b.roles[ROLE_RECURRING_SEAM] = [host.arts[0], host.arts[-1]]
    else:
        b.notices.append(_t("notice.one_art_host", lang, solution=host.display_name))
    if len(portfolio.solutions) >= 2:
        second = portfolio.solutions[1]
        b.roles[ROLE_SECOND_SOLUTION] = second.short
        b.roles[ROLE_WEAK_SOURCE_ART] = second.arts[-1]
        b.roles[ROLE_SLO_BREACH_SOLUTION] = second.short
        b.roles[ROLE_CROSS_SOLUTION_DEPENDENCY] = [second.arts[0], host.arts[0]]
        if len(second.arts) < 2:
            b.notices.append(_t("notice.one_art_second", lang, solution=second.display_name))
    else:
        b.notices.append(_t("notice.one_solution", lang))
    if len(portfolio.solutions) > 2:
        others = ", ".join(s.display_name for s in portfolio.solutions[2:])
        b.notices.append(_t("notice.anchor_free", lang, others=others))
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

def _summary(template: str, outlier: str | None, weak: str | None, lang: str) -> list[str]:
    """The three summary sentences of a template, with the bound roles filled in."""
    def s(key: str, **kw: object) -> str:
        return _t(f"sum.{key}", lang, **kw)

    if template == TEMPLATE_CALM:
        return [s("calm.1"), s("calm.2"), s("calm.3")]
    if template == TEMPLATE_STANDARD:
        return [s("standard.1"),
                s("standard.2", outlier=s("part.outlier", outlier=outlier) if outlier else "",
                  weak=s("part.weak", weak=weak) if weak else ""),
                s("standard.3")]
    if template == TEMPLATE_ESCALATION:
        return [s("escalation.1"),
                s("escalation.2",
                  blocks=s("part.blocks_outlier", outlier=outlier) if outlier else s("part.blocks_plain"),
                  decay=s("part.decay_weak", weak=weak) if weak else s("part.decay_plain")),
                s("escalation.3")]
    return [s("recovery.1"),
            s("recovery.2", outlier=s("part.rec_outlier", outlier=outlier) if outlier else "",
              weak=s("part.rec_weak", weak=weak) if weak else "."),
            s("recovery.3")]


def _art(name: str) -> str:
    return f"ART {name}"


def _catalogue(binding: RoleBinding, tags: dict[str, str],
               lang: str = DEFAULT_LANG) -> list[tuple[str, str, str, str]]:
    """(event id, role, title, effect) for every event the binding can host, in ``lang``."""
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

    def add(eid: str, role: str, **kw: object) -> None:
        events.append((eid, role, _t(f"ev.{eid}.title", lang, **kw),
                       _t(f"ev.{eid}.effect", lang, **kw)))

    if outlier:
        add(EVENT_OUTLIER, ROLE_OUTLIER_ART, art=_art(outlier), ht=ht)
    if weak:
        add(EVENT_WEAK_SOURCE, ROLE_WEAK_SOURCE_ART, art=_art(weak), st=st)
    if blocked:
        add(EVENT_BLOCKED, ROLE_BLOCKED_DEPENDENCY, a=_art(blocked[0]), b=_art(blocked[1]), ht=ht)
    if cross:
        add(EVENT_CROSS_SOLUTION, ROLE_CROSS_SOLUTION_DEPENDENCY,
            a=_art(cross[0]), b=_art(cross[1]), ht=ht, st=st)
    if seam:
        add(EVENT_SEAM, ROLE_RECURRING_SEAM, a=_art(seam[0]), b=_art(seam[1]), ht=ht)
    if slo_sol:
        add(EVENT_SLO_BREACH, ROLE_SLO_BREACH_SOLUTION, sol=slo_sol, st=st)
    if host:
        add(EVENT_HOST_PATTERNS, ROLE_HOST_SOLUTION, host=host, ht=ht)
    if weak:
        add(EVENT_WEAK_DECAY, ROLE_WEAK_SOURCE_ART, art=_art(weak))
    if second:
        add(EVENT_NEW_RISK, ROLE_SECOND_SOLUTION, second=second, st=st)
    if host:
        add(EVENT_ROADMAPS, ROLE_HOST_SOLUTION, ht=ht,
            second_part=_t("ev.E10.second", lang, st=st) if second else ".")
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
              stands: int = 6, switches: dict[str, bool] | None = None,
              lang: str = DEFAULT_LANG) -> Story:
    """
    Build the story of a template for a bound structure and a series length.

    Events the binding cannot host are left out (the binding's notices say
    why). ``switches`` override the template's enabled flags per event id;
    an event whose prerequisite is off (EVENT_REQUIRES) is switched off
    with a notice instead of raising. ``lang`` is the language of title,
    summary, event texts and notices (one of the five suite languages;
    anything else is English).

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
    for eid, role, title, effect in _catalogue(binding, tags, lang):
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
            notices.append(_t("notice.requires", lang, eid=eid, needs=needs))
    unknown = sorted(set(switches) - set(by_id))
    if unknown:
        notices.append(_t("notice.unknown_switch", lang, ids=", ".join(unknown)))
    outlier = binding.art(ROLE_OUTLIER_ART)
    weak = binding.art(ROLE_WEAK_SOURCE_ART)
    return Story(template=template, title=template_title(template, lang),
                 summary=_summary(template, outlier, weak, lang), stands=stands,
                 roles=dict(binding.roles), notices=notices, events=events)


def standard_story(binding: RoleBinding, tags: dict[str, str] | None = None,
                   stands: int = 6, lang: str = DEFAULT_LANG) -> Story:
    """The built-in story of the demo portfolio („Standard-Lage")."""
    return story_for(TEMPLATE_STANDARD, binding, tags, stands, lang=lang)


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
