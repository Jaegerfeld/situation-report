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
