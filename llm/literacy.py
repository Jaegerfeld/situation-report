# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       17.10.2026
# Geändert:       17.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   KI-Kompetenz-Log nach Art. 4 KI-VO (Rechts-Kandidat R4, nach Rohrlich
#   B.5 / BNetzA-Hinweispapier „KI-Kompetenzen nach Artikel 4"): Der
#   Betreiber dokumentiert die Maßnahmen, mit denen er die KI-Kompetenz
#   seiner Teams sicherstellt — Art, Umfang, Inhalt, Teams, Teilnehmerzahl,
#   nie Namen (Leitplanke b; Namenslisten bleiben im HR-System, das Log
#   verweist dorthin). `python -m llm literacy LOG.json` baut daraus den
#   Nachweis-Bericht: je Team der Stand (aktuell · auffrischen fällig ·
#   keine Maßnahme), die genutzten KI-Funktionen aus dem Betreiber-Nachweis
#   als Bedarfsbild (Zweck → Thema; nicht abgedeckte Themen als Hinweis,
#   keine Bewertung) und das Angebot des Curriculums je Thema. Einschätzung,
#   keine Rechtsberatung: Art. 4 nennt die Dokumentation nicht ausdrücklich,
#   die Aufsicht empfiehlt sie. Entscheidungen Robert 17.10.2026: Betreiber-
#   Ebene statt Portfolio-Register, Teams und Zahlen statt Namen, Fälligkeit
#   mit refresh_months, Bedarfsbild aus dem Nachweis.
# =============================================================================

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from .guard import text_as_data

SCHEMA_VERSION = 1
DEFAULT_REFRESH_MONTHS = 12
KINDS = ("workshop", "training", "briefing", "self_study", "pilot")
#: Competence topics (Kompetenzfeld 7 / Curriculum-Modul 7) a measure can cover.
TOPICS: dict[str, dict[str, str]] = {
    "labeling": {"de": "Kennzeichnung und Freigabepflicht (Art. 50)", "en": "Labelling and approval duty (Art. 50)"},
    "citation": {"de": "Zitierpflicht und Unbekannt-Satz (D3/D4/M6)", "en": "Citation duty and the unknown sentence (D3/D4/M6)"},
    "approval": {"de": "Freigabe-Ritual und llm approve", "en": "Approval ritual and llm approve"},
    "limits": {"de": "Grenzen: Halluzination, Noise, das LLM rechnet nicht", "en": "Limits: hallucination, noise, the LLM does not compute"},
    "data": {"de": "Datenminimierung, Teams statt Personen", "en": "Data minimisation, teams not persons"},
    "export": {"de": "Prompt-Export und Rückweg (llm check)", "en": "Prompt export and return path (llm check)"},
    "prompting": {"de": "Fragen an das Lagebild stellen", "en": "Asking the situational picture"},
}
#: Which topics a used AI purpose presupposes (needs picture from the operator evidence).
PURPOSE_TOPICS: dict[str, tuple[str, ...]] = {
    "d1_exec_summary": ("labeling", "limits"), "d2_narration": ("labeling", "limits"),
    "d3_question": ("labeling", "citation", "prompting", "limits"),
    "d4_anomaly": ("labeling", "citation", "limits"), "d5_red_team": ("labeling", "limits"),
    "d6_translation": ("labeling",), "d8_conference": ("labeling", "limits"),
    "m6_briefing": ("labeling", "citation", "limits"), "p3_reading": ("labeling", "limits"),
    "approval": ("approval",),
}
#: Where the curriculum answers each topic (static offer table).
OFFER: dict[str, str] = {
    "labeling": "Curriculum-Modul 7 · docs/modules/llm.md (Drei Wächter, Marker und Freigabe)",
    "citation": "Tutorial „Das Lagebild befragen“ (docs/tutorials/ask-the-picture.de.md)",
    "approval": "docs/modules/llm.md (llm approve) · Praxis-Workshop-Ritual Freigabe zuletzt",
    "limits": "KI-Denkschrift v2.2, Teil C (Noise, Verifizieren können) · Noise-Audit (D7)",
    "data": "docs/modules/get_data.md (Datenminimierung ab Quelle) · Leitplanke (b)",
    "export": "docs/modules/llm.md (Prompt-Export, llm check)",
    "prompting": "Tutorial „Das Lagebild befragen“, Kapitel 4–9",
}
#: Keys that would carry persons - refused on load (Leitplanke b).
PERSON_KEYS = frozenset({"names", "participants_list", "attendees", "persons", "people",
                         "participant_names", "trainer_name"})

