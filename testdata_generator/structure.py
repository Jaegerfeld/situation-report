# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       26.10.2026
# Geändert:       26.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Struktur des Demo-Datenraums als Daten (Beta, Schnitt 1a, Entscheidung
#   E2a vom 26.10.2026): beliebig viele Portfolios, je Portfolio beliebig
#   viele Solutions, je Solution beliebig viele ARTs (mindestens einer).
#   Der Workflow (klassisch / eigene Stage-Map) ist eine Eigenschaft der
#   Solution, nicht des ARTs.
#
#   Die Datei `structure.json` liegt im Datenraum und wird von der
#   Oberfläche (Schritt 1) bearbeitet. Drei Vorlagen: Klein (1·1·2),
#   Standard (1·2·3 — das heutige Demo-Portfolio), Groß (5 Portfolios).
#   Namen werden vorgeschlagen (griechische Buchstaben, dann S<n>) und sind
#   änderbar; die Geschichte (story.py) bindet ihre Rollen an Positionen,
#   nicht an Namen — Umbenennen bricht nichts.
# =============================================================================

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCHEMA = 1

WORKFLOW_CLASSIC = "classic"
WORKFLOW_STAGE_MAP = "stage_map"
WORKFLOWS = (WORKFLOW_CLASSIC, WORKFLOW_STAGE_MAP)

TEMPLATE_SMALL = "small"
TEMPLATE_STANDARD = "standard"
TEMPLATE_LARGE = "large"
STRUCTURE_TEMPLATES = (TEMPLATE_SMALL, TEMPLATE_STANDARD, TEMPLATE_LARGE)

#: Vorgeschlagene Solution-Namen in Reihenfolge; danach S25, S26, …
GREEK = ("Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta",
         "Theta", "Iota", "Kappa", "Lambda", "My", "Ny", "Xi", "Omikron",
         "Pi", "Rho", "Sigma", "Tau", "Ypsilon", "Phi", "Chi", "Psi",
         "Omega")

#: Register je Solution, die der Datenraum anlegt (Zählgrundlage der
#: Schätzung; scenario.py schreibt genau diese Dateien).
REGISTER_NAMES = ("risks", "nfr", "capabilities", "dependencies",
                  "decisions", "slo", "dora", "flow_problems", "themes",
                  "solution_areas", "decision_points")

#: Schwellen, ab denen die Schätzung vor Dauer und Größe warnt (E2a).
WARN_ARTS = 30
WARN_PORTFOLIOS = 5

_NAME_RE = re.compile(r"^[\w .\-]+$", re.UNICODE)
_SPEC_RE = re.compile(r"^(\d+)([sc]?)$")


def slug(name: str) -> str:
    """Folder-safe key of a name: 'Solution Süd' -> 'sued', 'Alpha' -> 'alpha'."""
    text = name.strip()
    if text.lower().startswith("solution "):
        text = text[len("solution "):]
    text = (text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
            .replace("Ä", "Ae").replace("Ö", "Oe").replace("Ü", "Ue")
            .replace("ß", "ss"))
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()
    return text


@dataclass
class SolutionSpec:
    """
    One solution of a portfolio.

    Attributes:
        name:     Short name ("Alpha"); the display name is "Solution Alpha".
        arts:     Short ART names ("Alpha-1"); member names are "ART Alpha-1".
        workflow: WORKFLOW_CLASSIC (default pooling path) or
                  WORKFLOW_STAGE_MAP (own stage map, schema 2).
    """
    name: str
    arts: list[str] = field(default_factory=list)
    workflow: str = WORKFLOW_CLASSIC

    @property
    def short(self) -> str:
        return self.name.removeprefix("Solution ").strip()

    @property
    def display_name(self) -> str:
        return f"Solution {self.short}"

    @property
    def key(self) -> str:
        return slug(self.name)

    @property
    def member_names(self) -> list[str]:
        return [f"ART {a}" for a in self.arts]


@dataclass
class PortfolioSpec:
    """One portfolio: a name and its solutions."""
    name: str
    solutions: list[SolutionSpec] = field(default_factory=list)

    @property
    def key(self) -> str:
        return slug(self.name)

    @property
    def arts(self) -> list[str]:
        return [a for s in self.solutions for a in s.arts]


