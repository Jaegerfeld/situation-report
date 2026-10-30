# SituationReport Beta — Hinweise für Tester

Danke fürs Ausprobieren. Dieses Paket ist ein **Vorschau-Stand** der Beta (Branch
`beta/ux-redesign`), kein Release. Es installiert nichts auf deinem Rechner: entpacken,
starten, am Ende den Ordner löschen.

## Entpacken und starten (Windows)

1. Rechtsklick auf die ZIP → Eigenschaften → unten „Zulassen" (Sicherheit) → OK.
   Ohne diesen Schritt blockiert Windows Defender die enthaltenen Dateien.
2. ZIP entpacken (nicht aus dem ZIP heraus starten).
3. **`DatenraumBrowser.bat`** doppelklicken: Es öffnet sich dein Browser mit der neuen
   Oberfläche „Datenraum erzeugen". Das Fenster dahinter bleibt offen — es ist der lokale
   Server; schließen beendet die Oberfläche.
4. Alternativ `SituationReport.bat`: der Launcher mit allen Modulen, darin die Karte
   „Datenraum (Browser)".
5. **Wenn der Browser die Seite nicht lädt** (403, „nicht erreichbar", Proxy-Hinweis):
   `DatenraumFenster.bat` doppelklicken — dieselben drei Schritte als Fenster, ohne Server.
   Im Launcher heißt die Karte „Datenraum (Fenster)". Bitte trotzdem notieren, welche
   Meldung der Browser zeigte.

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

- Lief die Oberfläche im Browser? Wenn nicht: Welche Meldung stand da (403, „Seite nicht
  erreichbar", Proxy-Hinweis)? Welcher Browser, welches Betriebssystem, Firmenrechner?
- Was war unklar, was hast du gesucht und nicht gefunden?
- Wo hast du gezögert, bevor du geklickt hast?
- Wie lange hat die Erzeugung gedauert (steht auf der Ergebniskarte)?

Bitte Antworten als Text oder Screenshots an Robert. **Keine echten Projektdaten** in den
Generator laden — das Paket ist für erfundene Daten gedacht.

## Bekannte Grenzen dieses Stands

- Firmenrechner können lokale Server (127.0.0.1) über Proxy oder Richtlinien blockieren.
  Dann `DatenraumFenster.bat` nehmen — gleicher Funktionsumfang, nur als Fenster.
- Der Reiter „Ein ART" und das Umbenennen einzelner ARTs in der Oberfläche fehlen noch.
- Texte der Oberfläche: Deutsch und Englisch.
