# simulate

Monte-Carlo-Forecast auf Basis des historischen Tagesdurchsatzes (Throughput).
Beantwortet zwei Fragen probabilistisch – ohne Story-Point-Schätzung:

- **Wie viele Items** schaffen wir in einem Zeitraum? (Kapazitäts-Forecast)
- **Wann ist** ein Backlog von N Items **fertig**? (Termin-Forecast, optional mit
  Scope-Wachstum über eine Split-Rate)
- **Schaffen wir den Scope bis Datum X?** – bei gesetztem `--backlog` zusätzlich
  eine Konfidenz-Gauge: P(mindestens Backlog-Items bis zum Horizont-Datum). Das
  ist derselbe Wert wie der Punkt der Exceedance-Kurve an der Stelle „Backlog“.

Die Ergebnisse werden als Exceedance-Perzentile dargestellt – z. B. „mit 85 %
Konfidenz mindestens X Items“ bzw. „spätestens an Tag Y / Datum Z“ – mit
Referenzlinien bei 85/75/50 %.

## Aufruf

GUI (ohne Argumente):

```
python -m simulate
```

CLI:

```
python -m simulate ART_A_IssueTimes.xlsx --horizon 84 --backlog 50 \
    --runs 25000 --split-rate 0.1 --seed 1 --output forecast.html
```

| Option | Bedeutung |
|---|---|
| `--cfd FILE` | Optionale CFD-Datei. |
| `--history-days N` | Länge des History-Fensters (Standard 180). |
| `--history-end YYYY-MM-DD` | Exklusives Enddatum (Standard: heute). |
| `--horizon DAYS` | Vorhersagehorizont (Standard 84). |
| `--backlog N` | Aktiviert zusätzlich den Termin-Forecast für N Items. |
| `--runs N` | Anzahl Monte-Carlo-Läufe (Standard 25000). |
| `--split-rate R` | Erwartete neue Items je erledigtem Item (Scope-Wachstum). |
| `--seed N` | Seed für reproduzierbare Läufe. |
| `--output FILE` | HTML-Report-Zieldatei. |

## GUI: Sprache & Templates

Wie die übrigen Modul-GUIs unterstützt simulate fünf Sprachen
(Deutsch, Englisch, Rumänisch, Portugiesisch, Französisch). Die
**Flaggen-Schaltfläche** oben rechts schaltet die Oberfläche um; die Wahl wird
in `~/.situation_report/prefs.json` gespeichert und von allen Modulen geteilt.

Über das Menü **Templates** lassen sich die aktuellen Eingaben speichern und
laden:

- **Speichern** legt Dateien und Parameter samt Sprache im gemeinsamen
  Projekt-Template ab (`project_template`, Abschnitt `simulate`).
- **Laden** stellt Eingaben und Sprache wieder her. Dieselbe Template-Datei
  wird von den anderen Modulen mitgenutzt – jedes Modul schreibt nur seinen
  eigenen Abschnitt.

## Methode

Reine Standardbibliothek (kein numpy/pandas): Aus dem History-Fenster –
**inklusive Null-Tage** – wird die empirische Tagesdurchsatz-Verteilung gebildet
und über `runs` Läufe neu gezogen. Inspiriert vom R-Vorbild des Teams und von
Daniel Vacanti, *Actionable Agile Metrics for Predictability*.
