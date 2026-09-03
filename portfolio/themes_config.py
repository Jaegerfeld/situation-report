# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Strategic Themes & integrierte Roadmap (Roadmap B7, VSC-2 aus dem
#   Workshop Wolfsburg 08/2026). Schließt zwei konsolidierte SAFe-Lücken:
#   Strategic Themes bekommen ein strukturiertes Zuhause (Themes mit
#   Epic-Verknüpfung), und die Solution-Ebene bekommt eine integrierte
#   Roadmap mit Initiative-Swimlanes über Trains (Zeithorizont nah
#   granular, fern grob: P1 · P2 · Y1 · Y2 · Y3). Orphan-Detection in
#   beide Richtungen ist zentral: ein Theme ohne Epics ist „deklariert
#   und vergessen", ein Epic ohne Theme eine „Zombie-Initiative" —
#   Letzteres ist ein bewusst leeres theme-Feld; ein TIPPFEHLER in der
#   Referenz ist dagegen ein Validierungsfehler, kein Zombie.
# =============================================================================

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

THEMES_SCHEMA_VERSION = 1

HORIZON_P1 = "P1"
HORIZON_P2 = "P2"
HORIZON_Y1 = "Y1"
HORIZON_Y2 = "Y2"
HORIZON_Y3 = "Y3"
#: Near-term granular, far-term coarse — the roadmap's column order.
HORIZONS = (HORIZON_P1, HORIZON_P2, HORIZON_Y1, HORIZON_Y2, HORIZON_Y3)

EPIC_PLANNED = "planned"
EPIC_IN_PROGRESS = "in_progress"
EPIC_DONE = "done"
EPIC_STATUSES = (EPIC_PLANNED, EPIC_IN_PROGRESS, EPIC_DONE)


@dataclass
class StrategicTheme:
    """One strategic theme — the 'why' initiatives hang from."""
    theme_id: str
    title: str
    description: str = ""


@dataclass
class Epic:
    """
    One initiative on the integrated roadmap.

    ``theme`` references a StrategicTheme id; an EMPTY theme is the
    explicit zombie marker (initiative without a strategic home).
    ``train`` is the delivering train/ART (a swimlane row), ``horizon``
    one of P1/P2/Y1/Y2/Y3.
    """
    epic_id: str
    title: str
    train: str
    horizon: str
    theme: str = ""
    status: str = EPIC_PLANNED


@dataclass
class ThemesRegister:
    """Strategic themes and roadmap epics of one solution."""
    themes: list[StrategicTheme] = field(default_factory=list)
    epics: list[Epic] = field(default_factory=list)


def orphan_theme_ids(register: ThemesRegister) -> set[str]:
    """Themes without a single epic — declared and forgotten."""
    used = {e.theme for e in register.epics if e.theme}
    return {t.theme_id for t in register.themes} - used


def zombie_epics(register: ThemesRegister) -> list[Epic]:
    """Epics without a theme — initiatives without a strategic home."""
    return [e for e in register.epics if not e.theme]


def parse_themes(data: Any) -> ThemesRegister:
    """
    Build a ThemesRegister from an already-parsed JSON object.

    Raises:
        ValueError: On structural errors — missing lists, empty ids/
                    titles, duplicates, unknown horizon/status, or an epic
                    referencing a theme id that does not exist (a typo is
                    an error, not a zombie).
    """
    if not isinstance(data, dict):
        raise ValueError("Themes file must be a JSON object.")

    themes_raw = data.get("themes", [])
    epics_raw = data.get("epics", [])
    if not isinstance(themes_raw, list) or not isinstance(epics_raw, list):
        raise ValueError("Themes file needs 'themes' and 'epics' lists "
                         "(either may be empty).")

    themes: list[StrategicTheme] = []
    theme_ids: set[str] = set()
    for i, entry in enumerate(themes_raw):
        if not isinstance(entry, dict):
            raise ValueError(f"Theme #{i + 1} is not an object.")
        theme_id = str(entry.get("id", "")).strip()
        title = str(entry.get("title", "")).strip()
        if not theme_id or not title:
            raise ValueError(f"Theme #{i + 1} needs non-empty 'id' and "
                             f"'title'.")
        if theme_id in theme_ids:
            raise ValueError(f"Duplicate theme id '{theme_id}'.")
        theme_ids.add(theme_id)
        themes.append(StrategicTheme(
            theme_id=theme_id, title=title,
            description=str(entry.get("description", "")).strip()))

    epics: list[Epic] = []
    epic_ids: set[str] = set()
    for i, entry in enumerate(epics_raw):
        if not isinstance(entry, dict):
            raise ValueError(f"Epic #{i + 1} is not an object.")
        epic_id = str(entry.get("id", "")).strip()
        title = str(entry.get("title", "")).strip()
        train = str(entry.get("train", "")).strip()
        if not epic_id or not title or not train:
            raise ValueError(f"Epic #{i + 1} needs non-empty 'id', 'title' "
                             f"and 'train'.")
        if epic_id in epic_ids:
            raise ValueError(f"Duplicate epic id '{epic_id}'.")
        epic_ids.add(epic_id)

        horizon = str(entry.get("horizon", "")).strip()
        if horizon not in HORIZONS:
            raise ValueError(
                f"Epic '{epic_id}': unknown horizon '{horizon}' — expected "
                f"one of {', '.join(HORIZONS)}.")

        status = str(entry.get("status", EPIC_PLANNED)).strip().lower()
        if status not in EPIC_STATUSES:
            raise ValueError(
                f"Epic '{epic_id}': unknown status '{status}' — expected "
                f"one of {', '.join(EPIC_STATUSES)}.")

        theme = str(entry.get("theme", "")).strip()
        if theme and theme not in theme_ids:
            raise ValueError(
                f"Epic '{epic_id}': 'theme' references unknown theme "
                f"'{theme}' — a typo is an error; leave 'theme' empty to "
                f"mark a deliberate zombie initiative.")

        epics.append(Epic(epic_id=epic_id, title=title, train=train,
                          horizon=horizon, theme=theme, status=status))

    return ThemesRegister(themes=themes, epics=epics)


def load_themes(path: Path) -> ThemesRegister:
    """Read and validate a themes JSON file."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return parse_themes(raw)


def themes_to_dict(register: ThemesRegister) -> dict[str, Any]:
    """Serialise a ThemesRegister back into the schema-v1 JSON shape."""
    themes = []
    for t in register.themes:
        entry: dict[str, Any] = {"id": t.theme_id, "title": t.title}
        if t.description:
            entry["description"] = t.description
        themes.append(entry)
    epics = []
    for e in register.epics:
        entry = {"id": e.epic_id, "title": e.title, "train": e.train,
                 "horizon": e.horizon}
        if e.theme:
            entry["theme"] = e.theme
        if e.status != EPIC_PLANNED:
            entry["status"] = e.status
        epics.append(entry)
    return {"schema": THEMES_SCHEMA_VERSION, "themes": themes, "epics": epics}


def save_themes(path: Path, register: ThemesRegister) -> None:
    """Write a ThemesRegister to a JSON file."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(themes_to_dict(register), indent=2, ensure_ascii=False),
        encoding="utf-8")
