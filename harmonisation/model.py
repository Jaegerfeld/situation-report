# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       12.10.2026
# Geändert:       12.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Datenmodell des Harmonisierungs-Scores (Roadmap P3): Ein Fragenkatalog in drei Dimensionen (Business Value,
#   Transparenz, IT/Betrieb), End-to-End-Prozesse, versionierte Bewertungen
#   je Prozess mit Antwort UND Beleggrad je Frage, und die Entscheidung des
#   Boards je Prozess. Alles JSON mit eigener SCHEMA_VERSION, nur
#   Standardbibliothek. Der Katalog ist Daten, nicht Code: Der mitgelieferte
#   Beispielkatalog ist eine Illustration, der Erstnutzer bringt seinen
#   eigenen mit.
# =============================================================================

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1

#: Antwortskala: 0 „trifft nicht zu" … 4 „trifft voll zu". None = unbekannt.
SCALE_MIN = 0
SCALE_MAX = 4

#: Beleggrad je Antwort — wie die Antwort zustande kam.
EVIDENCE_DOCUMENTED = "documented"   # Dokument, Messung, System
EVIDENCE_ESTIMATED = "estimated"     # Einschätzung der befragten Person
EVIDENCE_HEARSAY = "hearsay"         # vom Hörensagen
EVIDENCE_LEVELS = (EVIDENCE_DOCUMENTED, EVIDENCE_ESTIMATED, EVIDENCE_HEARSAY)

#: Entscheidung des Boards je Prozess — wird eingetragen, nie gerechnet.
DECISION_STANDARDISE = "standardise"
DECISION_BRAND_SPECIFIC = "brand_specific"
DECISION_OPEN = "open"
DECISIONS = (DECISION_STANDARDISE, DECISION_BRAND_SPECIFIC, DECISION_OPEN)

CATALOGUE_FILE = "catalogue.json"
PROCESSES_FILE = "processes.json"
DECISIONS_FILE = "decisions.json"
ASSESSMENTS_DIR = "assessments"

LANGS = ("de", "en", "ro", "pt", "fr")


class HarmonisationError(ValueError):
    """A workspace file is missing, malformed or inconsistent."""


# ---------------------------------------------------------------------------
# Katalog
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Question:
    id: str
    text: dict[str, str]          # lang -> text; en is the fallback

    def label(self, lang: str) -> str:
        return self.text.get(lang) or self.text.get("en") or next(iter(self.text.values()), self.id)


@dataclass(frozen=True)
class Dimension:
    id: str
    name: dict[str, str]
    questions: tuple[Question, ...]

    def label(self, lang: str) -> str:
        return self.name.get(lang) or self.name.get("en") or self.id


@dataclass(frozen=True)
class Catalogue:
    name: str
    dimensions: tuple[Dimension, ...]
    note: str = ""                # z. B. „Beispielkatalog — Illustration"

    @property
    def question_ids(self) -> list[str]:
        return [q.id for d in self.dimensions for q in d.questions]

    def dimension_of(self, question_id: str) -> Dimension:
        for d in self.dimensions:
            if any(q.id == question_id for q in d.questions):
                return d
        raise KeyError(question_id)


def _lang_map(raw: Any, what: str) -> dict[str, str]:
    """A text in several languages; a bare string counts as English."""
    if isinstance(raw, str):
        return {"en": raw}
    if isinstance(raw, dict) and raw and all(isinstance(v, str) for v in raw.values()):
        return {str(k): v for k, v in raw.items()}
    raise HarmonisationError(f"{what}: expected a text or {{lang: text}}, got {raw!r}")


