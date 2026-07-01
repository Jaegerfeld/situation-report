# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       01.07.2026
# Geändert:       01.07.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für die display-unabhängigen Teile von simulate.gui: die
#   Übersetzungstabelle _T (gleiche Keys, keine Leerwerte, EN-Fallback) und die
#   Form→RunParams-Validierung. Der tkinter-Teil wird nicht instanziiert.
# =============================================================================

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from simulate.gui import (
    _T,
    LANG_DE,
    LANG_EN,
    _tr,
    parse_form,
)

_ALL_LANGS = (LANG_DE, LANG_EN)


class TestTranslations:
    def test_all_languages_present(self) -> None:
        for lang in _ALL_LANGS:
            assert lang in _T

    def test_same_keys_in_all_languages(self) -> None:
        ref = set(_T[LANG_EN].keys())
        for lang in _ALL_LANGS:
            assert set(_T[lang].keys()) == ref

    def test_no_empty_values(self) -> None:
        for lang, entries in _T.items():
            for key, value in entries.items():
                assert value, f"Empty translation [{lang}][{key}]"

    def test_fallback_to_english(self) -> None:
        assert _tr("xx", "window_title") == _T[LANG_EN]["window_title"]


class TestParseForm:
    def _defaults(self, **over: str) -> dict[str, str]:
        base = dict(
            issue_times="C:/x/ART_A_IssueTimes.xlsx", cfd="", history_days="180",
            history_end="", horizon="84", backlog="", runs="25000",
            split_rate="0.0", seed="",
        )
        base.update(over)
        return base

    def test_builds_valid_params(self) -> None:
        p = parse_form(**self._defaults(backlog="50", seed="7",
                                        history_end="2026-07-01", split_rate="0.1"))
        assert p.issue_times == Path("C:/x/ART_A_IssueTimes.xlsx")
        assert p.cfd is None
        assert p.history_days == 180
        assert p.history_end == date(2026, 7, 1)
        assert p.horizon_days == 84
        assert p.backlog == 50
        assert p.runs == 25000
        assert p.split_rate == pytest.approx(0.1)
        assert p.seed == 7

    def test_optional_fields_become_none(self) -> None:
        p = parse_form(**self._defaults())
        assert p.cfd is None and p.history_end is None
        assert p.backlog is None and p.seed is None
        assert p.split_rate == 0.0

    def test_missing_issue_times_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_form(**self._defaults(issue_times="  "))

    def test_bad_int_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_form(**self._defaults(runs="abc"))

    def test_runs_must_be_positive(self) -> None:
        with pytest.raises(ValueError):
            parse_form(**self._defaults(runs="0"))

    def test_bad_date_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_form(**self._defaults(history_end="01.07.2026"))

    def test_negative_split_rate_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_form(**self._defaults(split_rate="-0.5"))

    def test_seed_zero_allowed(self) -> None:
        assert parse_form(**self._defaults(seed="0")).seed == 0

    def test_cfd_path_kept(self) -> None:
        p = parse_form(**self._defaults(cfd="C:/x/ART_A_CFD.xlsx"))
        assert p.cfd == Path("C:/x/ART_A_CFD.xlsx")