@dataclass
class Structure:
    """The whole data-room structure: portfolios -> solutions -> ARTs."""
    portfolios: list[PortfolioSpec] = field(default_factory=list)
    schema: int = SCHEMA

    @property
    def n_portfolios(self) -> int:
        return len(self.portfolios)

    @property
    def n_solutions(self) -> int:
        return sum(len(p.solutions) for p in self.portfolios)

    @property
    def n_arts(self) -> int:
        return sum(len(p.arts) for p in self.portfolios)

    def describe(self) -> str:
        """'1 Portfolio · 2 Solutions · 6 ARTs' (counts only, language-neutral)."""
        p, s, a = self.n_portfolios, self.n_solutions, self.n_arts
        return (f"{p} Portfolio{'s' if p != 1 else ''} · "
                f"{s} Solution{'s' if s != 1 else ''} · "
                f"{a} ART{'s' if a != 1 else ''}")


# --- Validation -------------------------------------------------------------

def _check_name(label: str, name: str) -> None:
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"{label}: name must not be empty.")
    if name != name.strip():
        raise ValueError(f"{label} '{name}': leading or trailing whitespace.")
    if not _NAME_RE.match(name):
        raise ValueError(
            f"{label} '{name}': only letters, digits, space, '.', '_' and '-' "
            f"are allowed (the name becomes a file name).")


def validate(structure: Structure) -> None:
    """
    Check a structure; raises ValueError with the first problem found.

    Rules (E2a): at least one portfolio, one solution per portfolio and one
    ART per solution; names file-safe; portfolio keys unique; solution keys
    unique within a portfolio; ART names unique within a portfolio (they
    name the raw extracts in one shared raw/ folder); workflow known.
    """
    if structure.schema != SCHEMA:
        raise ValueError(f"structure schema {structure.schema!r} unknown "
                         f"(expected {SCHEMA}).")
    if not structure.portfolios:
        raise ValueError("structure needs at least one portfolio.")
    pkeys: set[str] = set()
    for portfolio in structure.portfolios:
        _check_name("portfolio", portfolio.name)
        if portfolio.key in pkeys:
            raise ValueError(f"portfolio key '{portfolio.key}' is not unique.")
        pkeys.add(portfolio.key)
        if not portfolio.solutions:
            raise ValueError(f"portfolio '{portfolio.name}' needs at least "
                             f"one solution.")
        skeys: set[str] = set()
        arts_seen: set[str] = set()
        for solution in portfolio.solutions:
            _check_name(f"solution in '{portfolio.name}'", solution.name)
            if not solution.key:
                raise ValueError(f"solution '{solution.name}' yields an "
                                 f"empty folder key.")
            if solution.key in skeys:
                raise ValueError(f"solution key '{solution.key}' is not "
                                 f"unique in portfolio '{portfolio.name}'.")
            skeys.add(solution.key)
            if solution.workflow not in WORKFLOWS:
                raise ValueError(
                    f"solution '{solution.name}': workflow "
                    f"'{solution.workflow}' unknown — expected one of "
                    f"{', '.join(WORKFLOWS)}.")
            if not solution.arts:
                raise ValueError(f"solution '{solution.name}' needs at "
                                 f"least one ART.")
            for art in solution.arts:
                _check_name(f"ART in '{solution.name}'", art)
                if art in arts_seen:
                    raise ValueError(f"ART name '{art}' is not unique in "
                                     f"portfolio '{portfolio.name}'.")
                arts_seen.add(art)


# --- Serialisation ----------------------------------------------------------

def to_dict(structure: Structure) -> dict[str, Any]:
    return {
        "schema": structure.schema,
        "portfolios": [
            {"name": p.name,
             "solutions": [
                 {"name": s.short, "workflow": s.workflow,
                  "arts": list(s.arts)}
                 for s in p.solutions]}
            for p in structure.portfolios],
    }


