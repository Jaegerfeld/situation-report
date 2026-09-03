# Tutorial: Eine eigene Datenquelle anbinden

**Zielgruppe:** Entwickler:innen, die noch nie eine Kennzahlen-Quelle an
SituationReport angebunden haben. **Dauer:** rund 30 Minuten.
**Voraussetzungen:** das Repository, Python 3.11+, keine externen Systeme —
alles läuft gegen das Demo-Szenario. **Am Ende:** dein eigener Provider
speist den Portfolio-Report.

---

## 1. Das Modell in drei Begriffen

Alles im `sources`-Framework dreht sich um drei Dinge:

1. **Record** — das normierte Ergebnis. Für ein SLO sieht es so aus:

    ```json
    {"service": "Order API", "slo": "availability",
     "target_pct": 99.9, "sli_pct": 99.95,
     "window": "30d", "source": "csv:slos.csv"}
    ```

    Es gibt drei Record-Arten: `slo`, `dora`, `quality`. Der Report sieht
    immer nur Records — nie dein System.

2. **Provider** — ein Übersetzer: Er liest *dein* System (eine Datei, eine
   REST-API, was auch immer) und gibt Records zurück. Eine Python-Datei,
   eine Klasse.

3. **Register** — die JSON-Datei, die ein Abruf schreibt
   (`{"schema": 1, "kind": "slo", "records": [...]}`). Die Solution-Config
   referenziert sie (`"slo": "slo.json"`), der Report rendert sie.

Eine Regel hält alles vergleichbar: **Provider urteilen nie.** Ob ein SLO
*breached* oder eine DORA-Einheit *low* ist, entscheidet eine zentrale
Regel — dieselbe für jede Quelle. Dein Provider übersetzt nur Werte.

---

## 2. Erst benutzen, dann bauen (5 Minuten)

Erzeuge das Demo-Portfolio und sieh dir zuerst ein fertiges Register an:

```bash
python -m testdata_generator --scenario portfolio --output demo --seed 42
python -m sources providers
```

`providers` listet jede entdeckte Quelle (`csv`, `file`, `github`,
`gitlab`, `prometheus`, `sonarqube`). Jetzt dein erster Abruf — mit dem
`file`-Provider und einem Register, das das Szenario schon erzeugt hat:

```bash
echo {"provider": "file", "path": "demo/slo_alpha.json"} > meine_quellen.json
python -m sources fetch --kind slo --config meine_quellen.json --output mein_slo.json
```

Öffne `mein_slo.json`: Das ist das Zielformat. Egal welche Quelle du
anbindest — genau das kommt heraus. Deshalb sind Quellen austauschbar.

---

## 3. Deinen eigenen Provider bauen, Schritt für Schritt

Wir binden eine **CSV-Datei** als Quelle an (Teams pflegen SLO-Werte oft
in einer Tabelle). Kein Server nötig — und das Muster ist für jedes System
identisch. Die fertige Referenz liegt in `sources/providers/csv_slo.py`;
tippe deine eigene Kopie zum Lernen, oder lies mit.

**Schritt 3.1 — eine Datei anlegen.** Ein Provider ist ein einzelnes Modul
in `sources/providers/`. Lege `sources/providers/my_csv.py` an:

```python
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from sources.base import KIND_SLO, SloRecord


class MyCsvSource:
    # (1) Der Name in Configs und in der `providers`-Liste.
    provider_id = "my_csv"
    # (2) Was diese Quelle liefern kann.
    kinds = (KIND_SLO,)

    # (3) Der Übersetzer: Fremdformat hinein, Records heraus.
    def fetch(self, kind, config, log):
        path = Path(config["path"])
        if not path.is_file():
            raise RuntimeError(f"my_csv: '{path}' existiert nicht.")
        fetched_at = datetime.now().isoformat(timespec="seconds")
        records = []
        with path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                records.append(SloRecord(
                    service=row["service"],
                    slo=row["slo"],
                    target_pct=float(row["target_pct"]),
                    sli_pct=float(row["sli_pct"]) if row.get("sli_pct") else None,
                    source=f"my_csv:{path.name}",
                    fetched_at=fetched_at,
                ))
        log(f"  my_csv: {len(records)} records")
        return records


# (4) Genau dieses Objekt sucht die Auto-Discovery.
PROVIDER = MyCsvSource()
```

Vier nummerierte Ideen — das ist der ganze Contract: eine Id, die Arten,
ein `fetch()`, das übersetzt, und ein `PROVIDER`-Objekt auf Modulebene.
**Nirgends ist ein Register zu pflegen**: Die Existenz der Datei ist die
Registrierung.

**Schritt 3.2 — die Discovery sehen.**

```bash
python -m sources providers
```

`my_csv: slo` erscheint in der Liste. Falls nicht: Die Datei muss in
`sources/providers/` liegen und `PROVIDER` auf Modulebene definieren.

**Schritt 3.3 — Daten geben.** Lege `team_slos.csv` an:

```text
service,slo,target_pct,sli_pct
Order API,availability,99.9,99.95
Checkout,availability,99.5,99.55
```

**Schritt 3.4 — abrufen.** Lege `csv_quelle.json` an …

```json
{"provider": "my_csv", "path": "team_slos.csv"}
```

… und führe aus:

```bash
python -m sources fetch --kind slo --config csv_quelle.json --output mein_slo.json
```

