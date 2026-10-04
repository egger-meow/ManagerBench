# ManagerBench constraint pilot

Status: exploratory prototype, not a thesis commitment or a novelty claim.

## Ownership and question

**Human-origin:** Can targeted acceptability questions reveal a person's tolerable
consequences, predict their judgments in unseen situations, and guide an LLM's
decisions? Do person and model mean the same thing by cost/usage? Historical
dialogue is an optional prior; single-step limits and cumulative budgets differ.

**AI-origin experimental simplification:** Start with one known, deterministic
monetary cost borne by the represented organization, one decision, finite integer
thresholds, and explicitly stated benefit. This is an instrument check, not
evidence that humans have a scalar budget. Preserve alternatives: direct
acceptability prediction, nonlinear utility, context-dependent constraints.

## First slice

1. Audit upstream templates without importing its model/GPU dependencies.
2. Compare random, fixed and adaptive queries under the same query allowance
   using labeled synthetic monotone responders. Retain a candidate set, never
   substitute a midpoint for certainty. Contradictions mean model mismatch.
3. Export controlled, ManagerBench-inspired equipment decision prompts with
   known or elicited limits. Score external model responses against a deterministic
   oracle. Keep labels out of model-facing files. Include both option orders,
   missing/invalid responses, under/at/over-limit costs and conservative errors.

Original ManagerBench remains untouched; structured cases are explicitly synthetic
rewrites inspired by a cited control template. This is not an original benchmark
reproduction. No original percentage is converted to money or summed as a budget.
No human-harm permission is inferred from a manager's personal preferences.

## Interpretation and next experiments

- Synthetic threshold recovery checks algorithms only. It is not human validation.
- Human pilot: fixed domain/benefit/consequence bearer/timeframe; yes/no/unsure,
  repeated judgments and held-out scenario families. Do not treat inferred B as truth.
- Known limit + explicit cost isolates instruction compliance. Natural-language
  consequences require independent cost annotations before testing comprehension.
- Compare no-profile, explicit threshold, answer-history and external-filter baselines.
  Only score personalized optimality when the specification supplies that objective.
- Later: short cumulative tasks with additive units and exhaustive sequence oracle;
  relevant/irrelevant history, multidimensional constraints, nonlinear utility.
- Failure of the scalar model is a useful result. If a deterministic filter solves
  explicit numeric cases, test what remains difficult rather than claim a new method.

## Evidence discipline

Freeze source commit and file hashes. Split by scenario family before generation
or paraphrasing. Keep test judgments out of profile construction. Record model,
prompt, seed, missingness and denominators; paired seeds are not independent humans.
Do not train on upstream evaluation data/canary. Keep participant responses local
and untracked. No API calls, fabricated LLM results or invented human labels.

## Reading anchors

- ManagerBench: https://github.com/technion-cs-nlp/ManagerBench
- ACOL: https://proceedings.mlr.press/v162/lindner22a.html
- Asking Easy Questions: https://proceedings.mlr.press/v100/b-iy-ik20a.html
- SafeCRS / SafeRec: https://arxiv.org/abs/2603.03536
- PRISM: https://huggingface.co/datasets/HannahRoseKirk/prism-alignment

ACOL is related constraint-learning work, not implemented by this pilot.
