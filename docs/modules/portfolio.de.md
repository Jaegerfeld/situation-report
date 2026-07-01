# portfolio

Fasst mehrere bereits konfigurierte ARTs zu einem kombinierten
**Large-Solution-** oder **Portfolio-**Report zusammen — als **Pooled** (die
Solution als ein System betrachtet) oder als **Vergleich** (Einheiten
nebeneinander). Nutzt die Metriken aus `build_reports`; die einzelnen
ART-Reports werden nur referenziert, nicht verändert.

**Status:** verfügbar (Alpha)

## Handbücher

| Sprache | Download |
|---------|----------|
| Deutsch (DE) | [Benutzerhandbuch](../portfolio_Benutzerhandbuch.pdf) |
| English (EN) | [User Manual](../portfolio_UserManual.pdf) |
| Română (RO) | [Manual de Utilizator](../portfolio_ManualUtilizator.pdf) |
| Português (PT) | [Manual do Utilizador](../portfolio_ManualUtilizador.pdf) |
| Français (FR) | [Manuel d'utilisation](../portfolio_ManuelUtilisateur.pdf) |

---

## Grundbegriffe

| Begriff | Bedeutung |
|---------|-----------|
| ART | Agile Release Train / Teamgruppe — die Ebene, auf der du in `build_reports` bereits berichtest. |
| Solution | Eine Gruppierung mehrerer ARTs (referenziert deren Projekt-Templates). |
| Portfolio | Eine Gruppierung mehrerer Solutions (Portfolio > Solutions > ARTs). |
| Pooled | Modus: Alle Issues werden zu **einem** Datensatz zusammengeführt — die Solution als ein System. |
| Vergleich | Modus: Jede Einheit (ART oder Solution) wird separat nebeneinander dargestellt. |

## Oberfläche

![Screenshot der Portfolio-GUI](../assets/Portfolio-GUI.png)

## Start

### GUI

```bash
python -m portfolio
```

Oder auf die Kachel **Solutions & Portfolios** links im SituationReport-Launcher
klicken.

### Kommandozeile

```bash
python -m portfolio solution.json --mode pooled --output report.html
# Vergleichsmodus / PDF-Ausgabe:
python -m portfolio solution.json --mode comparison --pdf report.pdf
```

Die Konfigurationsdatei (`solution.json`) listet die Mitglieder auf (ARTs bei
einer Solution, Solutions bei einem Portfolio) und wird in der GUI erstellt bzw.
bearbeitet.

## Architektur

```
portfolio/
├── __main__.py        Dispatcher: GUI ohne Argumente, CLI mit Argumenten
├── cli.py             run_solution_report() + argparse-CLI
├── solution_config.py Solution-/Portfolio-Konfiguration (Mitglieder, Modus, Terminologie)
├── aggregator.py      Zusammenführung auf Datensatz-Ebene + Rendering (HTML/PDF)
└── summary.py         Management-Summary (Items, Done, WIP, CT-Perzentile)
```

Nutzt `build_reports` (Loader, Metriken, Export) wieder. Die Aggregation erfolgt
per **Record-Pooling** — die ART-Issues werden auf Datensatz-Ebene
zusammengeführt und die bestehenden Metriken laufen unverändert darüber (ein
gepoolter Median ≠ der Mittelwert der Mediane).

## Tests

```bash
python -m pytest tests/portfolio/
```
