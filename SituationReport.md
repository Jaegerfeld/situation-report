# SituationReport

Toolsuite für das Lagebild auf Portfolio- und Solution-Ebene: Flow-Metriken aus Jira, Governance-Register, Vorbereitung der Value-Stream-Conference, Prognosen und KI-Entwürfe — lokal auf dem eigenen Rechner.

**Repository:** https://github.com/Jaegerfeld/situation-report
**Dokumentation (deutsch):** https://jaegerfeld.github.io/situation-report/de/
**Denkschriften:** https://jaegerfeld.github.io/situation-report/de/denkschriften/

---

## Module

Die gepflegte Modulübersicht mit Reifegrad steht in der Dokumentation:
**[Modul-Übersicht](https://jaegerfeld.github.io/situation-report/de/modules/)**

Sie wird an einer Stelle gepflegt und von README und Startseiten übernommen —
diese Seite führt bewusst keine eigene Kopie, damit nichts auseinanderläuft.

## Einstieg

```bash
git clone https://github.com/Jaegerfeld/situation-report.git
cd situation-report
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

Danach startet `python -m launcher` das zentrale Fenster, aus dem sich alle
Module öffnen lassen (Windows: `SituationReport.bat`, macOS:
`SituationReport.command`, Linux: `./SituationReport.sh`).

## Technologie

- **Sprache:** Python >= 3.11
- **Oberflächen:** tkinter (GUI) und CLI je Modul
- **Diagramme/Export:** Plotly, kaleido, ReportLab
- **Datenquellen:** Jira (REST-Abruf oder geprüfter Export) sowie steckbare
  externe Quellen für SLO-, DORA- und Qualitätswerte
- **KI:** optional und austauschbar — lokal (Ollama) oder extern (Claude-API)
- **Lizenz:** BSD-3-Clause
