# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       02.09.2026
# Geändert:       02.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für portfolio.dependency_config (B5): Parsen und Validieren
#   eines Dependency-Registers, Normalisierung der Status-Werte, Fehlerfälle
#   (inkl. Selbstabhängigkeit) und der Datei-Roundtrip.
# =============================================================================

from __future__ import annotations

from datetime import date

import pytest

from portfolio.dependency_config import (
    DEP_BLOCKED,
    Dependency,
    DependencyRegister,
    dependencies_to_dict,
    load_dependencies,
    parse_dependencies,
    save_dependencies,
)


def _dep(dep_id: str = "D-1", **kwargs) -> dict:
    base = {"id": dep_id, "title": "Test dependency",
            "from": "ART A", "to": "ART B", "status": "on_track"}
    base.update(kwargs)
    return base


class TestParseDependencies:
    def test_minimal_valid_register(self) -> None:
        reg = parse_dependencies({"dependencies": [_dep()]})
        dep = reg.dependencies[0]
        assert dep.dep_id == "D-1"
        assert dep.from_art == "ART A"
        assert dep.to_art == "ART B"
        assert dep.status == "on_track"
        assert dep.due is None

    def test_empty_register_is_valid(self) -> None:
        assert parse_dependencies({"dependencies": []}) == DependencyRegister()

    def test_normalisation_and_full_fields(self) -> None:
        reg = parse_dependencies({"dependencies": [_dep(
            status="BLOCKED", due="2025-05-01", notes=" n ")]})
        dep = reg.dependencies[0]
        assert dep.status == DEP_BLOCKED
        assert dep.due == date(2025, 5, 1)
        assert dep.notes == "n"

    def test_rejects_non_object_and_missing_list(self) -> None:
        with pytest.raises(ValueError, match="JSON object"):
            parse_dependencies([])
        with pytest.raises(ValueError, match="'dependencies' list"):
            parse_dependencies({"dependencies": "x"})

    def test_rejects_empty_required_fields(self) -> None:
        with pytest.raises(ValueError, match="'id'"):
            parse_dependencies({"dependencies": [_dep(dep_id=" ")]})
        with pytest.raises(ValueError, match="'title'"):
            parse_dependencies({"dependencies": [_dep(title="")]})
        with pytest.raises(ValueError, match="'from' and 'to'"):
            parse_dependencies({"dependencies": [{**_dep(), "from": ""}]})

    def test_rejects_self_dependency(self) -> None:
        with pytest.raises(ValueError, match="must differ"):
            parse_dependencies({"dependencies": [
                {**_dep(), "from": "ART A", "to": "ART A"}]})

    def test_rejects_duplicate_id(self) -> None:
        with pytest.raises(ValueError, match="Duplicate dependency id"):
            parse_dependencies({"dependencies": [_dep(), _dep()]})

    def test_rejects_unknown_status_and_bad_due(self) -> None:
        with pytest.raises(ValueError, match="unknown status"):
            parse_dependencies({"dependencies": [_dep(status="waiting")]})
        with pytest.raises(ValueError, match="'due'"):
            parse_dependencies({"dependencies": [_dep(due="01.05.2025")]})


class TestRoundtrip:
    def test_save_and_load_roundtrip(self, tmp_path) -> None:
        register = DependencyRegister(dependencies=[
            Dependency("D-1", "API contract", "ART A", "ART B", "blocked",
                       due=date(2025, 5, 1), notes="hot"),
            Dependency("D-2", "Fixtures", "ART B", "Vendor X", "done"),
        ])
        path = tmp_path / "dependencies.json"
        save_dependencies(path, register)
        assert load_dependencies(path) == register

    def test_to_dict_omits_empty_optionals(self) -> None:
        data = dependencies_to_dict(DependencyRegister(
            dependencies=[Dependency("D-1", "T", "A", "B", "on_track")]))
        entry = data["dependencies"][0]
        assert "due" not in entry
        assert "notes" not in entry
        assert data["schema"] == 1