def from_dict(data: Any) -> Structure:
    """Parse and validate; raises ValueError on malformed input."""
    if not isinstance(data, dict):
        raise ValueError("structure must be a JSON object.")
    raw_ps = data.get("portfolios")
    if not isinstance(raw_ps, list):
        raise ValueError("'portfolios' must be a list.")
    portfolios: list[PortfolioSpec] = []
    for raw_p in raw_ps:
        if not isinstance(raw_p, dict):
            raise ValueError("each portfolio must be an object.")
        raw_ss = raw_p.get("solutions")
        if not isinstance(raw_ss, list):
            raise ValueError(f"portfolio '{raw_p.get('name', '?')}': "
                             f"'solutions' must be a list.")
        solutions: list[SolutionSpec] = []
        for raw_s in raw_ss:
            if not isinstance(raw_s, dict):
                raise ValueError("each solution must be an object.")
            arts = raw_s.get("arts")
            if not isinstance(arts, list) or not all(
                    isinstance(a, str) for a in arts):
                raise ValueError(f"solution '{raw_s.get('name', '?')}': "
                                 f"'arts' must be a list of names.")
            solutions.append(SolutionSpec(
                name=str(raw_s.get("name", "")),
                arts=list(arts),
                workflow=str(raw_s.get("workflow", WORKFLOW_CLASSIC))))
        portfolios.append(PortfolioSpec(name=str(raw_p.get("name", "")),
                                        solutions=solutions))
    try:
        schema = int(data.get("schema", SCHEMA))
    except (TypeError, ValueError) as exc:
        raise ValueError("'schema' must be an integer.") from exc
    structure = Structure(portfolios=portfolios, schema=schema)
    validate(structure)
    return structure


