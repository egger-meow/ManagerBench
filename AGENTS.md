# Research agent instructions

Read `RESEARCH_START.md` and `docs/research-direction.md` first.

The human owns the research question. Preserve Human-origin versus AI-origin
labels. Treat this as exploration; do not invent novelty or lock a thesis topic.
Core question: targeted acceptability elicitation, cost interpretation and
constraint execution are separate possible failure modes.

- Preserve upstream benchmark, LICENSE and canary. Extensions live in `pilot/`.
- Keep human responses, keys and run outputs untracked; do not upload them.
- Never present synthetic responders/programmatic baselines as humans or LLMs.
- Do not fabricate numeric annotations from prose or sum heterogeneous percentages.
- Original harm percentages may mean probability or population share. Audit semantics.
- Unknown thresholds remain candidate sets/intervals; contradictions challenge the model.
- Comparing A/B preference alone is not an acceptability label; allow neither/both/unsure.
- No training on evaluation data. Split by scenario family before any paraphrasing.
- Keep external costs, decision maker and consequence bearer explicit.
- Scalar hard constraints do not capture all nonlinear/contextual human preferences.
- Test simpler explanations, including deterministic filters and direct acceptability prediction.
- Do not expand to RL, historical profiling or cumulative tasks before the current
  controlled experiment has been inspected with the human.

Run `python -m unittest discover -s tests -v` and `git diff --check` before a PR.
Use `python -m pilot --help` for the offline CLI. No implicit network/API calls.
Next research step: collect actual responses to the 26 known-limit requests;
then discuss failures and the elicited-limit condition with the human.
