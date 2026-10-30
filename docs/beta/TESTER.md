# SituationReport Beta — Hinweise für Tester

Danke fürs Ausprobieren. Dieses Paket ist ein **Vorschau-Stand** der Beta (Branch
`beta/ux-redesign`), kein Release. Es installiert nichts auf deinem Rechner: entpacken,
starten, am Ende den Ordner löschen.

## Entpacken und starten (Windows)

1. Rechtsklick auf die ZIP → Eigenschaften → unten „Zulassen" (Sicherheit) → OK.
   Ohne diesen Schritt blockiert Windows Defender die enthaltenen Dateien.
2. ZIP entpacken (nicht aus dem ZIP heraus starten).
3. **`DatenraumFenster.bat`** doppelklicken: die Oberfläche „Datenraum erzeugen" als
   Fenster mit drei Schritten. Das ist der Standardweg — er öffnet keinen Netzwerkport.
4. Alternativ `SituationReport.bat`: der Launcher mit allen Modulen, darin die Karte
   „Datenraum (Fenster)".
5. **Nur auf einem privaten Rechner:** `DatenraumBrowser.bat` zeigt dieselben Schritte im
   Browser. Dafür startet ein lokaler Server auf 127.0.0.1 — auf einem Firmenrechner hat die
   Sicherheitssoftware das beim ersten Test blockiert und gemeldet. Bitte dort nicht erneut
   versuchen, bevor die IT es freigegeben hat.

macOS/Linux: `DatenraumBrowser.sh` bzw. `.command` (erster Start richtet eine Python-Umgebung
ein, dafür ist einmal Internet nötig).

## Was du ausprobieren sollst (rund 15 Minuten)

1. **Die Minute:** Vorlage „Standard-Lage" lassen → Weiter → Weiter → Zielordner lassen →
   „Datenraum erzeugen". Erscheint die Ergebniskarte? Öffnen sich Portfolio-Report und
   jüngstes Delta?
2. **Eine andere Geschichte:** zurück zu Schritt 1, „Eskalation" wählen, erzeugen, dann im
   Vergleichswähler 3 → 4 öffnen. Siehst du, wie die Abhängigkeit AD-1 blockiert?
3. **Eine andere Struktur:** in Schritt 1 rechts eine Solution hinzufügen oder ARTs zählen.
   Passt „Was entsteht" mit?
4. **Ordnerdialog:** „Durchsuchen …" in Schritt 3. Öffnet sich ein Dialog?

Die ausführliche Anleitung: `docs/tutorials/demo-data-room.de.md` im Paket oder online
unter https://jaegerfeld.github.io/situation-report/ (Tutorials → Demo-Datenraum).

## Was wir wissen wollen

- Lief das Fenster? Wenn nicht: Welche Meldung stand da? Welches Betriebssystem, Firmenrechner?
- Falls du den Browser-Weg auf einem privaten Rechner probiert hast: Lief er?
- Was war unklar, was hast du gesucht und nicht gefunden?
- Wo hast du gezögert, bevor du geklickt hast?
- Wie lange hat die Erzeugung gedauert (steht auf der Ergebniskarte)?

Bitte Antworten als Text oder Screenshots an Robert. **Keine echten Projektdaten** in den
Generator laden — das Paket ist für erfundene Daten gedacht.

## Bekannte Grenzen dieses Stands

- Der Browser-Weg startet einen lokalen Server; Endgeräte-Sicherheitssoftware auf
  Firmenrechnern blockiert und meldet das (im ersten Test geschehen). Deshalb ist das Fenster
  der Standardweg — gleicher Funktionsumfang.
- Der Reiter „Ein ART" und das Umbenennen einzelner ARTs in der Oberfläche fehlen noch.
- Texte der Oberfläche: Deutsch und Englisch.
