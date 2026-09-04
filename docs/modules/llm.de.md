# llm

Steckbare LLM-Schicht (Roadmap D2 Teil 2): Ein Sprachmodell entwirft die
Lage-Narration zum Delta-Briefing — **lokal zuerst, immer gekennzeichnet,
bei Zahlen nie im Vertrauen**. Das `sources`-Muster, auf KI-Backends
übertragen.

**Status:** umgesetzt (alpha)

## Design: das sources-Muster für KI

- **Austauschbar** — der Report sieht nie einen Anbieter. Ein Provider
  implementiert einen Contract (`complete(system, prompt, config) →
  LlmResult`); alles andere — Prompt, Wächter, Kennzeichnung, Audit —
  liegt zentral in `llm/` und ist für jedes Backend identisch.
- **Lokal zuerst** — `ollama` (Standardmodell `mistral-nemo`) betreibt
  das Modell vollständig auf dem eigenen Rechner: kein Konto, kein
  Schlüssel, keine Konzern-Freigabe, Daten verlassen das System nie.
  `claude` (Anthropic Messages API, Standard `claude-sonnet-5`) ist der
  externe Weg; `mock` zeigt den kompletten Ablauf ganz ohne Modell.
- **Leicht erweiterbar** — ein neues Backend ist EINE Datei in
  `llm/providers/` mit einem `PROVIDER`-Objekt; die Auto-Discovery
  findet sie (`python -m llm providers` ist das maßgebliche Inventar).

## Drei Wächter — verdrahtet, nicht dokumentiert

1. **Zahlen-Wächter** (`llm/guard.py`) — jede Zahl im generierten Text
   muss wörtlich im Briefing stehen, sonst wird der Text mit klarer
   Fehlermeldung verworfen: *das LLM textet, es rechnet nicht.*
   (Einzelziffern gelten als Prosa.)
2. **KI-Kennzeichnung** (Art. 50 KI-VO) — jeder Entwurf trägt sichtbar
   Modell, Deployment-Klasse und Prompt-Version und behauptet nie eine
   Freigabe; die erteilt erst der Mensch, der den Entwurf redigiert.
3. **Betreiber-Nachweis** (`llm/audit.py`) — jede Anfrage hängt eine
   JSONL-Zeile an (`llm_audit.jsonl`): Zeitstempel, Provider, Modell,
   Deployment-Klasse, Prompt-Version, Dauer, SHA-256-Hashes von Eingabe
   und Ausgabe, Wächter-Urteil. Nur Hashes — nie Volltexte, nie
   Schlüssel.

`llm/narrate.py` verdrahtet alle drei um jede Vervollständigung; kein
Aufrufer kann sie umgehen, ohne das Modul zu meiden.

## Benutzung

```
python -m llm providers                 # Inventar
python -m llm test [--llm mock]         # Verkabelungs-Check (gekennzeichnete Probe)

python -m portfolio --delta vorher.json jetzt.json --narrate \
    [--llm ollama|claude|mock] [--llm-model NAME] [--llm-lang de|en] \
    --output delta.html
```

Seit D1 wirkt `--narrate` auch auf einen **Report-Lauf** mit
HTML-`--output`: die gekennzeichnete *Executive Summary (Entwurf)*
landet direkt unter der Management-Summary-Tabelle; Eingabe ist der
deterministische Summary-Contract (Kennzahlen, Quell-Konfidenz,
Governance-Kopfzahlen — strukturell ohne Personen-/Owner-Felder), dazu
`<output>.exec_summary.md` zum Redigieren (Audit-Zweck
`d1_exec_summary`).

Ohne `--narrate` ist das Briefing exakt die deterministische D2-Ausgabe
(saubere Degradation). Mit Flag bekommt es den gekennzeichneten
Abschnitt **„Narration (Entwurf)“**; die Markdown-Ausgabe schreibt
zusätzlich `<output>.narration.md` — den Entwurf, den ein Mensch
redigiert und freigibt. In der GUI: Checkbox „KI-Narration (Entwurf)“
plus Provider-Auswahl; der Testdaten-Generator führt den Ablauf am
Demo-Portfolio mit wählbarem Provider vor (Default `mock` — ohne
Installation; für den echten Lauf auf `ollama`/`claude` umschalten).

Das Modell sieht ausschließlich den Markdown-Contract des
Delta-Briefings — der nennt per Konstruktion Teams, ARTs und Solutions,
nie Personen (durch einen Pipeline-Test erzwungen).

## Ollama einrichten (der lokale Weg)

Siehe das Tutorial [Ollama auf Windows 11 installieren](../tutorials/install-ollama.md)
— auch als separate PDFs:
[DE](../ollama_Installationsanleitung_DE.pdf) /
[EN](../ollama_Installationsanleitung_EN.pdf). Kurzfassung:
von ollama.com installieren, `ollama pull mistral-nemo`, dann
`python -m llm test`.

## Rezept: ein neues Backend anbinden

Eine Datei, z. B. `llm/providers/my_backend.py`:

```python
from llm.base import DEPLOYMENT_EXTERNAL, LlmResult

class MyBackend:
    provider_id = "my_backend"
    deployment_class = DEPLOYMENT_EXTERNAL   # sichtbar in Banner + Audit
    default_model = "my-model-1"

    def complete(self, system, prompt, config):
        text = ...  # deine API; Schluessel NUR aus einer Umgebungsvariable
        return LlmResult(text=text, provider_id=self.provider_id,
                         model=self.default_model,
                         deployment_class=self.deployment_class)

PROVIDER = MyBackend()
```

Provider generieren — sie urteilen nie, kennzeichnen nie, loggen nie;
das geschieht zentral. API-Schlüssel nur aus Umgebungsvariablen
(`ANTHROPIC_API_KEY` für `claude`, per `token_env` übersteuerbar), nie
gespeichert, nie geloggt. Mit Mocks testen (`tests/llm/unit/` zeigt das
Request-Recorder-Muster); ein optionaler Live-Test gegen Ollama läuft
mit `-m ollama_live`.
