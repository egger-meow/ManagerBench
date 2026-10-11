# Interactive Error Recovery and Agent-Window Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide an interactive error recovery menu on API failures (429/503/max attempts) and introduce an `AgentBackend` enabling manual/agentic prompt handover via files and terminal for mimicry evaluation.

**Architecture:** 
1. Build `AgentBackend` implementing `generate(request)` with dual-channel (inbox/outbox file and stdin/stdout copy-paste) formatting and schema validation.
2. Integrate `InteractiveErrorHandler` into `JournalClient.call` to offer options (wait & retry, change API key, switch to agent backend, or safe exit) in interactive terminal sessions.
3. Add `--backend` (`google` or `agent`) and `--allow-code-update` flags to `run.py`, `batch.py`, and `workflow.py` while strictly preserving data provenance.

**Tech Stack:** Python 3.11+, standard library (`json`, `sys`, `pathlib`, `os`, `time`), `unittest`.

**Spec:** `docs/superpowers/specs/2026-10-12-interactive-agent-backend-design.md`

## Global Constraints
- `AGENTS.md`: Never present synthetic responders/programmatic baselines as humans or LLMs. Preserve Human-origin versus AI-origin labels.
- Provenance: Any output generated via `AgentBackend` must explicitly log `origin: "agent_interactive"` and `model_version: "agent-mimic:<model>"`.
- Crash safety: Atomic snapshots, OS run locks, and disk journals must never be bypassed.
- Git workflow: Commit and push after every task completion.
- Strict Real Data Fidelity: Do not fake or mock data.

---

### Task 1: Implement `AgentBackend` with Dual-Channel Handover

**Files:**
- Create: `pilot/social_tradeoffs/agent_backend.py`
- Test: `tests/test_agent_backend.py`

**Interfaces:**
- Consumes: `request` dictionary from `JournalClient.call()`:
  ```python
  {
      'provider': 'agent',
      'model': str,
      'role': str,
      'prompt': str,
      'payload': dict,
      'generation_settings': dict,
      'response_schema': dict,
  }
  ```
- Produces: `generate(request) -> dict`:
  ```python
  {
      'text': str,
      'raw': {'origin': 'agent_interactive', 'model_mimic': str, 'text': str},
      'usage': {'prompt_token_count': None, 'candidates_token_count': None},
      'model_version': str,
  }
  ```

- [ ] **Step 1: Write the failing test for `AgentBackend`**

```python
# tests/test_agent_backend.py
import json
import tempfile
import unittest
from pathlib import Path
from pilot.social_tradeoffs.agent_backend import AgentBackend, format_agent_prompt


class TestAgentBackend(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_format_agent_prompt(self):
        request = {
            'model': 'gemini-3.8-flash',
            'role': 'predictor',
            'prompt': '預測測試',
            'payload': {'targets': [{'item_id': 'test-01'}]},
            'response_schema': {'type': 'object', 'properties': {'test-01': {'type': 'string'}}},
        }
        prompt = format_agent_prompt(request)
        self.assertIn('gemini-3.8-flash', prompt)
        self.assertIn('預測測試', prompt)
        self.assertIn('test-01', prompt)
        self.assertIn('[輸出格式要求 (JSON Schema)]', prompt)

    def test_generate_via_outbox_file(self):
        backend = AgentBackend(inbox_path=self.folder / 'agent_inbox.md',
                               outbox_path=self.folder / 'agent_outbox.json',
                               interactive=False)
        request = {
            'model': 'gemini-3.8-flash',
            'role': 'selector',
            'prompt': '選題測試',
            'payload': {'targets': [{'item_id': 'q1'}]},
            'response_schema': {'type': 'object'},
        }
        # Pre-seed the outbox file
        expected_output = {'item_id': 'q1'}
        (self.folder / 'agent_outbox.json').write_text(json.dumps(expected_output), encoding='utf-8')

        result = backend.generate(request)
        self.assertEqual(json.loads(result['text']), expected_output)
        self.assertEqual(result['raw']['origin'], 'agent_interactive')
        self.assertEqual(result['model_version'], 'agent-mimic:gemini-3.8-flash')
        self.assertTrue((self.folder / 'agent_inbox.md').exists())


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests/test_agent_backend.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'pilot.social_tradeoffs.agent_backend')

- [ ] **Step 3: Implement `AgentBackend`**

Write `pilot/social_tradeoffs/agent_backend.py` with `format_agent_prompt` and `AgentBackend` class supporting inbox/outbox file handling and fallback terminal stdin paste.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests/test_agent_backend.py -v`
Expected: PASS

- [ ] **Step 5: Commit and push**

Run:
```bash
git add pilot/social_tradeoffs/agent_backend.py tests/test_agent_backend.py
git commit -m "feat(pilot): add AgentBackend with dual-channel prompt handover"
git push origin main
```

---

### Task 2: Implement `InteractiveErrorHandler` in `llm.py`

**Files:**
- Modify: `pilot/social_tradeoffs/llm.py`
- Test: `tests/test_interactive_error_handler.py`

**Interfaces:**
- Consumes: Exceptions from `backend.generate(request)` or attempt overflows.
- Produces: Interactively prompt user if `sys.stdin.isatty()`, returning one of:
  - `('retry_wait', delay_seconds)`
  - `('update_key', new_key)`
  - `('switch_agent', None)`
  - `('exit', None)`
  or re-raises exception if non-interactive.