_T = {
    "de": {"title": "KI-Kompetenz-Nachweis (Art. 4 KI-VO)", "operator": "Betreiber", "as_of": "Stand",
           "measures": "Maßnahmen", "teams": "Teams", "participants": "Teilnahmen", "digest": "Prüfsumme des Logs",
           "note": "Einschätzung, keine Rechtsberatung: Art. 4 KI-VO verlangt Maßnahmen zur KI-Kompetenz; "
                   "die Dokumentation folgt der Empfehlung der Aufsicht (BNetzA-Hinweispapier 06/2025). "
                   "Teams und Zahlen, keine Namen — Teilnahmelisten liegen im HR-System (Beleg je Maßnahme).",
           "h_teams": "Stand je Team", "col_team": "Team", "col_last": "letzte Maßnahme", "col_topics": "Themen",
           "col_due": "auffrischen bis", "col_status": "Status", "current": "aktuell", "due": "auffrischen fällig",
           "none": "keine Maßnahme", "h_measures": "Maßnahmen", "col_date": "Datum", "col_title": "Titel",
           "col_kind": "Art", "col_hours": "Std.", "col_part": "Teiln.", "col_ref": "Beleg",
           "h_needs": "Bedarfsbild aus dem Betreiber-Nachweis", "needs_intro": "Genutzte KI-Zwecke seit {since}: ",
           "needs_none": "kein Nachweis übergeben (--audit) oder keine Aufrufe im Zeitraum",
           "uncovered": "Genutzt, aber von keiner Maßnahme abgedeckt (Hinweis, keine Bewertung): ",
           "covered": "Alle vorausgesetzten Themen sind durch Maßnahmen abgedeckt.",
           "h_offer": "Angebot je Thema", "col_topic": "Thema", "col_offer": "Wo es steht", "footer": "SituationReport · llm literacy · R4"},
    "en": {"title": "AI literacy record (Art. 4 AI Act)", "operator": "Operator", "as_of": "as of",
           "measures": "measures", "teams": "teams", "participants": "attendances", "digest": "log checksum",
           "note": "An assessment, not legal advice: Art. 4 AI Act requires measures for AI literacy; the "
                   "documentation follows the supervisory guidance (BNetzA note 06/2025). Teams and counts, "
                   "no names — attendance lists live in the HR system (reference per measure).",
           "h_teams": "Status per team", "col_team": "Team", "col_last": "last measure", "col_topics": "topics",
           "col_due": "refresh by", "col_status": "status", "current": "current", "due": "refresh due",
           "none": "no measure", "h_measures": "Measures", "col_date": "date", "col_title": "title",
           "col_kind": "kind", "col_hours": "h", "col_part": "att.", "col_ref": "reference",
           "h_needs": "Needs picture from the operator evidence", "needs_intro": "AI purposes used since {since}: ",
           "needs_none": "no evidence file given (--audit) or no calls in the period",
           "uncovered": "Used, but covered by no measure (a hint, not a verdict): ",
           "covered": "Every presupposed topic is covered by a measure.",
           "h_offer": "Offer per topic", "col_topic": "topic", "col_offer": "where it lives", "footer": "SituationReport · llm literacy · R4"},
}


