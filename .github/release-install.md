### Windows

1. `SituationReport-Windows.zip` herunterladen
   **Wichtig:** ZIP vor dem Entpacken freigeben: Rechtsklick → Eigenschaften → Sicherheit → **Zulassen** → OK
   (Sonst blockiert Windows Defender das eingebettete Python.)
2. ZIP entpacken → `SituationReport.bat` doppelklicken → Launcher GUI
   `BuildReports.bat` doppelklicken → Build Reports direkt
   `TransformData.bat` doppelklicken → Transform Data direkt
   `TestdataGenerator.bat` doppelklicken → Testdata Generator direkt
   `Helper.bat` doppelklicken → Helper (JSON Merger) direkt
3. Beim ersten Start: Windows SmartScreen → **Weitere Informationen** → **Trotzdem ausführen**

> Python (3.11) und Chrome (PDF-Export) sind im Paket enthalten.

### macOS (Apple Silicon)

1. `SituationReport-macOS-ARM.zip` herunterladen und entpacken
2. Rechtsklick auf `SituationReport.command` → *Öffnen* → *Öffnen* bestätigen (Gatekeeper, einmalig)
3. Beim **ersten Start**: einmalige Einrichtung (~1 Min, Internet erforderlich)

### Linux (x64)

1. `SituationReport-Linux.zip` herunterladen und entpacken
2. Voraussetzung: `python3` und `python3-tk` installiert
   (`sudo apt install python3-tk` auf Ubuntu/Debian)
3. Im entpackten Ordner: `./SituationReport.sh`
   Beim **ersten Start**: einmalige Einrichtung (~1 Min, Internet erforderlich)

---

### Datenformat

| Datei | Bedeutung |
|-------|-----------|
| `*_IssueTimes.xlsx` | Pflicht – Durchlaufzeiten pro Issue und Stage |
| `*_CFD.xlsx` | Optional – tägliche Stage-Zählungen für CFD |
| `*_Transitions.xlsx` | Optional – Transitionen für Process-Flow-Ansicht |
