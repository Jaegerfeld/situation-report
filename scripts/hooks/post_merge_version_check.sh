#!/bin/bash
# Runs as PostToolUse hook after git merge commands.
# Injects a reminder into Claude's context to ask about version bumping.

VERSION=$(grep '__version__' version.py | grep -o '"[^"]*"' | tr -d '"')
printf '{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"Git merge abgeschlossen. Aktuelle Version in version.py: %s. Frage den Benutzer jetzt: Soll die Versionsnummer erhöht werden? (MAJOR = Breaking Change, MINOR = neues Feature, PATCH = Bugfix, keine Änderung) Aktualisiere version.py nach der Antwort des Benutzers."}}' "$VERSION"