- [ ] **Step 1: Write the failing test for `InteractiveErrorHandler`**

```python
# tests/test_interactive_error_handler.py
import unittest
from unittest.mock import patch
from pilot.social_tradeoffs.llm import handle_interactive_error


class TestInteractiveErrorHandler(unittest.TestCase):
    def test_non_interactive_returns_none(self):
        # When isatty is False, handler returns None so caller raises exception
        with patch('sys.stdin.isatty', return_value=False):
            choice = handle_interactive_error('call-01', 429, 'Rate limit')
            self.assertIsNone(choice)

    def test_interactive_choice_switch_agent(self):
        with patch('sys.stdin.isatty', return_value=True), \
             patch('builtins.input', return_value='3'):
            action, val = handle_interactive_error('call-01', 429, 'Rate limit')
            self.assertEqual(action, 'switch_agent')

    def test_interactive_choice_wait_retry(self):
        with patch('sys.stdin.isatty', return_value=True), \
             patch('builtins.input', side_effect=['1', '5']):
            action, delay = handle_interactive_error('call-01', 503, 'High demand')
            self.assertEqual(action, 'retry_wait')
            self.assertEqual(delay, 5)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests/test_interactive_error_handler.py -v`
Expected: FAIL (ImportError: cannot import name 'handle_interactive_error')

- [ ] **Step 3: Implement `handle_interactive_error` and integrate into `JournalClient.call`**

In `pilot/social_tradeoffs/llm.py`:
- Add `handle_interactive_error(call_id, code, message)` function.
- Integrate into `JournalClient.call` so that when `ClientError` (429), `ServerError` (503), or attempts limit is hit:
  - Call `handle_interactive_error()`.
  - Handle `switch_agent`: reassign `self.backend = AgentBackend(...)` and retry call.
  - Handle `update_key`: update `os.environ['GEMINI_API_KEY']`, re-create `GoogleBackend()`, and retry call.
  - Handle `retry_wait`: sleep for specified seconds and retry.
  - Handle `exit`: safely log checkpoint and call `sys.exit(0)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests/test_interactive_error_handler.py -v`
Expected: PASS

- [ ] **Step 5: Commit and push**

Run:
```bash
git add pilot/social_tradeoffs/llm.py tests/test_interactive_error_handler.py
git commit -m "feat(pilot): add interactive error recovery handler in JournalClient"
git push origin main
```

---

### Task 3: Support `--backend` and `--allow-code-update` in `run.py`, `batch.py`, and `workflow.py`

**Files:**
- Modify: `pilot/social_tradeoffs/run.py`
- Modify: `pilot/social_tradeoffs/batch.py`
- Modify: `pilot/social_tradeoffs/workflow.py`
- Test: `tests/test_social_workflow.py`

**Interfaces:**
- Consumes: CLI args `--backend [google|agent]`, `--allow-code-update`.
- Produces: Backend instantiation routing to `GoogleBackend` or `AgentBackend`, and permitting code hash migration on resume when explicitly requested.

- [ ] **Step 1: Write test for `--backend agent` CLI execution**

In `tests/test_social_workflow.py`, add a test verifying `execute_batch` and CLI with `backend='agent'`.

- [ ] **Step 2: Run test to verify failure/missing argument**

Run: `python -m unittest tests/test_social_workflow.py -v`
Expected: Fail or unrecognized argument.

- [ ] **Step 3: Update `run.py`, `batch.py`, and `workflow.py`**

- In `run.py`:
  - Add `--backend` argument (`choices=['google', 'agent']`, default `'google'`).
  - Add `--allow-code-update` argument (`action='store_true'`).
  - In `load_run()`: if `--allow-code-update` is True, print migration notice and allow code hash difference.
  - In `execute()`: instantiate `AgentBackend(inbox_path=folder / 'agent_inbox.md', outbox_path=folder / 'agent_outbox.json')` if backend is `'agent'`.
- In `batch.py`:
  - Pass `backend` parameter to `execute_batch()`.
- In `workflow.py`:
  - Pass through `--backend` and `--allow-code-update`.

- [ ] **Step 4: Run test suite to verify all tests pass**

Run: `python -m unittest discover -s tests -v`
Expected: All tests pass.

- [ ] **Step 5: Run git diff check**

Run: `git diff --check`
Expected: Clean.

- [ ] **Step 6: Commit and push**

Run:
```bash
git add pilot/social_tradeoffs/run.py pilot/social_tradeoffs/batch.py pilot/social_tradeoffs/workflow.py tests/test_social_workflow.py
git commit -m "feat(pilot): add CLI support for agent backend and allow-code-update flag"
git push origin main
```

---

### Task 4: End-to-End Verification and Resume Existing Batch

**Files:**
- Existing run: `runs/social-3ff94a35e97447fe90fc289f9c0d08f9`

- [ ] **Step 1: Test resume with `--allow-code-update` and check interactive menu**
Run dry-run or targeted verification on the existing batch.
- [ ] **Step 2: Ensure test suite and codebase integrity**
Run `python -m unittest discover -s tests -v` and `git diff --check`.
- [ ] **Step 3: Final commit and push**
```bash
git status
git commit -m "chore: complete interactive error recovery and agent backend integration"
git push origin main
```
