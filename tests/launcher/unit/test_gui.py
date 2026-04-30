# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       30.04.2026
# Geändert:       30.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für den SituationReport Launcher. Prüft Modul-Registry,
#   Übersetzungsvollständigkeit für alle Sprachen und Sprachumschalt-Logik.
# =============================================================================

from launcher.gui import (
    LANG_DE,
    LANG_EN,
    LANG_FR,
    LANG_PT,
    LANG_RO,
    _LANG_ORDER,
    _MODULES,
    _T,
)

_ALL_LANGS = (LANG_DE, LANG_EN, LANG_RO, LANG_PT, LANG_FR)

_REQUIRED_KEYS = {
    "window_title",
    "btn_launch",
    "lbl_planned",
    "tip_language",
    "tip_manual",
    "mod_build_reports_name",
    "mod_build_reports_desc",
    "mod_transform_data_name",
    "mod_transform_data_desc",
    "mod_get_data_name",
    "mod_get_data_desc",
    "mod_simulate_name",
    "mod_simulate_desc",
    "mod_testdata_generator_name",
    "mod_testdata_generator_desc",
}


class TestModuleRegistry:
    """Tests for the _MODULES registry — structure and content."""

    def test_all_entries_have_module_id(self):
        """Every module entry has a non-empty module_id."""
        for entry in _MODULES:
            assert entry.module_id

    def test_all_entries_have_icon(self):
        """Every module entry has a non-empty icon string."""
        for entry in _MODULES:
            assert entry.icon

    def test_all_entries_have_available_flag(self):
        """Every module entry has an explicit boolean available field."""
        for entry in _MODULES:
            assert isinstance(entry.available, bool)

    def test_exactly_two_available_modules(self):
        """Exactly two modules are marked as available (build_reports and transform_data)."""
        available = [e for e in _MODULES if e.available]
        assert len(available) == 2

    def test_build_reports_is_available(self):
        """build_reports is available."""
        ids = {e.module_id for e in _MODULES if e.available}
        assert "build_reports" in ids

    def test_transform_data_is_available(self):
        """transform_data is available."""
        ids = {e.module_id for e in _MODULES if e.available}
        assert "transform_data" in ids

    def test_five_modules_total(self):
        """The registry contains exactly five module entries."""
        assert len(_MODULES) == 5

    def test_all_module_ids_unique(self):
        """All module_ids in the registry are unique."""
        ids = [e.module_id for e in _MODULES]
        assert len(ids) == len(set(ids))

    def test_every_module_has_translation_keys(self):
        """Every module_id has name and desc keys in every language dict."""
        for entry in _MODULES:
            for lang in _ALL_LANGS:
                assert f"mod_{entry.module_id}_name" in _T[lang], (
                    f"Missing 'mod_{entry.module_id}_name' in {lang}"
                )
                assert f"mod_{entry.module_id}_desc" in _T[lang], (
                    f"Missing 'mod_{entry.module_id}_desc' in {lang}"
                )


class TestTranslations:
    """Tests for translation completeness and consistency across all languages."""

    def test_all_languages_present_in_translation_table(self):
        """All five language codes are present in the translation table."""
        for lang in _ALL_LANGS:
            assert lang in _T, f"Language '{lang}' missing from _T"

    def test_all_required_keys_present_in_all_languages(self):
        """Every required translation key is present in all five languages."""
        for lang in _ALL_LANGS:
            for key in _REQUIRED_KEYS:
                assert key in _T[lang], f"Key '{key}' missing in language '{lang}'"

    def test_no_language_has_empty_values(self):
        """No translation value is an empty string."""
        for lang in _ALL_LANGS:
            for key, value in _T[lang].items():
                assert value, f"Empty value for key '{key}' in language '{lang}'"

    def test_window_title_is_situationreport_in_all_languages(self):
        """The window title is 'SituationReport' in all languages."""
        for lang in _ALL_LANGS:
            assert _T[lang]["window_title"] == "SituationReport"


class TestLanguageOrder:
    """Tests for the _LANG_ORDER cycle used by the flag button."""

    def test_lang_order_contains_all_five_languages(self):
        """_LANG_ORDER contains exactly the five supported language codes."""
        assert set(_LANG_ORDER) == set(_ALL_LANGS)

    def test_lang_order_has_no_duplicates(self):
        """_LANG_ORDER has no repeated language codes."""
        assert len(_LANG_ORDER) == len(set(_LANG_ORDER))

    def test_cycle_from_each_language(self):
        """Cycling through _LANG_ORDER from any start returns to the start after N steps."""
        n = len(_LANG_ORDER)
        for start in _LANG_ORDER:
            idx = _LANG_ORDER.index(start)
            for _ in range(n):
                idx = (idx + 1) % n
            assert _LANG_ORDER[idx] == start

    def test_de_is_first_in_lang_order(self):
        """German is the first entry in _LANG_ORDER."""
        assert _LANG_ORDER[0] == LANG_DE
