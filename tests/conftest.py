# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       14.04.2026
# Geändert:       14.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Gemeinsame pytest-Fixtures für alle Tests des Projekts. Stellt Pfade zu
#   Testdaten (ART_A-Datensatz, Workflow-Definitionen) und Fixture-Dateien
#   bereit. Module-scoped Fixtures verhindern wiederholtes Einlesen großer
#   Dateien über mehrere Tests hinweg.
# =============================================================================

from pathlib import Path
import pytest

FIXTURES_DIR = Path(__file__).parent / "transform_data" / "fixtures"
TESTDATA_DIR = Path(__file__).parent.parent / "transform_data"


@pytest.fixture
def simple_workflow_file() -> Path:
    return FIXTURES_DIR / "workflow_simple.txt"


@pytest.fixture(scope="module")
def ata_json() -> Path:
    return TESTDATA_DIR / "ART_A.json"


@pytest.fixture(scope="module")
def ata_workflow() -> Path:
    return TESTDATA_DIR / "workflow_ART_A - original.txt"
