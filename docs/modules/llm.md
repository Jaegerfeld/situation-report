# llm

Pluggable LLM layer (roadmap D2 part 2): a language model drafts the
situational narration for the delta briefing — **local first, always
labeled, never trusted with numbers**. The `sources` pattern transferred
to AI backends.

**Status:** implemented (alpha)

## Design: the sources pattern for AI

- **Exchangeable** — the report never sees a vendor. A provider
  implements one contract (`complete(system, prompt, config) →
  LlmResult`); everything else — prompt, guards, labeling, audit — is
  central in `llm/` and identical for every backend.
- **Local first** — `ollama` (default model `mistral-nemo`) runs the
  model entirely on the user's machine: no account, no key, no corporate
  API approval, data never leaves the system. `claude` (Anthropic
  Messages API, default `claude-sonnet-5`) is the external alternative;
  `mock` demonstrates the full flow without any model.
- **Easy to extend** — a new backend is ONE file in `llm/providers/`
  defining a `PROVIDER` object; auto-discovery picks it up
  (`python -m llm providers` is the authoritative inventory).

## Three guards, wired in — not documented

1. **Numbers guard** (`llm/guard.py`) — every number in the generated
   text must occur verbatim in the briefing, otherwise the text is
   discarded with a clear error: *the LLM writes, it does not
   calculate.* (Single digits are treated as prose.)
2. **AI label** (Art. 50 EU AI Act) — every draft carries a visible
   banner with model, deployment class and prompt version, and never
   claims approval; only the human who edits the draft approves it.
3. **Operator evidence** (`llm/audit.py`) — every request appends a
   JSONL record (`llm_audit.jsonl`): timestamp, provider, model,
   deployment class, prompt version, duration, SHA-256 hashes of input
   and output, guard verdict. Hashes only — never full texts, never
   keys.

`llm/narrate.py` wires all three around every completion; callers cannot
bypass them without avoiding the module.

## Usage

```
python -m llm providers                 # inventory
python -m llm test [--llm mock]         # wiring check (labeled sample)
python -m llm translate FILE --to en ro # D6: deliver an edited text in
                                        # other house languages

python -m portfolio --delta prev.json now.json --narrate \
    [--llm ollama|claude|mock] [--llm-model NAME] [--llm-lang de|en] \
    --output delta.html
```

Since D1, `--narrate` also acts on a **report run** with an HTML
`--output`: the labeled *Executive Summary (Entwurf)* lands directly
below the Management-Summary table, its input being the deterministic
summary contract (metrics, source confidence, governance head counts —
structurally without person/owner fields), plus
`<output>.exec_summary.md` for editing (audit purpose
`d1_exec_summary`).

**Multilingual delivery (D6):** `--translate LANG …` on the portfolio
CLI additionally delivers the run's primary text in the house languages
(draft → `.narration.<lang>.md` / `.exec_summary.<lang>.md`;
deterministic briefing → `.<lang>.md`), and `python -m llm translate`
fans an edited, approved file out per language. The numbers invariant is
the perfect translation guard; banners are written in the target
language (all five house languages), audit purpose `d6_translation`.

**Red-team questions (D5):** `--red-team FILE` on a config generates
premortem/attack questions from the decision log — a **questions guard**
machine-discards any non-question output (raw material for judgement,
never judgements; audit purpose `d5_red_team`).

Without `--narrate` the briefing is exactly the deterministic D2 output
(clean degradation). With it, the briefing gains the labeled section
**Narration (Entwurf)**; Markdown output additionally writes
`<output>.narration.md` — the draft a human edits and approves. In the
GUI: checkbox *AI narration (draft)* plus provider picker; the test-data
generator demos the flow on the demo portfolio with a selectable
provider (default `mock` — no installation; switch to `ollama`/`claude`
for the real thing).

The model only ever sees the delta briefing's Markdown contract — which
by construction names teams, ARTs and solutions, never persons (enforced
by a pipeline test).

## Setting up Ollama (the local path)

See the tutorial [Install Ollama on Windows 11](../tutorials/install-ollama.md)
— also available as separate PDFs:
[DE](../ollama_Installationsanleitung_DE.pdf) /
[EN](../ollama_Installationsanleitung_EN.pdf). Short version:
install from ollama.com, `ollama pull mistral-nemo`, then
`python -m llm test`.

## Recipe: attach a new backend

One file, e.g. `llm/providers/my_backend.py`:

```python
from llm.base import DEPLOYMENT_EXTERNAL, LlmResult

class MyBackend:
    provider_id = "my_backend"
    deployment_class = DEPLOYMENT_EXTERNAL   # shown in banner + audit
    default_model = "my-model-1"

    def complete(self, system, prompt, config):
        text = ...  # call your API; key ONLY from an env var
        return LlmResult(text=text, provider_id=self.provider_id,
                         model=self.default_model,
                         deployment_class=self.deployment_class)

PROVIDER = MyBackend()
```

Providers generate — they never judge, never label, never log; that
happens centrally. API keys only from environment variables
(`ANTHROPIC_API_KEY` for `claude`, overridable via `token_env`), never
stored, never logged. Test with mocks (`tests/llm/unit/` shows the
request-recorder pattern); an optional live test for Ollama runs with
`-m ollama_live`.
