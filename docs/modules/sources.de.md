# sources

Steckbares Framework für externe Kennzahlen (Roadmap C1/C2): SLO-/SLI-Daten,
DORA-Liefermetriken und Code-Qualität — aus **austauschbaren, kombinierbaren**
Quellen, in normiertes Register-JSON, das der Portfolio-Report rendert.

**Status:** umgesetzt (alpha)

## Design: drei Garantien

1. **Austauschbar** — der Report sieht nie einen Hersteller. Provider
   übersetzen ein Fremdsystem in drei normierte Record-Contracts
   (`SloRecord`, `DoraRecord`, `QualityRecord`); Status-/Tier-Urteile
   fallen zentral in den Registern (`portfolio/slo_config.py`,
   `portfolio/dora_config.py`) — jede Quelle wird nach derselben Regel
   beurteilt.
2. **Kombinierbar** — eine Abruf-Config darf mehrere Quellen listen; ihre
   Records fließen in EIN Register, jede Zeile behält ihre Herkunft
   (Quellen-Spalte im Report).
3. **Leicht erweiterbar** — eine neue Quelle ist EINE Datei in
   `sources/providers/` mit einem `PROVIDER`-Objekt; die Auto-Discovery
   findet sie, nirgends ist ein Register zu pflegen (Rezept unten).

Der Datei-Provider ist der universelle Rückfallweg (das C3-Prinzip): Jedes
System ist heute anbindbar, indem es das normierte JSON exportiert — ganz
ohne API-Freigabe.

## Mitgelieferte Provider

| Provider | Art | Warum diese Referenz |
|---|---|---|
| `file` | slo, dora, quality | Universeller Weg 1 — funktioniert ohne jeden API-Zugang |
| `prometheus` | slo | De-facto-Standard des OSS-Monitorings (~77 % Produktionsnutzung; liegt hinter den meisten Grafana-Installationen); kommerzielle Marktführer (Datadog ~24 % APM-Anteil, Dynatrace) docken via `file` oder künftigen Provider an |
| `github` | dora | Roberts Wahl, größte Plattform — **keine native DORA-API**, die vier Kennzahlen werden *abgeleitet*: Deployments (Frequenz), jüngste Deployment-Status (CFR), gemergte PRs (Lead Time, Median created→merged), Incident-Issues (MTTR). Näherungen dokumentiert und konfigurierbar (Environment, Incident-Label, Caps) |
| `gitlab` | dora | Das einzige marktübliche System mit **nativer DORA-API** (`/api/v4/…/dora/metrics`, Ultimate) — als zweite Referenz behalten: der Austauschbarkeits-Beweis |
| `sonarqube` | quality | De-facto-Standard der statischen Qualität (von der Roadmap benannt): Coverage, Maintainability-Rating, kritische Verstöße |

Tokens kommen immer aus Umgebungsvariablen (`PROMETHEUS_TOKEN`,
`GITHUB_TOKEN`, `GITLAB_TOKEN`, `SONAR_TOKEN`, per `token_env`
übersteuerbar), werden nie gespeichert und nie geloggt; 401/403-Meldungen
zeigen auf die ggf. fehlende Freigabe und den Datei-Weg als Ausweichroute.

## CLI

```bash
python -m sources providers
python -m sources fetch --kind slo --config slo_quellen.json --output slo.json
```

Eine Config ist ein Quell-Objekt — oder eine Kombination:

```json
{
  "sources": [
    {"provider": "prometheus", "base_url": "https://prom.intern",
     "services": [{"service": "Order API", "slo": "availability",
                    "target_pct": 99.9,
                    "sli_query": "avg_over_time(up[30d])", "scale": 100}]},
    {"provider": "file", "path": "dynatrace_export.json"}
  ]
}
```

Der Output ist das Register-JSON, das die Solution-Config referenziert
(`"slo": "slo.json"`, `"dora": "dora.json"`); der Report rendert daraus
**Service Levels & Error Budgets** (breached zuerst; zentrale Budget-Regel:
verbraucht = (100−SLI)/(100−Ziel), at risk unter 25 % Rest) und **Delivery
Performance (DORA) & Code Quality** (Tier je Kennzahl an den
veröffentlichten DORA-Schwellen, Unit-Tier = schwächste Kennzahl;
Qualitätstabelle darunter).

## Rezept: eigene Quelle in ~30 Zeilen

`sources/providers/mein_system.py` anlegen:

```python
from sources.base import KIND_SLO, SloRecord
from sources.http import bearer, get_json, token_from_env

class MeinSystemSource:
    provider_id = "mein_system"
    kinds = (KIND_SLO,)

    def fetch(self, kind, config, log):
        headers = bearer(token_from_env(config, "MEIN_SYSTEM_TOKEN"))
        data = get_json(config["base_url"] + "/api/slos", headers, "MeinSystem")
        return [SloRecord(service=e["name"], slo=e["ziel"],
                          target_pct=e["target"], sli_pct=e["ist"],
                          source="mein_system") for e in data]

PROVIDER = MeinSystemSource()
```

Fertig — `python -m sources providers` listet sie, `fetch` kann sie nutzen,
und sie kombiniert frei mit jeder anderen Quelle.

## Architektur

```
sources/
├── base.py            Record-Contracts, Provider-Protokoll, Auto-Discovery
├── http.py            Gemeinsames urllib-GET + Auth-Header + Fehler-Mapping
├── cli.py             Befehle fetch (Mehr-Quellen-Merge) und providers
└── providers/
    ├── file_source.py Universeller Datei-Weg (alle Arten)
    ├── prometheus.py  C1-Referenz (SLO/SLI per Instant-Query)
    ├── github_dora.py C2-Referenz (DORA aus GitHub abgeleitet)
    ├── gitlab_dora.py C2-Alternative (native DORA-API)
    └── sonarqube.py   C2-Qualität (Component-Measures)
```

Nur Standardbibliothek. Die REST-Provider sind vollständig mock-getestet;
der Praxistest gegen echte Instanzen ist der verbleibende Schritt (wie bei
get_data).
