# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       16.05.2026
# Geändert:       16.05.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Gemeinsames Projekt-Template für alle Module (build_reports, transform_data,
#   testdata_generator, helper). Eine einzige JSON-Datei hält je einen Abschnitt
#   pro Modul, sodass die Pipeline-Konfiguration (Workflow, Pfade, Projekt,
#   Zeitraum) einmal gesetzt und in jedem Modul-GUI geladen werden kann.
#
#   Schema v5 kapselt die Modul-Abschnitte unter "modules". Ältere build_reports-
#   Templates (Schema v4, flache Struktur ohne "modules") werden weiterhin
#   gelesen und transparent als build_reports-Abschnitt interpretiert.
#
#   save_template ersetzt beim Speichern nur den eigenen Modul-Abschnitt und
#   erhält alle anderen Abschnitte einer bestehenden Datei.
# =============================================================================

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 5
APP_NAME = "situation_report"

#: Modulnamen, die einen Abschnitt im Projekt-Template haben dürfen.
MODULE_BUILD_REPORTS = "build_reports"
MODULE_TRANSFORM_DATA = "transform_data"
MODULE_TESTDATA_GENERATOR = "testdata_generator"
MODULE_HELPER = "helper"

DEFAULT_LANGUAGE = "de"


def _normalise(data: Any) -> dict[str, Any]:
    """
    Bring a raw parsed JSON object into the v5 envelope shape.

    A v5 file already has a ``modules`` mapping and is returned as-is (with
    guaranteed keys). A legacy build_reports template (schema v4 or older: a
    flat dict without ``modules``) is wrapped so its content becomes the
    ``build_reports`` section. The language is lifted from the legacy flat
    dict if present.

    Args:
        data: Raw object parsed from the template JSON file.

    Returns:
        Envelope dict with keys ``schema``, ``app``, ``language``, ``modules``.

    Raises:
        ValueError: If ``data`` is not a JSON object.
    """
    if not isinstance(data, dict):
        raise ValueError("Template file does not contain a JSON object.")

    if isinstance(data.get("modules"), dict):
        modules = {
            str(name): dict(section)
            for name, section in data["modules"].items()
            if isinstance(section, dict)
        }
        language = str(data.get("language", DEFAULT_LANGUAGE))
        return {
            "schema": int(data.get("schema", SCHEMA_VERSION)),
            "app": str(data.get("app", APP_NAME)),
            "language": language,
            "modules": modules,
        }

    # Legacy v4 (or older) build_reports template: flat dict without "modules".
    language = str(data.get("language", DEFAULT_LANGUAGE))
    return {
        "schema": SCHEMA_VERSION,
        "app": APP_NAME,
        "language": language,
        "modules": {MODULE_BUILD_REPORTS: dict(data)},
    }


def load_template(path: Path) -> dict[str, Any]:
    """
    Read a project-template file and return it in the v5 envelope shape.

    Legacy build_reports-only templates are transparently upgraded in memory
    (the file on disk is left untouched until the next save).

    Args:
        path: Path to the JSON template file.

    Returns:
        Envelope dict: ``{"schema", "app", "language", "modules": {name: {...}}}``.

    Raises:
        ValueError: If the file is not a JSON object.
        OSError / json.JSONDecodeError: On read or parse failure.
    """
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return _normalise(raw)


def get_section(envelope: dict[str, Any], module_name: str) -> dict[str, Any]:
    """
    Return the section dict for ``module_name`` from a loaded envelope.

    Args:
        envelope:    Result of load_template().
        module_name: One of the MODULE_* constants.

    Returns:
        The module's section dict, or an empty dict if the file has no section
        for that module.
    """
    return dict(envelope.get("modules", {}).get(module_name, {}))


def save_template(
    path: Path,
    module_name: str,
    section: dict[str, Any],
    language: str | None = None,
) -> None:
    """
    Write ``section`` as the given module's part of the project template.

    If the target file already exists it is read first (legacy v4 files are
    upgraded), and only the named module's section is replaced — every other
    module's section is preserved. If the file does not exist a new v5 template
    containing just this module's section is created.

    Args:
        path:        Destination JSON file.
        module_name: One of the MODULE_* constants — which section to write.
        section:     JSON-serialisable dict for this module.
        language:    Optional language code to store at the envelope level.
                     If None, an existing language is kept (or the default).
    """
    target = Path(path)
    if target.is_file():
        try:
            envelope = load_template(target)
        except (ValueError, json.JSONDecodeError, OSError):
            envelope = _normalise({})
    else:
        envelope = _normalise({})

    envelope["modules"][module_name] = dict(section)
    if language is not None:
        envelope["language"] = language

    payload = {
        "schema": SCHEMA_VERSION,
        "app": APP_NAME,
        "language": envelope.get("language", DEFAULT_LANGUAGE),
        "modules": envelope["modules"],
    }
    target.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
