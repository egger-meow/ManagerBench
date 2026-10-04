# Constraint Pilot Implementation Plan

**Goal:** Runnable offline instrument for the user's constraint-elicitation question.
**Architecture:** Python standard library; independent upstream audit, finite
threshold learner, controlled evaluation export and strict response scoring.
**Tech Stack:** Python 3.10+, unittest, JSON/JSONL.
**Spec:** docs/research-direction.md

## Global constraints

Do not alter upstream data or runner. Never call an API implicitly. Synthetic
results must say synthetic. Human responses and generated runs stay untracked.
No midpoint oracle for uncertain thresholds; no combining unlike harm percentages.

## Review focus

Boundary equality, all-accept/all-reject, contradictions, answer-label permutations,
missing/invalid/duplicate responses and evaluator-label leakage.

## Tasks

- [x] Write failing tests in tests/test_pilot.py for threshold recovery,
  uncertainty, contradictions, oracle ties/boundaries, label isolation and scoring.
- [x] Implement pilot/core.py: candidate-set updates and safe action oracle.
- [x] Implement pilot/data.py: audited upstream inventory and controlled cases.
- [x] Implement pilot/__main__.py: audit, demo, export, score and elicit commands.
- [x] Run unittest and end-to-end CLI smoke checks; write usage and evidence.
- [ ] Commit on research/constraint-pilot and open a draft PR on user's fork.
