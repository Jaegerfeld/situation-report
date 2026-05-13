# SituationReport – Übersicht für Einsteiger

**Version 0.99** | Erstellt: 03.05.2026 | Aktualisiert: 13.05.2026

Dieses Dokument fasst alle Bestandteile von SituationReport zusammen und erklärt sie
in einfacher Sprache. Technische Details aus den Original-Dokumentationen wurden
vereinfacht oder weggelassen.

> **📖 Hinweis zu Erklärungen:**
> Abschnitte, die mit diesem Symbol beginnen, sind zusätzliche Erklärungen
> für Nicht-Techniker und gehören nicht zur Original-Dokumentation.

---

## Was ist SituationReport?

SituationReport ist eine Werkzeugsammlung, die Daten aus dem Projektmanagement-Tool
**Jira** auswertet und daraus übersichtliche Berichte und Diagramme erstellt.
Die Software läuft lokal auf dem eigenen Computer — es werden keine Daten in
eine Cloud hochgeladen.

> **📖 Erklärung:**
> Jira ist ein weit verbreitetes Werkzeug, in dem Teams ihre Aufgaben (sogenannte
> „Issues" oder „Tickets") verwalten. Jede Aufgabe durchläuft dabei verschiedene
> Stationen, zum Beispiel: Backlog → In Bearbeitung → In Review → Fertig.
> SituationReport liest diese Daten aus und berechnet daraus, wie schnell und
> gleichmäßig ein Team arbeitet.

Das Projekt wurde als Experiment im Bereich KI-unterstützter Software-Entwicklung
erstellt. Mehr als 98 % des Codes wurden von Claude (Anthropic) geschrieben.

---

## Wie die Werkzeuge zusammenarbeiten

Der typische Ablauf sieht so aus:

```
[Jira-Export]  →  (Helper)  →  Transform Data  →  Build Reports
                   optional
                 (mehrere
                  Dateien)
```

1. **Jira-Export:** Aus Jira werden die Daten als Datei exportiert.
2. **Helper** *(optional)*: Falls mehrere Export-Dateien vorhanden sind,
   werden sie mit dem Helper-Werkzeug zu einer einzigen zusammengefügt.
3. **Transform Data:** Die Rohdaten werden aufbereitet und in strukturierte
   Tabellen umgewandelt.
4. **Build Reports:** Aus den Tabellen werden Diagramme und Berichte erstellt.

> **📖 Erklärung:**
> Man kann sich den Ablauf vorstellen wie einen Trichter: Zunächst kommen die
> Rohdaten aus Jira (unstrukturiert, groß), dann werden sie sortiert und
> zusammengefasst (Transform Data), und am Ende erhält man fertige Berichte
> mit Grafiken (Build Reports).

Für den Alltag gibt es außerdem zwei Hilfswerkzeuge:

- **Testdata Generator:** Erzeugt künstliche Testdaten, um die Software
  auszuprobieren, ohne echte Projektdaten zu benötigen.
- **Launcher:** Das Startfenster, von dem aus alle Werkzeuge geöffnet werden.

---

## Installation und Start

### Download

