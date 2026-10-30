# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       14.04.2026
# Geändert:       13.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Gemeinsame pytest-Fixtures für alle Tests des Projekts. Stellt Pfade zu
#   Testdaten (ART_A-Datensatz, Workflow-Definitionen) und Fixture-Dateien
#   bereit. Module-scoped Fixtures verhindern wiederholtes Einlesen großer
#   Dateien über mehrere Tests hinweg. Seit 13.10.2026 außerdem: jeder Test
#   bekommt eine eigene Präferenz-Datei — die GUI-Module schreiben sonst in
#   ~/.situation_report/prefs.json des Entwicklers (Sprache, Modell), und
#   ein Test kann den nächsten über diese Datei beeinflussen.
# =============================================================================

from pathlib import Path

import pytest

TESTDATA_DIR = Path(__file__).parent / "testdata"
ART_A_DIR = TESTDATA_DIR / "ART_A"
FIXTURES_DIR = TESTDATA_DIR / "fixtures"


@pytest.fixture
def simple_workflow_file() -> Path:
    return FIXTURES_DIR / "workflow_simple.txt"


@pytest.fixture(scope="module")
def ata_json() -> Path:
    return ART_A_DIR / "ART_A.json"


@pytest.fixture(scope="module")
def ata_workflow() -> Path:
    return ART_A_DIR / "workflow_ART_A.txt"


#: GUI modules that keep a module-level ``_PREFS_PATH`` (~/.situation_report/prefs.json).
_PREF_MODULES = (
    "build_reports.gui", "get_data.gui", "harmonisation.gui", "helper.gui",
    "launcher.gui", "portfolio.gui", "simulate.gui", "testdata_generator.gui",
    "transform_data.gui",
    "testdata_generator.i18n",
)


@pytest.fixture(autouse=True)
def isolate_user_prefs(monkeypatch, tmp_path):
    """
    Point every GUI's preference file at a per-test folder.

    The GUIs read and write ~/.situation_report/prefs.json at module level.
    Without this fixture a test that toggles the language or remembers an
    LLM choice overwrites the developer's real preferences and leaks its
    state into later tests (the flaky acceptance test of 12.10.2026 started
    in whatever language the previous test had saved). Modules that are not
    imported by the time a test runs are imported here so the patch holds
    even for a first import inside the test.
    """
    import importlib

    prefs = tmp_path / "prefs" / "prefs.json"
    for name in _PREF_MODULES:
        try:
            module = importlib.import_module(name)
        except Exception:  # pragma: no cover - a GUI without its deps stays untouched
            continue
        if hasattr(module, "_PREFS_PATH"):
            monkeypatch.setattr(module, "_PREFS_PATH", prefs)
    try:
        from build_reports.gui import BuildReportsApp
        monkeypatch.setattr(BuildReportsApp, "_EXCL_DEFAULTS_PATH",
                            tmp_path / "prefs" / "excl_defaults.json")
    except Exception:  # pragma: no cover
        pass
    yield prefs
