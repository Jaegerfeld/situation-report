# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       25.04.2026
# Geändert:       30.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Zentrale Versionsnummer für das gesamte situation-report-Projekt.
#   Wird von build_reports, transform_data und dem Manual-Generator gelesen.
#   Versionierung nach SemVer: MAJOR.MINOR.PATCH
#     MAJOR: brechende Änderungen (neues Dateiformat, inkompatible Konfiguration)
#     MINOR: neue Features (neue Metrik, neues GUI-Element)
#     PATCH: Bugfixes
# =============================================================================

__version__ = "0.8.0"
