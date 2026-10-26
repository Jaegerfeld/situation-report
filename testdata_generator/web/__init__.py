# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       26.10.2026
# Geändert:       26.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Browser-Oberfläche des Demo-Datenraums (Beta, Schnitt 3b, Entscheidung
#   E6 vom 26.10.2026: lokaler Server aus der Standardbibliothek + Browser
#   des Nutzers, kein Zusatzpaket). Drei Schritte wie im Prototyp —
#   Szenario, Umfang & Quellen, Erzeugen — auf der Dienstschicht
#   `testdata_generator.dataspace`.
#
#   server.py  HTTP-Server (nur 127.0.0.1, Zufallsport, Zufallsschlüssel
#              im Pfad), JSON-API, Erzeugung im Hintergrund-Thread
#   page.py    die Seite (HTML, CSS, JS ohne Bibliotheken)
#   texts.py   Oberflächentexte DE/EN
# =============================================================================
