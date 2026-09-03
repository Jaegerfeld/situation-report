# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Regressionsschutz für die Release-Paketierung (Auslöser: v0.21.0 —
#   das neue `sources`-Package fehlte in den Kopierlisten von
#   release.yml, der Windows-Launcher zeigte „No module named
#   'sources'"). Zwei Verteidigungslinien:
#   1) Listen-Abgleich: Jedes Top-Level-Package des Repos muss in BEIDEN
#      Plattform-Kopierlisten der release.yml stehen — ein neues Package
#      macht diesen Test rot, bis die Paketierung nachgezogen ist.
#   2) Bundle-Import-Smoke: Ein Mini-Bundle wird exakt aus den Listen der
#      release.yml zusammenkopiert und die GUI-Einstiege werden in einem
#      Subprozess importiert, dessen Modulpfad NUR das Bundle sieht — der
#      echte Beweis, dass das Zip startfähig wäre.
# =============================================================================

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RELEASE_YML = REPO / ".github" / "workflows" / "release.yml"

#: Top-level directories that are intentionally NOT shipped.
_NOT_SHIPPED_DIRS = {"tests", "sources_tests"}


def _local_packages() -> set[str]:
    """Every top-level package directory of the repo (has __init__.py)."""
    packages = set()
    for entry in REPO.iterdir():
        if (entry.is_dir() and entry.name not in _NOT_SHIPPED_DIRS
                and not entry.name.startswith(".")
                and (entry / "__init__.py").is_file()):
            packages.add(entry.name)
    return packages


def _release_module_lists() -> list[tuple[str, set[str]]]:
    """
    Extract the per-platform module copy lists from release.yml.

    Windows:  foreach ($mod in 'a','b',...) {
    Unix:     for mod in a b c ...; do
    """
    text = RELEASE_YML.read_text(encoding="utf-8")
    lists: list[tuple[str, set[str]]] = []

    windows = re.search(r"foreach \(\$mod in ([^)]+)\)", text)
    assert windows, "release.yml: Windows module list not found."
    lists.append(("windows",
                  set(re.findall(r"'([^']+)'", windows.group(1)))))

    unix = re.search(r"for mod in ([^;]+); do", text)
    assert unix, "release.yml: Unix module list not found."
    lists.append(("unix", set(unix.group(1).split())))
    return lists


def _release_file_lists() -> list[tuple[str, set[str]]]:
    """Extract the per-platform top-level FILE copy lists from release.yml."""
    text = RELEASE_YML.read_text(encoding="utf-8")
    lists: list[tuple[str, set[str]]] = []
    windows = re.search(r"foreach \(\$f in ('[^)]*\.py[^)]*')\)", text)
    assert windows, "release.yml: Windows file list not found."
    lists.append(("windows",
                  set(re.findall(r"'([^']+)'", windows.group(1)))))
    unix = re.search(r"for f in ([^;]*\.py[^;]*); do", text)
    assert unix, "release.yml: Unix file list not found."
    lists.append(("unix", set(unix.group(1).split())))
    return lists


class TestReleaseLists:
    def test_every_local_package_is_in_both_platform_lists(self) -> None:
        """The v0.21.0 lesson: a package the code imports must ship."""
        packages = _local_packages()
        assert "sources" in packages  # sanity: the trigger of this test
        for platform, listed in _release_module_lists():
            missing = packages - listed
            assert not missing, (
                f"release.yml [{platform}]: package(s) {sorted(missing)} "
                f"missing from the copy list — the shipped app would fail "
                f"with 'No module named ...'. Add them to BOTH platform "
                f"lists in .github/workflows/release.yml.")

    def test_shared_top_level_modules_ship(self) -> None:
        for platform, files in _release_file_lists():
            for required in ("version.py", "project_template.py"):
                assert required in files, (
                    f"release.yml [{platform}]: '{required}' missing from "
                    f"the file copy list.")


class TestBundleImportSmoke:
    def test_gui_entrypoints_import_from_a_bundle_built_from_the_lists(
            self, tmp_path: Path) -> None:
        """
        Copy exactly what release.yml ships and import every GUI entry in a
        subprocess whose module path sees ONLY the bundle (cwd) — the same
        situation as the unpacked zip.
        """
        bundle = tmp_path / "bundle"
        bundle.mkdir()
        modules = _release_module_lists()[0][1]
        for module in sorted(modules):
            source = REPO / module
            if source.is_dir():
                shutil.copytree(
                    source, bundle / module,
                    ignore=shutil.ignore_patterns("__pycache__"))
        for _platform, files in _release_file_lists()[:1]:
            for name in files:
                if (REPO / name).is_file() and name.endswith(".py"):
                    shutil.copy(REPO / name, bundle / name)

        # Isolation über cwd: `-c` setzt sys.path[0] auf das Bundle; das
        # Repo ist nirgends im Pfad. PYTHONPATH wird entfernt, der Rest
        # der Umgebung bleibt (Path.home() etc. brauchen sie).
        import os

        env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
        code = ("import portfolio.gui, portfolio.cli, launcher.gui, "
                "testdata_generator.gui, get_data.gui, sources.cli; "
                "print('BUNDLE_IMPORTS_OK')")
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=bundle, capture_output=True, text=True, timeout=120,
            env=env,
        )
        assert "BUNDLE_IMPORTS_OK" in result.stdout, (
            f"GUI imports failed inside the bundle — the release zip would "
            f"be broken.\nstderr: {result.stderr[-800:]}")
