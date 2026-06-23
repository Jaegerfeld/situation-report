# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       23.06.2026
# Geändert:       23.06.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Konsistenz-Wächter für das Packaging. Jedes im Launcher als verfügbar
#   markierte Modul muss von den Release- und Dev-Build-Workflows in das
#   Bundle kopiert werden, sonst startet ein Launcher-Button in der gebauten
#   App ins Leere. Der Test fängt genau diese Lücke ab (historisch z. B. das
#   anfangs vergessene 'portfolio'-Modul) und vergleicht die Modul-Registry
#   gegen die tatsächlichen Copy-Listen in den Workflow-YAMLs.
# =============================================================================

from pathlib import Path

import pytest

from launcher.gui import _MODULES

_REPO_ROOT = Path(__file__).resolve().parents[3]
_WORKFLOWS = [
    _REPO_ROOT / ".github" / "workflows" / "release.yml",
    _REPO_ROOT / ".github" / "workflows" / "dev-build.yml",
]

# Modules a launcher button can actually start. These MUST be bundled.
_AVAILABLE_MODULES = sorted(e.module_id for e in _MODULES if e.available)


@pytest.fixture(scope="module")
def workflow_texts() -> dict[str, str]:
    """Read each packaging workflow YAML once and return {filename: text}."""
    texts = {}
    for wf in _WORKFLOWS:
        assert wf.is_file(), f"Workflow file missing: {wf}"
        texts[wf.name] = wf.read_text(encoding="utf-8")
    return texts


def test_available_modules_nonempty() -> None:
    """Sanity check: the registry exposes at least one available module."""
    assert _AVAILABLE_MODULES, "No available modules found in launcher._MODULES"


@pytest.mark.parametrize("module_id", _AVAILABLE_MODULES)
@pytest.mark.parametrize("workflow", [wf.name for wf in _WORKFLOWS])
def test_available_module_is_bundled(
    module_id: str, workflow: str, workflow_texts: dict[str, str]
) -> None:
    """Every available launcher module appears in each workflow's copy list.

    Guards against shipping a build whose launcher offers a module the
    packaging step never copied into the bundle.
    """
    text = workflow_texts[workflow]
    assert f"'{module_id}'" in text or f" {module_id} " in text, (
        f"Module '{module_id}' is marked available in the launcher but is not "
        f"referenced in {workflow}'s module copy list. Add it there so the "
        f"built app can launch it."
    )


def test_launcher_itself_is_bundled(workflow_texts: dict[str, str]) -> None:
    """The launcher package itself must be bundled by every workflow."""
    for workflow, text in workflow_texts.items():
        assert "'launcher'" in text or " launcher " in text, (
            f"The 'launcher' package is not referenced in {workflow}'s copy list."
        )
