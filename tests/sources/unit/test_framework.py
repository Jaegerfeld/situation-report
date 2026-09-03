# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für das Quellen-Framework (C1/C2): Provider-Discovery
#   (neue Quelle = eine Datei), Record-Normalisierung, Datei-Provider,
#   CLI (fetch mit Kombination mehrerer Quellen, providers-Liste,
#   Fehlerbilder). Kein Netzwerk.
# =============================================================================

from __future__ import annotations

import json

import pytest

from sources.base import (
    KIND_DORA,
    KIND_SLO,
    SloRecord,
    discover_providers,
    record_from_dict,
    record_to_dict,
)
from sources.cli import fetch_records
from sources.cli import main as cli_main
from sources.providers.file_source import PROVIDER as FILE_PROVIDER


class TestDiscovery:
    def test_finds_all_shipped_providers_with_their_kinds(self) -> None:
        providers = discover_providers()
        assert set(providers) == {"file", "prometheus", "github", "gitlab",
                                  "sonarqube"}
        assert providers["file"].kinds == (KIND_SLO, KIND_DORA, "quality")
        assert providers["github"].kinds == (KIND_DORA,)
        assert providers["prometheus"].kinds == (KIND_SLO,)


class TestRecords:
    def test_from_dict_ignores_unknown_keys(self) -> None:
        record = record_from_dict(KIND_SLO, {
            "service": "API", "slo": "x", "target_pct": 99.9,
            "future_field": "ignored"})
        assert isinstance(record, SloRecord)
        assert record.target_pct == 99.9

    def test_from_dict_missing_required_raises(self) -> None:
        with pytest.raises(ValueError, match="slo record"):
            record_from_dict(KIND_SLO, {"sli_pct": 1.0})

    def test_to_dict_drops_empty_optionals(self) -> None:
        d = record_to_dict(SloRecord("API", "x", 99.9))
        assert "sli_pct" not in d
        assert "source" not in d
        assert d["window"] == "30d"


class TestFileProvider:
    def test_reads_envelope_and_bare_list_and_defaults_source(self, tmp_path) -> None:
        path = tmp_path / "slo.json"
        path.write_text(json.dumps({"records": [
            {"service": "A", "slo": "x", "target_pct": 99.0}]}),
            encoding="utf-8")
        [record] = FILE_PROVIDER.fetch(KIND_SLO, {"path": str(path)},
                                       lambda m: None)
        assert record.source == "file:slo.json"

        bare = tmp_path / "bare.json"
        bare.write_text(json.dumps([
            {"service": "B", "slo": "y", "target_pct": 99.0,
             "source": "kept"}]), encoding="utf-8")
        [record] = FILE_PROVIDER.fetch(KIND_SLO, {"path": str(bare)},
                                       lambda m: None)
        assert record.source == "kept"

    def test_missing_file_and_bad_shape_raise(self, tmp_path) -> None:
        with pytest.raises(RuntimeError, match="does not exist"):
            FILE_PROVIDER.fetch(KIND_SLO, {"path": str(tmp_path / "x.json")},
                                lambda m: None)
        bad = tmp_path / "bad.json"
        bad.write_text('{"foo": 1}', encoding="utf-8")
        with pytest.raises(RuntimeError, match="records"):
            FILE_PROVIDER.fetch(KIND_SLO, {"path": str(bad)}, lambda m: None)


class TestFetchRecordsAndCli:
    def _slo_file(self, tmp_path, name: str, service: str) -> str:
        path = tmp_path / name
        path.write_text(json.dumps({"records": [
            {"service": service, "slo": "x", "target_pct": 99.0,
             "sli_pct": 99.5}]}), encoding="utf-8")
        return str(path)

    def test_combines_two_sources_keeping_origin(self, tmp_path) -> None:
        configs = [
            {"provider": "file", "path": self._slo_file(tmp_path, "a.json", "A")},
            {"provider": "file", "path": self._slo_file(tmp_path, "b.json", "B")},
        ]
        records = fetch_records(KIND_SLO, configs, log=lambda m: None)
        assert [r["service"] for r in records] == ["A", "B"]
        assert records[0]["source"] == "file:a.json"
        assert records[1]["source"] == "file:b.json"

    def test_unknown_provider_and_kind_mismatch(self, tmp_path) -> None:
        with pytest.raises(RuntimeError, match="Unknown provider"):
            fetch_records(KIND_SLO, [{"provider": "nope"}], log=lambda m: None)
        with pytest.raises(RuntimeError, match="not 'slo'"):
            fetch_records(KIND_SLO, [{"provider": "github"}],
                          log=lambda m: None)

    def test_cli_fetch_writes_register(self, tmp_path, capsys) -> None:
        cfg = tmp_path / "cfg.json"
        cfg.write_text(json.dumps({"sources": [
            {"provider": "file",
             "path": self._slo_file(tmp_path, "a.json", "A")}]}),
            encoding="utf-8")
        out = tmp_path / "register.json"
        assert cli_main(["fetch", "--kind", "slo", "--config", str(cfg),
                         "--output", str(out)]) == 0
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["kind"] == "slo"
        assert len(data["records"]) == 1

    def test_cli_lists_providers(self, capsys) -> None:
        assert cli_main(["providers"]) == 0
        out = capsys.readouterr().out
        for name in ("file", "prometheus", "github", "gitlab", "sonarqube"):
            assert name in out

    def test_cli_reports_config_errors(self, tmp_path, capsys) -> None:
        missing = tmp_path / "missing.json"
        assert cli_main(["fetch", "--kind", "slo", "--config", str(missing),
                         "--output", str(tmp_path / "o.json")]) == 1
        assert "cannot read config" in capsys.readouterr().err
