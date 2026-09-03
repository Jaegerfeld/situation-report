# Installing Ollama on Windows 11

**Audience:** anyone who wants the AI narration to run locally. **Time:**
about 15 minutes plus the model download. **You need:** Windows 11 and
disk space for the model — no admin rights, no account, no API key.
**At the end:** `--narrate` drafts narrations on your machine, and no
data ever leaves it.

This guide is also available as a separate PDF:
[EN](../ollama_Installationsanleitung_EN.pdf) /
[DE](../ollama_Installationsanleitung_DE.pdf).

---

## 1. Why local?

Ollama runs language models entirely on your own machine. For the
situation report's AI narration this means: the delta briefing never
leaves the system, and you need no corporate approval for external
services. This path shows up as `deployment_class "local"` in the AI
banner and in the operator-evidence log (`llm_audit.jsonl`).

## 2. Prerequisites

- Windows 11, 64-bit; no administrator rights needed (Ollama installs
  into the user profile).
- Disk space: ~4 GB for Ollama itself plus the model — `mistral-nemo`
  downloads about 7 GB, `mistral` about 4 GB.
- Memory: 16 GB recommended for `mistral-nemo` (12B); with 8 GB pick the
  smaller `mistral` (7B).
- Without a GPU everything runs on the CPU — a narration then takes up
  to a minute. An NVIDIA or AMD GPU is used automatically.

## 3. Install

1. Open [ollama.com/download/windows](https://ollama.com/download/windows)
   and download `OllamaSetup.exe`.
2. Double-click the file and follow the wizard — there are no choices to
   make.
3. Ollama then runs in the background; the llama icon appears in the
   taskbar's notification area, and it starts automatically after a
   reboot.

Verify the installation (Windows key, type `powershell`):

```
ollama --version
```

## 4. Pull the model

The narration's default model is `mistral-nemo`:

```
ollama pull mistral-nemo
```

On an 8 GB machine, use `ollama pull mistral` instead. Quick test — the
first answer takes longest because the model is loaded into memory
(leave the chat with `/bye`):

```
ollama run mistral-nemo "Answer in one sentence: what is a situation report?"
```

## 5. Wiring check with SituationReport

```
python -m llm providers
python -m llm test
```

`providers` lists the discovered AI backends (`ollama`, `claude`,
`mock`); `test` runs one labeled sample narration through Ollama — if it
prints a draft with the AI banner, everything is wired.

## 6. Use it

CLI — `--narrate` adds the labeled **Narration (Entwurf)** section to
the delta briefing; the numbers guard discards any invented figure, and
the evidence record lands in `llm_audit.jsonl` next to the output:

```
python -m portfolio --delta prev.json now.json --narrate --output delta.html --browser
```

GUI — in the Solutions & Portfolios window tick **AI narration
(draft)**, pick the provider next to it, then run **Delta briefing …**
as usual.

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| `Python was not found` (points to the Microsoft Store) | Windows redirects `python` to a Store placeholder. Run the commands in the repository folder and use `.venv\Scripts\python.exe` there (or activate once: `.venv\Scripts\Activate.ps1`); alternatively `py -m llm test`, or disable the app execution aliases `python.exe`/`python3.exe` under *Settings → Apps → Advanced app settings*. |
| `Could not reach Ollama` / connection refused | Ollama is not running — start it from the Start menu, wait for the llama icon. |
| `Ollama does not know model …` | Run `ollama pull mistral-nemo` (section 4). |
| Answers are slow | Up to a minute on pure CPU is normal; `--llm-model mistral` roughly halves the wait. |
| Low space on `C:` | `setx OLLAMA_MODELS "D:\ollama-models"`, then restart Ollama. |
| Stop Ollama | Right-click the llama icon → *Quit Ollama*. |

## 8. Privacy in one sentence

Ollama listens on your machine only (`localhost:11434`); neither
briefing nor narration ever leaves the system — and the difference from
the external path (Claude API) stays visible at all times via the
`deployment_class` in banner and audit.
