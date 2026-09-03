# Ollama auf Windows 11 installieren

**Zielgruppe:** alle, die die KI-Narration lokal betreiben wollen.
**Dauer:** rund 15 Minuten plus Modell-Download. **Voraussetzungen:**
Windows 11 und Plattenplatz für das Modell — keine Admin-Rechte, kein
Konto, kein API-Schlüssel. **Am Ende:** `--narrate` entwirft Narrationen
auf deinem Rechner, und keine Daten verlassen ihn.

Diese Anleitung gibt es auch als separate PDF:
[DE](../ollama_Installationsanleitung_DE.pdf) /
[EN](../ollama_Installationsanleitung_EN.pdf).

---

## 1. Warum lokal?

Ollama betreibt Sprachmodelle vollständig auf dem eigenen Rechner. Für
die KI-Narration des Lagebilds heißt das: Das Delta-Briefing verlässt
nie das System, und es braucht keine Konzern-Freigabe für externe
Dienste. Dieser Weg erscheint als `deployment_class "local"` in der
KI-Kennzeichnung und im Betreiber-Nachweis (`llm_audit.jsonl`).

## 2. Voraussetzungen

- Windows 11, 64-bit; keine Administratorrechte nötig (Ollama
  installiert sich ins Benutzerprofil).
- Plattenplatz: ~4 GB für Ollama selbst plus Modell — `mistral-nemo`
  lädt rund 7 GB, `mistral` rund 4 GB.
- Arbeitsspeicher: 16 GB empfohlen für `mistral-nemo` (12B); mit 8 GB
  das kleinere `mistral` (7B) wählen.
- Ohne Grafikkarte läuft alles auf der CPU — eine Narration dauert dann
  bis zu einer Minute. Eine NVIDIA- oder AMD-GPU wird automatisch
  genutzt.

## 3. Installieren

1. [ollama.com/download/windows](https://ollama.com/download/windows)
   öffnen und `OllamaSetup.exe` herunterladen.
2. Die Datei per Doppelklick starten und dem Assistenten folgen — mehr
   Auswahl gibt es nicht.
3. Danach läuft Ollama im Hintergrund; im Infobereich der Taskleiste
   erscheint das Lama-Symbol, und nach einem Neustart startet Ollama
   automatisch mit.

Installation prüfen (Windows-Taste, `powershell` tippen):

```
ollama --version
```

## 4. Modell laden

Das Standardmodell der Narration ist `mistral-nemo`:

```
ollama pull mistral-nemo
```

Auf einem 8-GB-Rechner stattdessen `ollama pull mistral`. Kurztest — die
erste Antwort dauert am längsten, weil das Modell in den Speicher
geladen wird (Chat beenden mit `/bye`):

```
ollama run mistral-nemo "Antworte mit einem Satz: Was ist ein Lagebild?"
```

## 5. Verkabelungs-Check mit SituationReport

```
python -m llm providers
python -m llm test
```

`providers` listet die entdeckten KI-Anbieter (`ollama`, `claude`,
`mock`); `test` macht eine gekennzeichnete Probe-Narration über Ollama —
erscheint ein Entwurf mit KI-Banner, ist alles verkabelt.

## 6. Benutzen

CLI — `--narrate` ergänzt das Delta-Briefing um den gekennzeichneten
Abschnitt **„Narration (Entwurf)“**; der Zahlen-Wächter verwirft jede
erfundene Zahl, und der Nachweis landet in `llm_audit.jsonl` neben der
Ausgabe:

```
python -m portfolio --delta prev.json now.json --narrate --output delta.html --browser
```

GUI — im Solutions-&-Portfolios-Fenster die Checkbox **„KI-Narration
(Entwurf)“** anhaken, daneben den Provider wählen, dann wie gewohnt
**„Delta-Briefing …“**.

## 7. Wenn etwas hakt

| Symptom | Abhilfe |
|---|---|
| `Could not reach Ollama` / Verbindung abgelehnt | Ollama läuft nicht — über das Startmenü starten, auf das Lama-Symbol warten. |
| `Ollama does not know model …` | `ollama pull mistral-nemo` ausführen (Abschnitt 4). |
| Antworten dauern lange | Bis zu einer Minute auf reiner CPU ist normal; `--llm-model mistral` halbiert die Wartezeit ungefähr. |
| Platz auf `C:` knapp | `setx OLLAMA_MODELS "D:\ollama-models"`, danach Ollama neu starten. |
| Ollama beenden | Rechtsklick auf das Lama-Symbol → *Quit Ollama*. |

## 8. Datenschutz in einem Satz

Ollama lauscht nur auf dem eigenen Rechner (`localhost:11434`); weder
Briefing noch Narration verlassen das System — und der Unterschied zum
externen Weg (Claude-API) bleibt über die `deployment_class` in Banner
und Audit jederzeit sichtbar.