def parse_catalogue(data: dict[str, Any]) -> Catalogue:
    """Validate and build a Catalogue from parsed JSON."""
    if data.get("schema_version") != SCHEMA_VERSION:
        raise HarmonisationError(
            f"catalogue: schema_version {data.get('schema_version')!r} is not {SCHEMA_VERSION}")
    dims: list[Dimension] = []
    seen: set[str] = set()
    for d in data.get("dimensions") or []:
        questions: list[Question] = []
        for q in d.get("questions") or []:
            qid = str(q.get("id", "")).strip()
            if not qid:
                raise HarmonisationError("catalogue: a question has no id")
            if qid in seen:
                raise HarmonisationError(f"catalogue: duplicate question id '{qid}'")
            seen.add(qid)
            questions.append(Question(qid, _lang_map(q.get("text"), f"question {qid}")))
        did = str(d.get("id", "")).strip()
        if not did or not questions:
            raise HarmonisationError("catalogue: every dimension needs an id and questions")
        dims.append(Dimension(did, _lang_map(d.get("name"), f"dimension {did}"),
                              tuple(questions)))
    if not dims:
        raise HarmonisationError("catalogue: no dimensions")
    return Catalogue(name=str(data.get("name", "")), dimensions=tuple(dims),
                     note=str(data.get("note", "")))


# ---------------------------------------------------------------------------
# Prozesse, Bewertungen, Entscheidungen
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Process:
    id: str
    name: str
    owner: str = ""
    brands: tuple[str, ...] = ()


@dataclass(frozen=True)
class Answer:
    value: int | None             # None = unbekannt (zulässige Antwort)
    evidence: str = EVIDENCE_ESTIMATED


@dataclass(frozen=True)
class Assessment:
    process: str
    assessor: str
    day: date
    answers: dict[str, Answer]
    note: str = ""
    source: str = ""              # Dateiname, für Fehlermeldungen


@dataclass(frozen=True)
class Decision:
    process: str
    decision: str = DECISION_OPEN
    depth: str = ""               # Wortlaut des Boards, bewusst Freitext
    day: date | None = None
    body: str = ""


@dataclass
class Workspace:
    catalogue: Catalogue
    processes: tuple[Process, ...]
    assessments: tuple[Assessment, ...]
    decisions: dict[str, Decision] = field(default_factory=dict)
    root: Path | None = None

    def process(self, process_id: str) -> Process:
        for p in self.processes:
            if p.id == process_id:
                return p
        raise KeyError(process_id)


def parse_processes(data: dict[str, Any]) -> tuple[Process, ...]:
    if data.get("schema_version") != SCHEMA_VERSION:
        raise HarmonisationError("processes: wrong schema_version")
    out: list[Process] = []
    seen: set[str] = set()
    for p in data.get("processes") or []:
        pid = str(p.get("id", "")).strip()
        if not pid or pid in seen:
            raise HarmonisationError(f"processes: missing or duplicate id {pid!r}")
        seen.add(pid)
        out.append(Process(pid, str(p.get("name", pid)), str(p.get("owner", "")),
                           tuple(str(b) for b in p.get("brands") or [])))
    return tuple(out)


def _parse_day(raw: Any, what: str) -> date:
    try:
        return date.fromisoformat(str(raw))
    except (TypeError, ValueError) as exc:
        raise HarmonisationError(f"{what}: date {raw!r} is not YYYY-MM-DD") from exc


def parse_assessment(data: dict[str, Any], catalogue: Catalogue,
                     source: str = "") -> Assessment:
    """Validate one assessment against the catalogue and the scale."""
    where = source or "assessment"
    if data.get("schema_version") != SCHEMA_VERSION:
        raise HarmonisationError(f"{where}: wrong schema_version")
    process = str(data.get("process", "")).strip()
    if not process:
        raise HarmonisationError(f"{where}: no process")
    answers: dict[str, Answer] = {}
    known = set(catalogue.question_ids)
    for qid, raw in (data.get("answers") or {}).items():
        if qid not in known:
            raise HarmonisationError(f"{where}: question '{qid}' is not in the catalogue")
        if not isinstance(raw, dict):
            raise HarmonisationError(f"{where}: answer '{qid}' must be an object")
        value = raw.get("value")
        if value is not None:
            if not isinstance(value, int) or isinstance(value, bool) \
                    or not SCALE_MIN <= value <= SCALE_MAX:
                raise HarmonisationError(
                    f"{where}: answer '{qid}' must be {SCALE_MIN}..{SCALE_MAX} or null")
        evidence = str(raw.get("evidence", EVIDENCE_ESTIMATED))
        if evidence not in EVIDENCE_LEVELS:
            raise HarmonisationError(f"{where}: evidence '{evidence}' for '{qid}' unknown")
        answers[qid] = Answer(value, evidence)
    return Assessment(process=process, assessor=str(data.get("assessor", "")),
                      day=_parse_day(data.get("date"), where), answers=answers,
                      note=str(data.get("note", "")), source=source)


