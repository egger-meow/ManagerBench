# Paired agent-mimic rerun

`backend=agent` in the original runner is a passive inbox/outbox handoff. It does
not launch a model. Noninteractive handoffs time out after 300 seconds.

`python -m pilot.social_tradeoffs.agent_pair` supplies the missing coordinator.
It invokes the installed Codex CLI with the existing ChatGPT login; it never
constructs a GoogleBackend or uses a Gemini API key. Codex inference uses the
account's Codex capacity. Allowed payloads (including already revealed query
answers and reasons, when enabled) are sent to the external Codex inference
service. Local storage does not mean offline inference. This requires explicit
authorization via `--allow-codex-inference`. This is agent-mimic evidence, not
Gemini API evidence.

Each request starts a new ephemeral CLI process, with memory, project documents,
plugins, apps, shell tools, browser and web search disabled. Only the original
model-facing prompt/payload/schema is sent on stdin. Unexpected tool activity in
the JSONL trace is rejected. No parent chat, answer book or previous results are
sent. Validate isolation with a data-free probe in the target runtime first;
`fork_turns=none` alone does not prove that preloaded memories are absent.

Both conditions are initialized from one in-memory answer snapshot before any
inference. They share the agent model, instrument, prompt, code, seed and query
budget. Only participant reason access differs. The original Gemini target and
sampling settings remain mimic metadata; they are not Codex sampling controls.
The configured actual Codex model is recorded separately; a resolved provider
model version is unknown. Raw outputs, task hashes, command and traces are private
files under ignored `runs/` directories. Never commit those files.

From the repository root, use an environment with the existing
`pilot/social_tradeoffs/requirements.txt` installed:

```powershell
python -m pilot.social_tradeoffs.agent_pair --pair-id corrected-agent-NEW --agent-model YOUR_VERIFIED_CODEX_MODEL --allow-codex-inference --preflight
python -m pilot.social_tradeoffs.agent_pair --resume runs/corrected-agent-NEW --allow-codex-inference
```

Preflight completes and journals only fixed/no-reason k=0. Resume reuses that
validated response and completes all 38 requests across two conditions. Each
condition runs fixed/random/adaptive; every selector/predictor still starts a
new agent process. Conditions can run concurrently without sharing agent history.
Allow up to 30 minutes per CLI process, rather than the passive five-minute
handoff timeout. Failed or ambiguous requests remain recorded; inspect their
private `agent_tasks` trace before explicitly using `--retry-ambiguous`.
Existing unjournaled outputs are never silently regenerated or overwritten.

Completion requires both batch `completed.json` files and the pair completion
marker. The pair directory contains `paired-scores.json`, `report.md` and
`reasoning-comparison.png`/`.svg`. Coverage remains separate from accuracy.