Alle verfügbaren Versionen sind auf der
[GitHub-Releases-Seite](https://github.com/Jaegerfeld/situation-report/releases)
verfügbar. Es gibt stabile Versionen (z. B. `v0.9.0`) und Entwicklungs-Builds
(`dev-latest`). Für den normalen Einsatz empfiehlt sich immer die **neueste
stabile Version**.

> **📖 Erklärung:**
> Ein „Release" ist eine veröffentlichte, getestete Version der Software.
> „Dev Build" bedeutet: der aktuellste Entwicklungsstand, der noch nicht
> vollständig getestet wurde und daher neue, möglicherweise fehlerhafte
> Funktionen enthalten kann.

### Windows

1. `SituationReport-Windows.zip` herunterladen
2. Zip-Datei entpacken (Rechtsklick → *Alle extrahieren*)
3. `SituationReport.bat` doppelklicken → das Startfenster öffnet sich

> **📖 Erklärung:**
> Beim ersten Start erscheint möglicherweise eine Sicherheitsmeldung von
> Windows SmartScreen. Das ist normal, weil die Software nicht von Microsoft
> zertifiziert ist. Auf **Weitere Informationen → Trotzdem ausführen**
> klicken. Das Windows-Paket enthält Python und Chrome bereits eingebaut —
> es muss nichts separat installiert werden.

### macOS

1. `SituationReport-macOS-ARM.zip` herunterladen und entpacken
2. *Rechtsklick* auf `SituationReport.command` → *Öffnen* → im Dialog
   erneut *Öffnen* bestätigen (einmalig nötig)
3. Beim ersten Start wird automatisch eine Python-Umgebung eingerichtet
   (~1 Minute, Internetverbindung erforderlich)

### Linux

1. `SituationReport-Linux.zip` herunterladen und entpacken
2. Im Terminal: `./SituationReport.sh`
3. Beim ersten Start wird automatisch eine Python-Umgebung eingerichtet
   (~1 Minute, Internetverbindung erforderlich)

---

## Der Launcher: Das Startfenster

Der Launcher ist das zentrale Startfenster von SituationReport. Er zeigt alle
verfügbaren und geplanten Werkzeuge als Kacheln an.

```
┌──────────────────────────────────────────┐
│  SituationReport  v0.9.0  BETA     ?  🌐 │
├──────────────────────────────────────────┤
│  ┌──────────────┐ ┌──────────────┐       │
│  │  🔄  BETA    │ │  📊  BETA    │       │
│  │Transform Data│ │ Build Reports│       │
│  │  [Starten]   │ │  [Starten]   │       │
│  └──────────────┘ └──────────────┘       │
│  ┌──────────────┐ ┌──────────────┐       │
│  │  📥          │ │  🎲          │       │
│  │  Get Data    │ │   Simulate   │       │
│  │(bald verf.)  │ │(bald verf.)  │       │
│  └──────────────┘ └──────────────┘       │
│  ┌──────────────┐ ┌──────────────┐       │
│  │  🧪  ALPHA   │ │  🔧  ALPHA   │       │
│  │Testdata Gen. │ │   Helper     │       │
│  │  [Starten]   │ │  [Starten]   │       │
│  └──────────────┘ └──────────────┘       │
└──────────────────────────────────────────┘
```

**Was die Kacheln zeigen:**

| Kachel | Status | Bedeutung |
|--------|--------|-----------|
| Transform Data | BETA | Verfügbar, stabil |
| Build Reports | BETA | Verfügbar, stabil |
| Get Data | *(bald verfügbar)* | Noch nicht fertig |
| Simulate | *(bald verfügbar)* | Noch nicht fertig |
| Testdata Generator | ALPHA | Verfügbar, experimentell |
| Helper | ALPHA | Verfügbar, experimentell |

> **📖 Erklärung zu den Reifegraden:**
> - **BETA** (orange): Das Werkzeug ist fertig und für den produktiven Einsatz
>   geeignet. Kleine Fehler können noch vorkommen.
> - **ALPHA** (rot): Das Werkzeug funktioniert grundsätzlich, ist aber noch
>   neu und kann sich noch verändern.
> - **Kein Badge / „bald verfügbar"**: Das Werkzeug ist noch in Planung und
>   noch nicht nutzbar.

Ein Klick auf **Starten** öffnet das gewählte Werkzeug in einem eigenen
Fenster. Der Launcher bleibt dabei offen.

**Weitere Funktionen des Launchers:**

- **? (Fragezeichen):** Öffnet das Benutzerhandbuch im Browser
- **🌐 (Flagge):** Wechselt die Sprache (Deutsch → Englisch → Rumänisch →
  Portugiesisch → Französisch → Deutsch …)
- **Gelbes Update-Banner:** Erscheint automatisch, wenn eine neuere Version
  auf GitHub verfügbar ist, mit einem Link zum Herunterladen

---

## Transform Data: Daten aufbereiten

Transform Data liest einen Jira-Export und eine Workflow-Beschreibung und
erzeugt daraus drei strukturierte Tabellen (Excel-Dateien), die von
Build Reports weiterverarbeitet werden.

> **📖 Erklärung:**
> Jira speichert alle Informationen über eine Aufgabe (wann sie erstellt
> wurde, durch welche Stationen sie gegangen ist, wie lange sie wo war)
> intern als Liste von Ereignissen. Transform Data liest diese Ereignisliste
> und berechnet daraus: Wie viel Zeit hat die Aufgabe in jeder Station
> verbracht? Das Ergebnis sind saubere Tabellen, die man sich direkt in
> Excel anschauen oder mit Build Reports auswerten kann.

### Was wird benötigt?

1. **Jira-JSON-Export:** Eine Datei mit den Aufgabendaten aus Jira
2. **Workflow-Datei:** Eine einfache Textdatei, die beschreibt, welche
   Stationen (Status) es in diesem Projekt gibt

> **📖 Erklärung zur Workflow-Datei:**
> Die Workflow-Datei ist notwendig, weil Jira-Projekte sehr unterschiedlich
> aufgebaut sein können. Ein Projekt hat vielleicht die Stationen
> „Backlog → In Analyse → In Entwicklung → Fertig", ein anderes ganz
> andere Namen. Die Workflow-Datei sagt dem Programm, wie die Stationen
> in diesem konkreten Projekt heißen und in welcher Reihenfolge sie kommen.
> Außerdem wird darin festgelegt, welche Station den Start der aktiven
> Arbeit markiert (`<First>`) und welche Station das Ende markiert
> (`<Closed>`).

Beispiel einer Workflow-Datei:
```
Funnel
Analysis:In Analysis
Implementation:In Progress
Done:Canceled
<First>Analysis
<Closed>Done
```

### Was wird erzeugt?

| Datei | Inhalt |
|-------|--------|
| `*_IssueTimes.xlsx` | Eine Zeile pro Aufgabe mit der Zeit (in Minuten) in jeder Station |
| `*_Transitions.xlsx` | Eine Zeile pro Statuswechsel pro Aufgabe, chronologisch |
| `*_CFD.xlsx` | Tägliche Eintrittszählungen je Station (Grundlage für das CFD-Diagramm) |

> **📖 Erklärung zu den Ausgabedateien:**
> - **IssueTimes** ist die wichtigste Datei. Sie zeigt für jede Aufgabe
>   genau, wann sie erstellt wurde, wann die Arbeit daran begann, wann
>   sie abgeschlossen wurde — und wie viel Zeit sie in jeder Station
>   verbracht hat.
> - **Transitions** ist das vollständige Protokoll aller Statuswechsel.
>   Nützlich, wenn man genau nachvollziehen möchte, wann was passiert ist.
> - **CFD** enthält die Daten für das Cumulative Flow Diagram — eine
>   spezielle Art von Diagramm, die zeigt, wie viele Aufgaben im Laufe
>   der Zeit durch das System geflossen sind.

### Besonderheiten

- **Nicht gemappte Status:** Falls ein Jira-Status in der Workflow-Datei
  nicht vorkommt, wird eine Warnung ausgegeben. Die Zeit in diesem Status
  wird der letzten bekannten Station zugerechnet.
- **Übersprungene Stationen:** Falls eine Aufgabe eine Station übersprungen
  hat, erkennt Transform Data das automatisch und behandelt es korrekt.

> **📖 Erklärung:**
> In der Praxis passiert es manchmal, dass eine Aufgabe eine Station
> übersprungen hat (zum Beispiel direkt von „In Analyse" nach „Fertig"
> gewechselt ist, ohne „In Entwicklung" zu durchlaufen). Transform Data
> erkennt solche Fälle und berechnet trotzdem sinnvolle Werte.

---

## Build Reports: Berichte erstellen

Build Reports liest die von Transform Data erzeugten Tabellen und erstellt
daraus interaktive Diagramme und Berichte. Die Diagramme können im Browser
angezeigt oder als PDF exportiert werden.

> **📖 Erklärung:**
> Build Reports ist das „Auswertungs-Werkzeug". Es beantwortet Fragen wie:
> Wie lange dauert es im Durchschnitt, bis eine Aufgabe fertig ist?
> Wie viele Aufgaben werden pro Woche abgeschlossen? Wie viele Aufgaben
> sind gerade gleichzeitig in Bearbeitung? Die Antworten werden als
> Diagramme dargestellt.

### Filter und Einstellungen

Bevor die Berichte erstellt werden, kann man die Daten einschränken:

| Einstellung | Bedeutung |
|-------------|-----------|
| Von / Bis | Nur Aufgaben berücksichtigen, die in diesem Zeitraum abgeschlossen wurden |
| Projekte | Nur bestimmte Jira-Projekte auswerten |
| Issuetypen | Nur bestimmte Aufgabentypen (z. B. nur „Feature", nicht „Bug") |
| Status-Ausschluss | Aufgaben mit bestimmten Status komplett ignorieren (z. B. „Canceled") |
| Zero-Day-Ausschluss | Aufgaben ignorieren, die zu schnell durch alle Stationen gingen (vermutlich Testaufgaben oder Fehler) |

> **📖 Erklärung zu Zero-Day-Issues:**
> Manchmal gibt es Aufgaben, die innerhalb von Sekunden durch alle Stationen
> bewegt wurden — zum Beispiel weil jemand eine Aufgabe nur zu Testzwecken
> erstellt und sofort wieder geschlossen hat. Diese „Null-Tage-Aufgaben"
> würden die Statistiken verzerren und können daher herausgefiltert werden.

Konfigurationen können als **Template** gespeichert und später wieder
geladen werden — nützlich, wenn man regelmäßig immer denselben Bericht
erstellt.

### Die Metriken (Diagramme)

#### Flow Time / Cycle Time — Wie lange dauert eine Aufgabe?

> **📖 Erklärung:**
> Diese Metrik beantwortet die Frage: „Wie lange dauert es von dem Moment,
> wo wir anfangen, an einer Aufgabe zu arbeiten, bis sie fertig ist?"
> Das ist eine der wichtigsten Kennzahlen für ein Team — sie zeigt, ob der
> Prozess schnell oder langsam ist und ob er vorhersagbar ist.

**Zwei Diagramme:**

- **Boxplot:** Zeigt die Verteilung aller Durchlaufzeiten. Wie breit die Box
  ist, zeigt, wie unterschiedlich (unvorhersagbar) die Zeiten sind.
  Im Kopf stehen Kennzahlen: Minimum, Maximum, Durchschnitt, Median,
  und der Anteil der Aufgaben, die in 90 Tagen oder weniger abgeschlossen
  wurden.

  > **📖 Erklärung zum Boxplot:**
  > Ein Boxplot ist eine kompakte Darstellung einer Verteilung. Die Box
  > umschließt die mittleren 50 % der Werte. Die Linie in der Mitte ist
  > der Median (der mittlere Wert). Die „Antennen" zeigen den Bereich,
  > in dem die meisten Werte liegen. Je schmaler die Box und je kürzer
  > die Antennen, desto vorhersagbarer ist der Prozess.

- **Scatterplot:** Zeigt jeden einzelnen Abschluss als Punkt auf einer
  Zeitachse. Farbkodierung: rote Punkte = besonders langsam, orange =
  überdurchschnittlich langsam, blau = normal.
  Eine Trendlinie (blau) zeigt, ob die Zeiten über die Zeit besser oder
  schlechter werden.

  > **📖 Erklärung zu den Referenzlinien:**
  > Im Scatterplot gibt es drei horizontale Linien:
  > - **Median (rot):** 50 % der Aufgaben waren schneller, 50 % langsamer.
  > - **P85 (hellgrün):** 85 % der Aufgaben waren schneller als dieser Wert.
  > - **P95 (cyan):** 95 % der Aufgaben waren schneller.
  > Diese Linien helfen bei der Vorhersage: „Wenn wir heute mit einer
  > Aufgabe anfangen, wann wird sie mit 85 % Wahrscheinlichkeit fertig sein?"

#### Flow Velocity / Throughput — Wie viele Aufgaben werden fertig?

> **📖 Erklärung:**
> Diese Metrik beantwortet die Frage: „Wie viele Aufgaben schließt das Team
> pro Woche oder Monat ab?" Ein stabiler, hoher Durchsatz ist ein Zeichen
> für einen gut laufenden Prozess.

**Drei Diagramme:**

- **Tagesfrequenz:** Wie viele Aufgaben werden typischerweise an einem
  einzigen Tag abgeschlossen? (Die meisten Teams schließen mehrere Aufgaben
  an manchen Tagen ab, an anderen gar keine.)
- **Wochenverlauf:** Linienchart mit den wöchentlichen Abschlüssen —
  zeigt Trends und Schwankungen über Zeit.
- **PI-Verlauf:** Balkendiagramm der Abschlüsse pro Planning Interval
  (SAFe-Begriff für einen größeren Planungszyklus).

  > **📖 Erklärung zu PI:**
  > In SAFe (Scaled Agile Framework) werden Quartale in „Program Increments"
  > (PIs) eingeteilt — typischerweise jeweils 8–12 Wochen mit mehreren
  > Sprints. Der PI-Verlauf zeigt, wie produktiv das Team in jedem PI war.

#### Flow Load / WIP — Wie viele Aufgaben sind gerade in Bearbeitung?

> **📖 Erklärung:**
> WIP steht für „Work in Progress" — Aufgaben, die begonnen, aber noch
> nicht fertig sind. Zu viele gleichzeitig in Bearbeitung befindliche
> Aufgaben verlangsamen den Prozess (jeder ist beschäftigt, aber nichts
> kommt voran). Diese Metrik zeigt den aktuellen Stand.

**Ein Diagramm:** Gruppierter Boxplot aller laufenden Aufgaben, aufgeteilt
nach Station. Das Alter jeder Aufgabe (Tage seit Bearbeitungsbeginn) ist
sichtbar. Referenzlinien aus den historischen Abschlussdaten geben einen
Kontext: Aufgaben, die länger als der Median oder das 85. Perzentil laufen,
sind möglicherweise blockiert.

> **📖 Erklärung:**
> Der Flow Load zeigt quasi eine „Momentaufnahme" des Systems: Welche
> Aufgaben stecken gerade wo? Und wie lange sind sie schon dort? Aufgaben,
> die sehr lang in einer Station bleiben, können auf ein Problem hinweisen —
> zum Beispiel einen Engpass oder eine Blockade.

#### Cumulative Flow Diagram (CFD) — Wie fließt die Arbeit?

> **📖 Erklärung:**
> Das CFD ist eine der aussagekräftigsten Visualisierungen im agilen
> Projektmanagement. Es zeigt für jeden Tag, wie viele Aufgaben insgesamt
> in jede Station eingetreten sind. An der Form des Diagramms kann man
> ablesen: Läuft das System gleichmäßig? Stauen sich Aufgaben in einer
> bestimmten Station? Wird genug abgeschlossen?

**Ein Diagramm:** Gestapeltes Flächendiagramm. Die Breite zwischen der
oberen und unteren Trendlinie zeigt die durchschnittliche Durchlaufzeit
(je breiter, desto länger). Eine schrumpfende Breite bedeutet: das Team
wird schneller. Eine wachsende Breite bedeutet: der Prozess verlangsamt sich.

#### Flow Distribution — Was arbeitet das Team?

> **📖 Erklärung:**
> Diese Metrik zeigt die Zusammensetzung der Arbeit. Wie viel Prozent sind
> neue Features? Wie viel sind Bugs? Welche Station beschäftigt das Team
> am meisten? Wo verbringen Aufgaben die meiste Zeit?

**Drei Diagramme:**

- **By Issue Type:** Kreisdiagramm — welche Anteile haben die verschiedenen
  Aufgabentypen (Feature, Bug, Enabler …)?
- **Stage Prominence:** Kreisdiagramm — in welcher Station verbringen
  Aufgaben die meiste Zeit? Das zeigt, wo der eigentliche Schwerpunkt
  der Arbeit liegt.
- **Avg Cycle Time by Type:** Balkendiagramm — dauern Features länger als
  Bugs? Diese Ansicht zeigt die durchschnittliche Durchlaufzeit pro
  Aufgabentyp.

### Terminologie

Build Reports unterstützt zwei verschiedene Bezeichnungssysteme:

| SAFe-Bezeichnung | Allgemeine Bezeichnung |
|-----------------|----------------------|
| Flow Time | Cycle Time |
| Flow Velocity | Throughput |
| Flow Load | WIP (Work in Progress) |

> **📖 Erklärung:**
> Je nach Kontext des Teams oder Unternehmens werden diese Konzepte
> unterschiedlich bezeichnet. In SAFe (einem verbreiteten agilen
> Framework) heißt es „Flow Time", in anderen Kontexten „Cycle Time".
> Gemeint ist dasselbe. Die Umschaltung beeinflusst nur die Beschriftungen
> in den Diagrammen.

### Export

- **Browser:** Alle Diagramme werden in einer HTML-Datei im Browser geöffnet.
  Dort sind sie interaktiv (Zoom, Tooltip beim Hovern, Legende ein-/ausblenden).
- **PDF:** Alle Diagramme werden zu einem mehrseitigen PDF zusammengefasst.
  Gleichzeitig wird automatisch eine Excel-Datei mit allen ausgewerteten
  Aufgaben erstellt.

---

## Helper: Dateien zusammenführen

Das Helper-Modul enthält aktuell ein Werkzeug: den **JSON Merger**.

> **📖 Erklärung — das Problem:**
> Jira kann bei einem Export maximal 1.000 Aufgaben auf einmal ausgeben.
> Hat ein Projekt mehr als 1.000 Aufgaben, muss man mehrere Exporte
> durchführen — und erhält dann mehrere Dateien. Transform Data erwartet
> aber eine einzige Datei. Der Helper löst dieses Problem: Er nimmt
> alle Export-Dateien und fügt sie zu einer einzigen zusammen.

### Was der JSON Merger macht

1. Alle angegebenen Jira-JSON-Dateien werden eingelesen
2. Die Aufgaben aus allen Dateien werden kombiniert
3. Doppelt vorhandene Aufgaben (nach Aufgaben-ID) werden automatisch
   entfernt (Deduplizierung)
4. Das Ergebnis ist eine einzige Datei, die direkt von Transform Data
   verarbeitet werden kann

> **📖 Erklärung zur Deduplizierung:**
> Wenn man mehrere Jira-Exporte mit überlappenden Zeiträumen durchführt,
> kann es vorkommen, dass dieselbe Aufgabe in mehreren Dateien vorkommt.
> Der Helper erkennt das und entfernt die Duplikate automatisch. Im Log
> wird für jedes erkannte Duplikat eine Meldung angezeigt.

### Benutzeroberfläche

```
Eingabedateien
┌─────────────────────────────────┐
│ /pfad/zu/export_0.json          │
│ /pfad/zu/export_1000.json       │
│ /pfad/zu/export_2000.json       │
└─────────────────────────────────┘
[Hinzufügen…]  [Entfernen]

Ausgabedatei (JSON)
[/pfad/zu/merged.json    ] [Suchen…]

☑ Duplikate entfernen

         [Zusammenführen]
```

---

## Testdata Generator: Testdaten erstellen

Der Testdata Generator erzeugt künstliche Jira-Daten, die dem echten
Jira-Format entsprechen. Die erzeugten Dateien können direkt mit
Transform Data und Build Reports verarbeitet werden.

> **📖 Erklärung — wofür ist das nützlich?**
> Man kann SituationReport ausprobieren, ohne echte Projektdaten zu
> benötigen. Auch für Schulungen, Demonstrationen oder das Testen neuer
> Funktionen ist der Testdata Generator nützlich. Die generierten Daten
> sehen realistisch aus: Es gibt Aufgaben, die schnell fertig wurden,
> andere die sehr lange dauerten, manche die noch offen sind — genauso
> wie in einem echten Projekt.

### Konfigurierbare Parameter

| Parameter | Bedeutung |
|-----------|-----------|
| Workflow-Datei | Welche Stationen sollen die Aufgaben durchlaufen? |
| Projekt-Key | Wie sollen die Aufgaben-IDs heißen (z. B. „DEMO-1", „DEMO-2"…)? |
| Anzahl Aufgaben | Wie viele Aufgaben sollen erzeugt werden? |
| Datum-Bereich | Zwischen welchen Daten sollen die Aufgaben entstanden sein? |
| Aufgabentypen | Welcher Anteil soll Feature, Bug, Enabler usw. sein? |
| Abschlussrate | Welcher Prozentsatz der Aufgaben soll bereits abgeschlossen sein? |
| Rückschritt-Wahrscheinlichkeit | Wie oft soll eine Aufgabe zurück zu einer früheren Station springen? |
| Seed | Eine Zahl, mit der immer exakt dieselben Daten erzeugt werden (für reproduzierbare Tests) |
| Mittlere Cycle-Time | Durchschnittliche Durchlaufzeit in Tagen (lognormalverteilt) |
| Standardabweichung | Streuung der Cycle-Time |
| Flow-Muster | Welches Antipattern soll simuliert werden? (Triangle, Flat Triangle, Cluster, Batch) |
| PI-Zyklus-Länge | Länge eines Program Increments in Wochen (für Cluster/Batch-Muster) |

> **📖 Erklärung zum Seed:**
> Normalerweise sind die erzeugten Daten zufällig. Mit einem Seed
> (einer beliebigen Zahl, z. B. „42") wird die Zufälligkeit festgelegt:
> Wer denselben Seed verwendet, erhält immer exakt dieselben Daten.
> Das ist nützlich, wenn man sicherstellen möchte, dass ein Test immer
> mit den gleichen Daten läuft.

### Flow-Antipattern-Muster (neu in v0.99)

Der Testdata Generator kann typische Probleme aus dem agilen Prozess-Monitoring simulieren:

| Muster | Was es zeigt | Wofür nützlich |
|--------|-------------|----------------|
| **Triangle** | Cycle-Time steigt kontinuierlich über die Zeit — das Team wird immer langsamer | Erkennen von schleichender Prozessverschlechterung |
| **Flat Triangle** | Wie Triangle, aber der Anstieg verflacht am Ende | Zeigt einen Prozess, der sich stabilisiert aber auf hohem Niveau |
| **Cluster of Dots** | Viele Lieferungen häufen sich kurz vor dem PI-Ende — in normaler Zeit | Zeigt Deadline-getriebenes Verhalten, Batching am PI-Ende |
| **Batch Transfers** | Wie Cluster, aber mit sehr unterschiedlicher Cycle-Time | Zeigt, dass kurze und sehr lange Aufgaben gemeinsam am PI-Ende ausgeliefert werden |

> **📖 Erklärung zu Flow-Antipatterns:**
> Daniel Vacanti und Prateek Singh haben typische Muster beschrieben, die
> auf Probleme im agilen Prozess hinweisen. Das Triangle-Muster bedeutet:
> Mit der Zeit dauert jede Aufgabe länger — ein Zeichen, dass der Prozess
> überlastet wird. Das Cluster-Muster bedeutet: Das Team liefert nicht
> gleichmäßig, sondern sammelt Aufgaben und schiebt sie kurz vor dem
> PI-Ende durch — was zu unnötigem Stress und schlechterer Qualität führt.

---

## Geplante Module (noch nicht verfügbar)

### Get Data — Direkter Jira-Abruf

Dieses Modul ist noch in Planung. Es soll Daten direkt über die Jira-REST-API
abrufen — ohne manuellen Export.

> **📖 Erklärung:**
> Aktuell muss man Daten manuell aus Jira exportieren (als Datei
> herunterladen). Wenn Get Data fertig ist, kann SituationReport die
> Daten selbst aus Jira laden — man gibt nur ein, welches Projekt man
> auswerten möchte, und das Programm holt sich die Daten automatisch.

**Workaround bis zur Fertigstellung:** Jira-Daten manuell exportieren,
bei Bedarf mit dem Helper zusammenführen, dann mit Transform Data
verarbeiten.

### Simulate — Prognosen und Vorhersagen

Dieses Modul ist noch in Planung. Es soll auf Basis historischer Daten
Vorhersagen ermöglichen — zum Beispiel: „Wann werden wir mit dieser
Menge an Aufgaben voraussichtlich fertig sein?"

> **📖 Erklärung:**
> Mit historischen Daten (wie lange hat das Team bisher gebraucht?) kann
> man mit statistischen Methoden Vorhersagen treffen. Zum Beispiel:
> „Wir haben noch 20 Aufgaben offen. Wenn wir historisch 3 pro Woche
> abschließen, sind wir in 7 Wochen fertig — mit 85 % Wahrscheinlichkeit
> sogar in 9 Wochen." Diese Vorhersagen sind ehrlicher als klassische
> Schätzungen, weil sie auf echten Messdaten beruhen.

---

## Versionshistorie (Zusammenfassung)

| Version | Datum | Wichtigste Neuerungen |
|---------|-------|----------------------|
| **0.99** | 13.05.2026 | Testdata Generator: Flow-Antipattern (Triangle, Flat Triangle, Cluster, Batch), lognormale Cycle-Time |
| 0.9.8 | 09.05.2026 | Pixel-Flaggen-Buttons in allen GUIs |
| 0.9.0 | 03.05.2026 | Helper-Modul (JSON Merger) |
| 0.8.5 | 02.05.2026 | Testdata Generator, BETA-Badge für stabile Module |
| 0.8.4 | 30.04.2026 | Handbücher auf Rumänisch, Portugiesisch, Französisch |
| 0.8.3 | 30.04.2026 | Scrollbares Formular in Build Reports |
| 0.8.1 | 30.04.2026 | Automatische Update-Benachrichtigung im Launcher |
| 0.8.0 | 30.04.2026 | Launcher-GUI, Doppelklick-Startskripte |
| 0.7.0 | 30.04.2026 | Process Flow Metrik, CI/CD Release-Workflow |
| 0.5.0 | 26.04.2026 | Process Flow Diagramm |
| 0.4.0 | 26.04.2026 | Zweisprachige GUIs (DE/EN) |
| 0.2.0 | 25.04.2026 | Erste offizielle SemVer-Version |

> **📖 Erklärung zur Versionsnummer:**
> SituationReport verwendet semantische Versionierung: `MAJOR.MINOR.PATCH`.
> - **PATCH** (letzte Zahl): kleiner Bugfix
> - **MINOR** (mittlere Zahl): neue Funktion, rückwärtskompatibel
> - **MAJOR** (erste Zahl): grundlegende Änderung, Kompatibilität nicht garantiert
> Version 1.0.0 wird vergeben, wenn das Projekt als vollständig stabil gilt.

---

## Technische Hinweise

> **📖 Erklärung:**
> Dieser Abschnitt richtet sich an Personen mit technischem Hintergrund,
> die mehr über den Aufbau der Software wissen möchten.

SituationReport ist als **Monorepo** aufgebaut: Alle Module befinden sich
in einem einzigen Code-Repository, können aber unabhängig voneinander
verwendet werden.

```
situation-report/
├── launcher/           → Startfenster
├── transform_data/     → Datenaufbereitung
├── build_reports/      → Berichts-Generierung
├── testdata_generator/ → Testdaten-Erzeugung
├── helper/             → Hilfswerkzeuge
├── get_data/           → (geplant)
└── simulate/           → (geplant)
```

- **Sprache:** Python
- **GUI-Framework:** tkinter
- **Diagramme:** Plotly
- **Tests:** pytest (ca. 650+ Tests, Stand v0.99)
- **CI/CD:** GitHub Actions (automatische Builds für Windows, macOS, Linux)
- **Lizenz:** BSD-3-Clause

---

*Dieses Dokument wurde automatisch aus den Quell-Dokumentationen des
Projekts erstellt und für Nicht-Techniker aufbereitet (03.05.2026).*