def parse_decisions(data: dict[str, Any]) -> dict[str, Decision]:
    if data.get("schema_version") != SCHEMA_VERSION:
        raise HarmonisationError("decisions: wrong schema_version")
    out: dict[str, Decision] = {}
    for pid, raw in (data.get("decisions") or {}).items():
        decision = str(raw.get("decision", DECISION_OPEN))
        if decision not in DECISIONS:
            raise HarmonisationError(f"decisions: '{decision}' for '{pid}' unknown")
        day = _parse_day(raw["date"], f"decision {pid}") if raw.get("date") else None
        out[str(pid)] = Decision(str(pid), decision, str(raw.get("depth", "")), day,
                                 str(raw.get("body", "")))
    return out


# ---------------------------------------------------------------------------
# Laden und Schreiben
# ---------------------------------------------------------------------------

def _read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError as exc:
        raise HarmonisationError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise HarmonisationError(f"{path.name}: not valid JSON ({exc})") from exc
    if not isinstance(data, dict):
        raise HarmonisationError(f"{path.name}: expected an object at top level")
    return data


def load_workspace(root: Path) -> Workspace:
    """
    Load catalogue, processes, every assessment and the decisions from a folder.

    Layout::

        root/catalogue.json
        root/processes.json
        root/decisions.json          (optional)
        root/assessments/*.json      (zero or more)

    Raises:
        HarmonisationError: on a missing or inconsistent file, naming it.
    """
    root = Path(root)
    catalogue = parse_catalogue(_read_json(root / CATALOGUE_FILE))
    processes = parse_processes(_read_json(root / PROCESSES_FILE))
    known = {p.id for p in processes}
    assessments: list[Assessment] = []
    folder = root / ASSESSMENTS_DIR
    if folder.is_dir():
        for path in sorted(folder.glob("*.json")):
            a = parse_assessment(_read_json(path), catalogue, source=path.name)
            if a.process not in known:
                raise HarmonisationError(
                    f"{path.name}: process '{a.process}' is not in {PROCESSES_FILE}")
            assessments.append(a)
    decisions: dict[str, Decision] = {}
    if (root / DECISIONS_FILE).exists():
        decisions = parse_decisions(_read_json(root / DECISIONS_FILE))
        for pid in decisions:
            if pid not in known:
                raise HarmonisationError(
                    f"{DECISIONS_FILE}: process '{pid}' is not in {PROCESSES_FILE}")
    return Workspace(catalogue, processes, tuple(assessments), decisions, root)


def assessment_to_json(a: Assessment) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "process": a.process,
        "assessor": a.assessor,
        "date": a.day.isoformat(),
        "answers": {qid: {"value": ans.value, "evidence": ans.evidence}
                    for qid, ans in a.answers.items()},
        "note": a.note,
    }


def decisions_to_json(decisions: dict[str, Decision]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "decisions": {
            pid: {"decision": d.decision, "depth": d.depth,
                  "date": d.day.isoformat() if d.day else "", "body": d.body}
            for pid, d in sorted(decisions.items())},
    }


def processes_to_json(processes: tuple[Process, ...]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "processes": [{"id": p.id, "name": p.name, "owner": p.owner,
                       "brands": list(p.brands)} for p in processes],
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def assessment_filename(a: Assessment) -> str:
    """Stable, sortable file name: date, process, assessor."""
    who = "".join(ch if ch.isalnum() else "-" for ch in a.assessor.strip().lower()) or "anon"
    return f"{a.day.isoformat()}_{a.process}_{who}.json"
