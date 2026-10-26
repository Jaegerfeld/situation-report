# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       26.10.2026
# Geändert:       26.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Dienstschicht des Demo-Datenraums (Beta, Schnitt 3a): die drei Schritte
#   der Oberfläche als Daten — ein GenerationRequest (Szenario, Struktur,
#   Umfang, Quellen), eine Schätzung, ein Lauf mit Fortschritt je
#   Teilschritt und Abbruch, ein Ergebnis mit Zahlen und Pfaden. Jede
#   Oberfläche (tkinter, lokaler Server + Browser, Kommandozeile) sitzt auf
#   genau dieser Schicht und kennt den Generator nicht direkt.
#
#   Neun Teilschritte wie im Prototyp: Struktur und Geschichte, Jira-Exporte
#   und Arbeitsmappen, Register, Konfigurationen, Provider-Rohdaten, README,
#   Stände-Reihe, Delta-Briefings, KI-Entwürfe (F3, nur mit Schalter).
# =============================================================================

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from build_reports.chart_texts import DEFAULT_LANG

from .ai_drafts import write_ai_drafts
from .register_gen import DEFAULT_SCALE, SCALES
from .scenario import MAX_STANDS, MIN_STANDS, build_portfolio_scenario
from .story import STORY_TEMPLATES, SUGGESTED_STANDS, TEMPLATE_STANDARD, Story, load_story
from .structure import (
    REGISTER_NAMES,
    Estimate,
    Structure,
    estimate,
    structure_template,
    validate,
)
from .structure import (
    TEMPLATE_STANDARD as STRUCTURE_STANDARD,
)

#: (step id, label) in the order the generator runs them.
STEPS: tuple[tuple[str, str], ...] = (
    ("story", "Struktur und Geschichte"),
    ("arts", "Jira-Exporte und Arbeitsmappen"),
    ("registers", "Register"),
    ("configs", "Konfigurationen"),
    ("sources", "Provider-Rohdaten"),
    ("readme", "README"),
    ("stands", "Stände-Reihe"),
    ("deltas", "Delta-Briefings"),
    ("ai_drafts", "KI-Entwürfe (Mock)"),
)
STEP_LABELS = dict(STEPS)
STATE_RUNNING = "running"
STATE_DONE = "done"
STATE_SKIPPED = "skipped"
STATE_FAILED = "failed"


class GenerationCancelled(RuntimeError):
    """The caller asked to stop between two steps; the folder keeps what exists."""


@dataclass
class GenerationRequest:
    """Everything the three steps of the UI collect."""
    output_dir: Path
    structure: Structure | None = None
    template: str = TEMPLATE_STANDARD
    switches: dict[str, bool] = field(default_factory=dict)
    stands: int | None = None            # None = the template's suggestion
    scale: str = DEFAULT_SCALE
    seed: int = 42
    reference: date | None = None
    lang: str = DEFAULT_LANG
    art_profiles: dict[str, dict] | None = None
    ai_drafts: bool = False              # F3: off by default
    window_days: int = 365

    def resolved_structure(self) -> Structure:
        return self.structure or structure_template(STRUCTURE_STANDARD)

    def resolved_stands(self) -> int:
        return SUGGESTED_STANDS.get(self.template, 6) if self.stands is None else self.stands

    def resolved_reference(self) -> date:
        return self.reference or date.today()

    def validate(self) -> None:
        """Raise ValueError for anything the generator would refuse later."""
        validate(self.resolved_structure())
        if self.template not in STORY_TEMPLATES:
            raise ValueError(f"Unknown story template '{self.template}' — expected one of "
                             f"{', '.join(STORY_TEMPLATES)}.")
        stands = self.resolved_stands()
        if not MIN_STANDS <= stands <= MAX_STANDS:
            raise ValueError(f"stands must be {MIN_STANDS}..{MAX_STANDS}, got {stands}.")
        if self.scale not in SCALES:
            raise ValueError(f"Unknown scale '{self.scale}' — expected one of {', '.join(SCALES)}.")


def estimate_request(request: GenerationRequest) -> Estimate:
    """What the request will produce (the 'Was entsteht' box)."""
    return estimate(request.resolved_structure(), stands=request.resolved_stands(),
                    scale=request.scale)


@dataclass
class ProgressEvent:
    """One state change of one step."""
    step: str
    label: str
    state: str
    detail: str = ""
    elapsed_s: float = 0.0


ProgressSink = Callable[[ProgressEvent], None]