**Schritt 3.5 — in den Report.** Öffne `demo/solution_alpha.json`, setze
`"slo": "mein_slo.json"` (oder ergänze das Feld in deiner eigenen
Solution-Config). Dann rendern:

```bash
python -m portfolio demo/solution_alpha.json --output report.html --browser
```

Die Sektion **Service Levels & Error Budgets** zeigt jetzt deine
CSV-Zeilen — Status und Error-Budget wurden zentral abgeleitet, und die
Spalte *Data source* sagt `my_csv:team_slos.csv`. Deine Quelle ist
angebunden.

---

## 4. Ein REST-System statt einer Datei?

Gleiches Muster; nur `fetch()` ändert sich. Der gemeinsame Helfer
übernimmt HTTP, Auth und Fehler-Mapping:

```python
from sources.http import bearer, get_json, token_from_env

def fetch(self, kind, config, log):
    headers = bearer(token_from_env(config, "MEIN_SYSTEM_TOKEN"))
    data = get_json(config["base_url"] + "/api/slos", headers, "MeinSystem")
    return [SloRecord(service=e["name"], slo=e["ziel"],
                      target_pct=e["target"], sli_pct=e["ist"],
                      source="mein_system") for e in data]
```

Drei Regeln für REST-Provider:

- **Tokens nur aus Umgebungsvariablen** (`token_from_env`) — nie in
  Configs, nie in Logs. GUI/CLI speichern sie nie.
- `get_json` mappt Fehler für dich: Eine 401/403-Meldung verweist auf die
  womöglich fehlende API-Freigabe **und auf den Datei-Weg als
  Ausweichroute**.
- **Mit Mocks testen**, nicht gegen das Live-System: Kopiere das
  Request-Recorder-Muster aus
  `tests/sources/unit/test_rest_providers.py` — es patcht
  `sources.http._urlopen` und prüft URLs, Header und deine
  Übersetzungs-Mathematik.

---

## 5. Eine Quelle austauschen

Austauschen heißt: **die Abruf-Config ändern, sonst nichts.** Sagen wir,
die Prometheus-Freigabe ist noch nicht da, also startest du mit der CSV …

```json
{"provider": "my_csv", "path": "team_slos.csv"}
```

… und an dem Tag, an dem die Freigabe kommt, wird aus derselben Datei:

```json
{"provider": "prometheus", "base_url": "https://prom.intern",
 "services": [{"service": "Order API", "slo": "availability",
               "target_pct": 99.9,
               "sli_query": "avg_over_time(up[30d])", "scale": 100}]}
```

Denselben `fetch`-Befehl erneut ausführen; das Register behält seinen
Namen; Solution-Config und Report ändern sich überhaupt nicht. Nur die
Spalte *Data source* zeigt jetzt `prometheus:prom.intern` — die Herkunft
bleibt sichtbar, die Beurteilungsregeln bleiben identisch.

---

## 6. Zwei Quellen kombinieren

Eine Config darf eine `sources`-Liste tragen; die Records fließen in
**ein** Register, jede Zeile behält ihre Herkunft:

```json
{"sources": [
  {"provider": "prometheus", "base_url": "https://prom.intern",
   "services": [{"service": "Order API", "slo": "availability",
                 "target_pct": 99.9,
                 "sli_query": "avg_over_time(up[30d])", "scale": 100}]},
  {"provider": "my_csv", "path": "team_slos.csv"}
]}
```

Typischer Fall: Die meisten Services leben im Monitoring, zwei
Altsysteme nur in einer Tabelle — ein Register, eine Report-Sektion,
Herkunft je Zeile.

---

## 7. Quellen im Alltag verwalten

- **Inventar:** `python -m sources providers` ist die maßgebliche Liste —
  eine neue Provider-Datei erscheint automatisch, eine gelöschte
  verschwindet.
- **Tokens:** eine Umgebungsvariable je System (`PROMETHEUS_TOKEN`,
  `GITHUB_TOKEN`, `GITLAB_TOKEN`, `SONAR_TOKEN`, eigene über
  `token_env`). Tokens nie in Configs oder Code ablegen.
- **Konventionen:** eine Datei je Quelle; Provider übersetzen, sie
  urteilen nie (Status-/Tier-Regeln leben in `portfolio/slo_config.py`
  und `portfolio/dora_config.py`); nicht gemessene Werte sind `None`,
  keine Schätzung.
- **Fehler:** Eine scheiternde REST-Quelle benennt den Host und bei
  401/403 den Freigabe-Hinweis — bis die Freigabe da ist, liefere
  dieselben Daten über `file` oder `csv`.
- **Tests:** Gib deinem Provider eine kleine Testdatei neben
  `tests/sources/unit/test_csv_provider.py` — Happy Path, eine kaputte
  Eingabe, und eine Fehlermeldung, die Kolleg:innen wirklich lesen.

---

## 8. Checkliste für eine neue Quelle

1. Eine Datei in `sources/providers/` mit `provider_id`, `kinds`,
   `fetch()`, `PROVIDER`.
2. `fetch()` liefert normierte Records; Unbekanntes ist `None`; jeder
   Record setzt `source`.
3. Kein Urteil im Provider.
4. Tokens über `token_from_env`; nichts Geheimes in Logs oder Configs.
5. `python -m sources providers` listet sie.
6. Ein Abruf schreibt ein Register; der Report rendert es.
7. Mock-basierte Tests sind grün.
8. Der Rücktausch auf `file`/`csv` funktioniert weiter — das ist deine
   Ausweichroute, solange Freigaben ausstehen.