def load_structure(path: Path) -> Structure:
    """Read structure.json; raises ValueError (malformed) or OSError."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: not valid JSON ({exc}).") from exc
    return from_dict(data)


def save_structure(path: Path, structure: Structure) -> None:
    validate(structure)
    Path(path).write_text(json.dumps(to_dict(structure), indent=2,
                                     ensure_ascii=False) + "\n",
                          encoding="utf-8")


# --- Building and templates -------------------------------------------------

def suggest_solution_name(index: int) -> str:
    """Alpha, Beta, …, Omega, then S25, S26, …"""
    return GREEK[index] if index < len(GREEK) else f"S{index + 1}"


def suggest_art_names(solution_name: str, count: int) -> list[str]:
    short = solution_name.removeprefix("Solution ").strip()
    return [f"{short}-{i}" for i in range(1, count + 1)]


def make_portfolio(name: str, solutions: list[tuple[int, str]],
                   names: list[str] | None = None) -> PortfolioSpec:
    """
    Build a portfolio from (art_count, workflow) pairs.

    Solution names come from ``names`` or the Greek suggestion list; ART
    names follow '<Solution>-<n>'.
    """
    specs: list[SolutionSpec] = []
    for i, (count, workflow) in enumerate(solutions):
        sol_name = (names[i] if names and i < len(names)
                    else suggest_solution_name(i))
        specs.append(SolutionSpec(name=sol_name,
                                  arts=suggest_art_names(sol_name, count),
                                  workflow=workflow))
    return PortfolioSpec(name=name, solutions=specs)


def parse_arts_spec(spec: str) -> list[tuple[int, str]]:
    """
    '3,4s,1' -> [(3, classic), (4, stage_map), (1, classic)].

    One entry per solution: the ART count, optionally followed by 's'
    (own stage map) or 'c' (classic, the default).

    Raises:
        ValueError: empty spec, non-numeric entry or a zero count.
    """
    parts = [p.strip() for p in str(spec).split(",")]
    if not parts or any(not p for p in parts):
        raise ValueError(f"arts spec '{spec}': expected counts like '3,4s,1'.")
    result: list[tuple[int, str]] = []
    for part in parts:
        m = _SPEC_RE.match(part)
        if not m:
            raise ValueError(f"arts spec '{spec}': '{part}' is not a count "
                             f"(digits, optional 's' for stage map).")
        count = int(m.group(1))
        if count < 1:
            raise ValueError(f"arts spec '{spec}': every solution needs at "
                             f"least one ART.")
        result.append((count, WORKFLOW_STAGE_MAP if m.group(2) == "s"
                       else WORKFLOW_CLASSIC))
    return result


def structure_from_arts_spec(spec: str,
                             portfolio_name: str = "Demo Portfolio") -> Structure:
    """One portfolio from a compact CLI spec (see parse_arts_spec)."""
    structure = Structure([make_portfolio(portfolio_name, parse_arts_spec(spec))])
    validate(structure)
    return structure


def structure_template(name: str) -> Structure:
    """
    The three built-in structures (E2a).

    small:    Demo Portfolio · Alpha (classic) with 2 ARTs.
    standard: Demo Portfolio · Alpha (classic, 3) · Beta (stage map, 3) —
              the demo portfolio of 0.2x–0.5x, byte-for-byte the same data.
    large:    five portfolios, 3–4 solutions each, 1–6 ARTs per solution
              (49 ARTs) — the stress case for the estimate warning.

    Raises:
        ValueError: unknown template name.
    """
    if name == TEMPLATE_SMALL:
        return Structure([make_portfolio(
            "Demo Portfolio", [(2, WORKFLOW_CLASSIC)])])
    if name == TEMPLATE_STANDARD:
        return Structure([make_portfolio(
            "Demo Portfolio", [(3, WORKFLOW_CLASSIC), (3, WORKFLOW_STAGE_MAP)])])
    if name == TEMPLATE_LARGE:
        c, s = WORKFLOW_CLASSIC, WORKFLOW_STAGE_MAP
        layout = [
            ("Portfolio Nord", [(3, c), (4, s), (1, c)]),
            ("Portfolio Süd", [(2, c), (6, s), (2, c), (3, c)]),
            ("Portfolio West", [(1, c), (3, c), (5, s)]),
            ("Portfolio Ost", [(4, c), (2, s), (3, c), (1, c)]),
            ("Portfolio Mitte", [(2, c), (3, s), (4, c)]),
        ]
        portfolios: list[PortfolioSpec] = []
        offset = 0
        for pname, sols in layout:
            names = [suggest_solution_name(offset + i) for i in range(len(sols))]
            portfolios.append(make_portfolio(pname, sols, names))
            offset += len(sols)
        return Structure(portfolios)
    raise ValueError(f"Unknown structure template '{name}' — expected one of "
                     f"{', '.join(STRUCTURE_TEMPLATES)}.")


def resolve_structure(value: str | Path | None) -> Structure:
    """
    CLI helper: None -> standard template; a template name -> that template;
    anything else -> a structure.json path.
    """
    if value is None:
        return structure_template(TEMPLATE_STANDARD)
    text = str(value)
    if text in STRUCTURE_TEMPLATES:
        return structure_template(text)
    return load_structure(Path(text))


# --- Estimate ---------------------------------------------------------------

@dataclass(frozen=True)
class Estimate:
    """What a structure produces — the 'Was entsteht' box of step 1/2."""
    portfolios: int
    solutions: int
    arts: int
    jira_exports: int
    workbooks: int
    registers: int
    stands: int
    deltas: int
    warn: bool
    warn_reason: str = ""


def estimate(structure: Structure, stands: int = 6,
             scale: str = "m") -> Estimate:
    """
    Count the artefacts a structure yields (E2a: the estimate follows the
    structure) and flag the heavy cases: WARN_ARTS ARTs or more, or
    WARN_PORTFOLIOS portfolios or more at scale 'l'.
    """
    p, s, a = structure.n_portfolios, structure.n_solutions, structure.n_arts
    reasons = []
    if a >= WARN_ARTS:
        reasons.append(f"{a} ARTs (ab {WARN_ARTS} dauert die Erzeugung spürbar)")
    if p >= WARN_PORTFOLIOS and scale == "l":
        reasons.append(f"{p} Portfolios bei Umfang L")
    return Estimate(
        portfolios=p, solutions=s, arts=a,
        jira_exports=a, workbooks=3 * a, registers=len(REGISTER_NAMES) * s,
        stands=stands * p, deltas=max(stands - 1, 0) * p,
        warn=bool(reasons), warn_reason="; ".join(reasons))