def _t(lang: str, key: str, **kw: Any) -> str:
    return _T["de" if lang == "de" else "en"][key].format(**kw)


@dataclass
class Measure:
    measure_id: str
    day: date
    title: str
    kind: str
    teams: list[str]
    scope: list[str]
    duration_h: float | None = None
    participants: int | None = None
    module: str = ""
    materials: str = ""
    provider: str = ""
    attendance_ref: str = ""
    refresh_months: int | None = None
    notes: str = ""


@dataclass
class LiteracyLog:
    operator: str
    teams: list[str]
    measures: list[Measure]
    refresh_months: int = DEFAULT_REFRESH_MONTHS
    digest: str = ""


@dataclass
class TeamStatus:
    team: str
    measures: int = 0
    last: date | None = None
    due: date | None = None
    topics: set[str] = field(default_factory=set)
    status: str = "none"                  # current | due | none


def _add_months(day: date, months: int) -> date:
    month = day.month - 1 + months
    year = day.year + month // 12
    month = month % 12 + 1
    last_day = [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
    return date(year, month, min(day.day, last_day))


def _parse_date(value: Any, where: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{where}: date must be ISO (YYYY-MM-DD), got {value!r}.") from exc


def parse_log(data: Any) -> LiteracyLog:
    """Validate and parse a literacy log (dict). Person keys are refused."""
    if not isinstance(data, dict) or data.get("schema") != SCHEMA_VERSION:
        raise ValueError(f"ai_literacy.json needs \"schema\": {SCHEMA_VERSION}.")
    bad = sorted(k for k in data if k in PERSON_KEYS)
    refresh = int(data.get("refresh_months") or DEFAULT_REFRESH_MONTHS)
    teams = [text_as_data(t, 80) for t in (data.get("teams") or []) if str(t).strip()]
    measures: list[Measure] = []
    for i, raw in enumerate(data.get("measures") or [], start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"measures[{i}] is not an object.")
        bad += sorted(k for k in raw if k in PERSON_KEYS)
        mid = text_as_data(raw.get("id") or f"KM-{i}", 40)
        for key in ("date", "title", "kind", "teams"):
            if raw.get(key) in (None, "", []):
                raise ValueError(f"{mid}: '{key}' is required.")
        kind = str(raw["kind"]).strip()
        if kind not in KINDS:
            raise ValueError(f"{mid}: kind '{kind}' unknown - expected one of {', '.join(KINDS)}.")
        scope = [str(s).strip() for s in (raw.get("scope") or [])]
        unknown = [s for s in scope if s not in TOPICS]
        if unknown:
            raise ValueError(f"{mid}: scope {unknown} unknown - expected {', '.join(TOPICS)}.")
        participants = raw.get("participants")
        if participants is not None and (not isinstance(participants, int) or participants < 0):
            raise ValueError(f"{mid}: participants must be a non-negative integer (a count, never names).")
        measures.append(Measure(
            measure_id=mid, day=_parse_date(raw["date"], mid), title=text_as_data(raw["title"]),
            kind=kind, teams=[text_as_data(t, 80) for t in raw["teams"]], scope=scope,
            duration_h=float(raw["duration_h"]) if raw.get("duration_h") is not None else None,
            participants=participants, module=text_as_data(raw.get("module", ""), 80),
            materials=text_as_data(raw.get("materials", ""), 200), provider=text_as_data(raw.get("provider", ""), 80),
            attendance_ref=text_as_data(raw.get("attendance_ref", ""), 120),
            refresh_months=int(raw["refresh_months"]) if raw.get("refresh_months") else None,
            notes=text_as_data(raw.get("notes", ""))))
    if bad:
        raise ValueError(f"Person fields are not allowed in the literacy log (teams and counts only): "
                         f"{', '.join(sorted(set(bad)))}.")
    for m in measures:
        for t in m.teams:
            if t not in teams:
                teams.append(t)
    return LiteracyLog(operator=text_as_data(data.get("operator", ""), 120), teams=teams,
                       measures=sorted(measures, key=lambda m: m.day), refresh_months=refresh)


def load_log(path: Path) -> LiteracyLog:
    text = Path(path).read_text(encoding="utf-8")
    log = parse_log(json.loads(text))
    log.digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return log


def team_status(log: LiteracyLog, as_of: date) -> list[TeamStatus]:
    """Per team: measures, last date, topics, refresh due date and status."""
    out: list[TeamStatus] = []
    for team in log.teams:
        st = TeamStatus(team=team)
        for m in log.measures:
            if team not in m.teams or m.day > as_of:
                continue
            st.measures += 1
            st.topics |= set(m.scope)
            due = _add_months(m.day, m.refresh_months or log.refresh_months)
            if st.last is None or m.day > st.last:
                st.last = m.day
            if st.due is None or due > st.due:
                st.due = due
        if st.last is None:
            st.status = "none"
        elif st.due is not None and st.due < as_of:
            st.status = "due"
        else:
            st.status = "current"
        out.append(st)
    return out


def usage_from_audit(path: Path, since: date | None = None) -> Counter:
    """Count AI purposes in the operator evidence (export/external answers count as 'export')."""
    usage: Counter = Counter()
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return usage
    for line in lines:
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = str(rec.get("ts", ""))[:10]
        if since is not None:
            try:
                if date.fromisoformat(ts) < since:
                    continue
            except ValueError:
                continue
        purpose = str(rec.get("purpose", "?"))
        usage[purpose] += 1
        if rec.get("deployment_class") in ("export", "external_answer") or rec.get("provider") == "export":
            usage["export"] += 1
    return usage


def needed_topics(usage: Counter) -> set[str]:
    needed: set[str] = set()
    for purpose in usage:
        needed |= set(PURPOSE_TOPICS.get(purpose, ()))
        if purpose == "export":
            needed.add("export")
    return needed


def covered_topics(log: LiteracyLog, as_of: date) -> set[str]:
    return {s for m in log.measures if m.day <= as_of for s in m.scope}


def report_markdown(log: LiteracyLog, as_of: date, usage: Counter | None = None,
                    since: date | None = None, lang: str = "de") -> str:
    k = "de" if lang == "de" else "en"
    statuses = team_status(log, as_of)
    att = sum(m.participants or 0 for m in log.measures if m.day <= as_of)
    lines = [f"# {_t(k, 'title')} — {log.operator or '-'}", "",
             f"{_t(k, 'operator')}: {log.operator or '-'} · {_t(k, 'as_of')}: {as_of.isoformat()} · "
             f"{_t(k, 'measures')}: {sum(1 for m in log.measures if m.day <= as_of)} · {_t(k, 'teams')}: {len(log.teams)} · "
             f"{_t(k, 'participants')}: {att}" + (f" · {_t(k, 'digest')}: {log.digest}" if log.digest else ""),
             "", f"> {_t(k, 'note')}", "",
             f"## {_t(k, 'h_teams')}", "",
             f"| {_t(k, 'col_team')} | {_t(k, 'measures')} | {_t(k, 'col_last')} | {_t(k, 'col_topics')} | "
             f"{_t(k, 'col_due')} | {_t(k, 'col_status')} |", "|---|---|---|---|---|---|"]
    for st in statuses:
        topics = ", ".join(sorted(st.topics)) or "-"
        lines.append(f"| {st.team} | {st.measures} | {st.last.isoformat() if st.last else '-'} | {topics} | "
                     f"{st.due.isoformat() if st.due else '-'} | **{_t(k, st.status)}** |")
    lines += ["", f"## {_t(k, 'h_measures')}", "",
              f"| {_t(k, 'col_date')} | ID | {_t(k, 'col_title')} | {_t(k, 'col_kind')} | {_t(k, 'col_hours')} | "
              f"{_t(k, 'col_part')} | {_t(k, 'teams')} | {_t(k, 'col_topics')} | {_t(k, 'col_ref')} |",
              "|---|---|---|---|---|---|---|---|---|"]
    for m in log.measures:
        if m.day > as_of:
            continue
        hours = f"{m.duration_h:g}" if m.duration_h is not None else "-"
        lines.append(f"| {m.day.isoformat()} | {m.measure_id} | {m.title} | {m.kind} | {hours} | "
                     f"{m.participants if m.participants is not None else '-'} | {', '.join(m.teams)} | "
                     f"{', '.join(m.scope) or '-'} | {m.attendance_ref or m.materials or '-'} |")
    lines += ["", f"## {_t(k, 'h_needs')}", ""]
    if usage:
        shown = ", ".join(f"{p} ({n})" for p, n in sorted(usage.items()))
        lines.append(_t(k, "needs_intro", since=since.isoformat() if since else "-") + shown)
        gap = sorted(needed_topics(usage) - covered_topics(log, as_of))
        lines += ["", (_t(k, "uncovered") + ", ".join(f"{g} — {TOPICS[g][k]}" for g in gap)) if gap
                  else _t(k, "covered")]
    else:
        lines.append(f"_{_t(k, 'needs_none')}_")
    lines += ["", f"## {_t(k, 'h_offer')}", "", f"| {_t(k, 'col_topic')} | {_t(k, 'col_offer')} |", "|---|---|"]
    lines += [f"| {t} — {TOPICS[t][k]} | {OFFER[t]} |" for t in TOPICS]
    lines += ["", "---", _t(k, "footer"), ""]
    return "\n".join(lines)


def example_log(today: date | None = None) -> dict[str, Any]:
    """A small example log (teams and counts only)."""
    today = today or date.today()
    recent = _add_months(today, -2).isoformat()
    old = _add_months(today, -15).isoformat()
    return {
        "schema": SCHEMA_VERSION, "operator": "Portfolio-Stab Demo", "refresh_months": DEFAULT_REFRESH_MONTHS,
        "teams": ["Stab Portfolio", "ART Alpha-1", "ART Alpha-3", "ART Beta-3"],
        "measures": [
            {"id": "KM-1", "date": old, "title": "Einführung KI-Schicht: Kennzeichnung und Grenzen",
             "kind": "briefing", "duration_h": 1.5, "participants": 14,
             "teams": ["ART Alpha-1", "ART Alpha-3", "ART Beta-3"], "scope": ["labeling", "limits"],
             "module": "Curriculum-Modul 7", "materials": "docs/modules/llm.md", "provider": "intern",
             "attendance_ref": "HR-Schulungsportal #4711"},
            {"id": "KM-2", "date": recent, "title": "Lagebild befragen: Zitierpflicht, Unbekannt-Satz, Freigabe",
             "kind": "workshop", "duration_h": 3, "participants": 6, "teams": ["Stab Portfolio"],
             "scope": ["labeling", "citation", "approval", "limits", "prompting"],
             "module": "Curriculum-Modul 7", "materials": "docs/tutorials/ask-the-picture.de.md",
             "provider": "intern", "attendance_ref": "HR-Schulungsportal #4802"},
        ],
    }


def run_literacy(log_path: Path, as_of: date | None = None, audit_path: Path | None = None,
                 since: date | None = None, output: Path | None = None, lang: str = "de") -> tuple[str, int]:
    """Build the report; returns (markdown, exit code: 0 all current, 2 a team is due or without measure)."""
    log = load_log(log_path)
    today = as_of or date.today()
    usage = usage_from_audit(audit_path, since) if audit_path else None
    text = report_markdown(log, today, usage, since, lang)
    if output:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_text(text, encoding="utf-8")
    rc = 0 if all(s.status == "current" for s in team_status(log, today)) else 2
    return text, rc