@dataclass
class GenerationResult:
    """The outcome: paths of the build plus the numbers the result card shows."""
    request: GenerationRequest
    paths: dict[str, Any]
    structure: Structure
    story: Story | None
    portfolios: list[str]
    issues: int
    registers: int
    stands: int
    deltas: int
    providers: int
    ai_drafts: list[Path]
    elapsed_s: float

    @property
    def root(self) -> Path:
        return Path(self.request.output_dir)


def _portfolio_paths(paths: dict[str, Any]) -> list[dict[str, Any]]:
    """The per-portfolio dicts, whether the build had one portfolio or many."""
    if "portfolios" in paths and isinstance(paths["portfolios"], dict):
        return list(paths["portfolios"].values())
    return [paths]


def _count_issues(room: dict[str, Any]) -> int:
    raw_dir = Path(room["portfolio"]).parent / "raw"
    total = 0
    for raw in raw_dir.glob("*_jira.json"):
        try:
            total += int(json.loads(raw.read_text(encoding="utf-8")).get("total", 0))
        except (OSError, ValueError):
            continue
    return total


def _count_providers(room: dict[str, Any]) -> int:
    sources = room.get("sources") or {}
    kinds: set[str] = set()
    for info in sources.values():
        for kind in (info.get("configs") or {}):
            kinds.add(kind)
    return len(kinds)


def generate_dataspace(
    request: GenerationRequest,
    progress: ProgressSink | None = None,
    log: Callable[[str], None] | None = None,
    cancel: Callable[[], bool] | None = None,
) -> GenerationResult:
    """
    Run the generator for ``request`` with step-wise progress.

    Args:
        request:  What to build (validated first; ValueError before anything
                  is written).
        progress: Receives a ProgressEvent at every step start and end.
        log:      Line-wise progress of the generator (None = silent).
        cancel:   Polled between steps; True raises GenerationCancelled and
                  leaves the folder with what exists so far.

    Returns:
        GenerationResult with the build paths and the numbers for the result
        card. Several portfolios are counted together.
    """
    request.validate()
    started = time.monotonic()
    step_started: dict[str, float] = {}
    quiet: Callable[[str], None] = log or (lambda m: None)

    def emit(step: str, state: str, detail: str = "") -> None:
        if cancel is not None and cancel():
            raise GenerationCancelled(f"abgebrochen vor Schritt '{step}'")
        if state == STATE_RUNNING:
            step_started[step] = time.monotonic()
        elapsed = time.monotonic() - step_started.get(step, time.monotonic())
        if progress is not None:
            progress(ProgressEvent(step, STEP_LABELS.get(step, step), state, detail,
                                   round(elapsed, 2)))

    structure = request.resolved_structure()
    stands = request.resolved_stands()
    reference = request.resolved_reference()
    try:
        paths = build_portfolio_scenario(
            Path(request.output_dir), seed=request.seed, reference=reference,
            window_days=request.window_days, log=quiet, scale=request.scale,
            art_profiles=request.art_profiles, structure=structure, stands=stands,
            lang=request.lang, template=request.template, switches=request.switches,
            progress=emit)
    except GenerationCancelled:
        raise
    except Exception as exc:
        if progress is not None:
            progress(ProgressEvent("build", "Erzeugung", STATE_FAILED, str(exc),
                                   round(time.monotonic() - started, 2)))
        raise

    rooms = _portfolio_paths(paths)
    drafts: list[Path] = []
    if request.ai_drafts:
        emit("ai_drafts", STATE_RUNNING)
        for room in rooms:
            info = write_ai_drafts(Path(room["portfolio"]).parent, room, reference,
                                   lang=request.lang, log=quiet)
            drafts.append(info["dir"])
            room["ai_drafts"] = info
        emit("ai_drafts", STATE_DONE, f"{len(drafts)} Ordner")
    else:
        emit("ai_drafts", STATE_SKIPPED, "Schalter aus")

    story = load_story(Path(rooms[0]["story"])) if rooms and rooms[0].get("story") else None
    return GenerationResult(
        request=request, paths=paths, structure=structure, story=story,
        portfolios=[p.key for p in structure.portfolios],
        issues=sum(_count_issues(r) for r in rooms),
        registers=len(REGISTER_NAMES) * structure.n_solutions,
        stands=sum(len(r.get("snapshots") or []) for r in rooms),
        deltas=sum(len(r.get("deltas") or []) for r in rooms),
        providers=max((_count_providers(r) for r in rooms), default=0),
        ai_drafts=drafts,
        elapsed_s=round(time.monotonic() - started, 2),
    )
