# Design Specification: Interactive Error Recovery and Agent-Window Backend

- **Date:** 2026-10-12
- **Topic:** Interactive Error Handling & Agent-Window Backend for Social Tradeoffs Pilot
- **Status:** Approved for Implementation

---

## 1. Overview and Problem Statement

### 1.1 Background
The `pilot/social_tradeoffs` workflow runs multi-stage elicitation and evaluation (across `fixed`, `random`, and `adaptive` strategies).
During execution, the runner calls LLM endpoints for selection and prediction via `JournalClient` and `GoogleBackend`.

### 1.2 Identified Issues
1. **Hard Failures on API Errors:**
   - When Google's API returns `HTTP 429 RESOURCE_EXHAUSTED` (e.g. daily free-tier limit of 20 requests per day) or `HTTP 503 UNAVAILABLE` (spikes in demand), or when attempts reach the predefined maximum (`max_api_attempts = 3`), the runner immediately raises `AmbiguousCall` or `RuntimeError` and terminates with a crash traceback.
   - In non-interactive loops, it repeatedly crashes without diagnosing the issue or offering the user interactive choices to recover.
2. **Lack of Agent-in-the-Loop / Mimicry Window:**
   - The runner previously supported only direct `GoogleBackend` (via Google GenAI API).
   - When users lack API quota, prefer using an interactive agent (like Antigravity in the IDE, Codex, or web-based ChatGPT/Claude), or want to conduct evaluations by opening a clean, isolated "New Chat" to avoid context leakage, there is no standardized handover mechanism that matches the exact prompt, schema, and journal integrity of the LLM API flow.

---

## 2. Core Architecture and Design

```mermaid
flowchart TD
    CLI[workflow.py / run.py] --> JC[JournalClient.call]
    JC --> BackendChoice{Backend: google or agent?}
    
    %% Agent Backend Flow
    BackendChoice -->|agent| AB[AgentBackend.generate]
    AB --> ExportPrompt[寫入 runs/<run_id>/agent_inbox.md & 印出終端]
    ExportPrompt --> UserAction[使用者在 New Chat 貼上 / Antigravity 讀取 inbox]
    UserAction --> WriteOutbox[寫入 runs/<run_id>/agent_outbox.json 或貼入終端]
    WriteOutbox --> ValidateAgent[JSON Schema 校驗]
    ValidateAgent --> JournalCommit[記錄至 journal / validated.json]
    
    %% Google Backend Flow
    BackendChoice -->|google| GB[GoogleBackend.generate]
    GB --> APIErr{API 錯誤: 429/503/MaxAttempts?}
    APIErr -->|正常| ValidateAPI[JSON Schema 校驗]
    ValidateAPI --> JournalCommit
    
    APIErr -->|異常| InteractiveCheck{sys.stdin.isatty()?}
    InteractiveCheck -->|非交互| Crash[安全中止並記錄錯誤]
    InteractiveCheck -->|交互| Menu[顯示互動選單]
    Menu -->|1 等待重試| RetryWait[倒數/等待後重試]
    RetryWait --> GB
    Menu -->|2 更換 Key| UpdateKey[輸入新 GEMINI_API_KEY]
    UpdateKey --> GB
    Menu -->|3 切換 Agent| SwitchAgent[動態切換至 AgentBackend]
    SwitchAgent --> AB
    Menu -->|4 安全退出| GracefulExit[儲存 Checkpoint 並正常結束 exit 0]
```

### 2.1 Module 1: `AgentBackend` (Agent 窗口後端)
- **Interface:** Implements `generate(request)` identical to `GoogleBackend.generate(request)`.
- **Request payload:** Contains `role`, `prompt` (system instruction), `payload` (history + targets), `generation_settings`, `response_schema`, and `model` (target model identifier to mimic, e.g. `gemini-3.8-flash`).
- **Prompt Formulation:** Formats a structured, self-contained Markdown prompt:
  ```markdown
  ======================== [AGENT TASK PROMPT] ========================
  你是本實驗指定的預測模型模擬窗口。請根據以下系統提示詞與題目資料，
  以模型【{model}】的視角作答，並嚴格依照指定 JSON Schema 輸出純 JSON。

  [系統指示 (System Instruction)]:
  {prompt}

  [輸入資料 (Input Payload)]:
  {payload_json}

  [輸出格式要求 (JSON Schema)]:
  {schema_json}

  重要：請只輸出符合上述 Schema 的合法 JSON，不加任何 Markdown 語法標記或前後說明。
  =====================================================================
  ```
- **Dual-Channel Handover:**
  1. **File Channel:**
     - Writes the prompt to `<run_folder>/agent_inbox.md`.
     - Watches `<run_folder>/agent_outbox.json` for agent output.
     - In Antigravity IDE, user can simply ask in a new chat: `@runs/.../agent_inbox.md 請依指示輸出 JSON 至 runs/.../agent_outbox.json`.
  2. **Terminal Channel:**
     - Prints the formatted block to stdout.
     - Prompts for stdin input (ended by `END` line or EOF `Ctrl+Z` / `Ctrl+D`), or file save.
- **Validation & Return:**
  - Parses response string as JSON, validates with schema.
  - Returns:
    ```python
    {
        'text': json_str,
        'raw': {'origin': 'agent_interactive', 'model_mimic': request['model']},
        'usage': {'prompt_token_count': None, 'candidates_token_count': None},
        'model_version': f"agent-mimic:{request['model']}",
    }
    ```
  - Provenance: Transparently marked as `agent-mimic` in accordance with `AGENTS.md` and Real Data Fidelity.

### 2.2 Module 2: `InteractiveErrorHandler` (互動式錯誤恢復器)
- **Location:** Integrated into `JournalClient.call()` exception handler.
- **Trigger Conditions:**
  - `HTTP 429` (Quota / Rate limit reached)
  - `HTTP 503` (Server high demand / Unavailable)
  - Exceeding attempt limit (`max_api_attempts` reached)
  - Network timeouts / connection resets
- **Interactive Check:**
  - If `not sys.stdin.isatty()`, preserves existing fail-safe halt.
  - If `sys.stdin.isatty()`, displays a clear diagnosis:
    - 429: Explains quota exhaustion and estimated reset time.
    - 503: Explains temporary server demand spike.
    - Max attempts: Explains bounded retry budget reached.
- **Interactive Menu Options:**
  - `[1] 等待並重試 (Wait & Retry)`: Allows customizable delay or immediate retry.
  - `[2] 更換 API Key (Update API Key)`: Prompts for a new key, updates `GEMINI_API_KEY`, reinstantiates backend, and retries.
  - `[3] 切換為 Agent 窗口模式 (Switch to Agent Window)`: Dynamically swaps backend to `AgentBackend` for the current and subsequent calls.
  - `[4] 安全保存進度並退出 (Save & Exit)`: Gracefully exits with status 0, allowing `--resume` later.

### 2.3 Module 3: CLI & Compatibility Support
- **CLI Options:**
  - `--backend`: Choices `['google', 'agent']` (default `'google'`).
  - `--allow-code-update`: Allows `--resume` to proceed even if code revisions/hashes have been updated, avoiding blocking historical runs in progress.
- **Workflow Forwarding:**
  - `pilot/social_tradeoffs/workflow.py` forwards `--backend` and `--allow-code-update` properly.

---

## 3. Data Integrity and Provenance Compliance

1. **`AGENTS.md` Rules:**
   - *"Never present synthetic responders/programmatic baselines as humans or LLMs."*
   - When `AgentBackend` is used, metadata records `provider: "agent"`, `model_version: "agent-mimic:<model>"`, and raw payload logs `origin: "agent_interactive"`.
2. **Immutability of Snapshots:**
   - Instruments, answer books, and prompts remain immutable and snapshot-verified.
3. **Atomic Persistence:**
   - Every selection and prediction continues to be saved atomically in `selections/step-*.json` and `predictions/stage-*.json`.

---

## 4. Verification and Testing Plan

1. **Unit Tests:**
   - `test_agent_backend_file_handover`: Tests `AgentBackend` with mock file outbox.
   - `test_agent_backend_terminal_handover`: Tests `AgentBackend` with mock stdin.
   - `test_interactive_error_handler_switch_to_agent`: Tests switching from failed API call to agent backend.
   - `test_interactive_error_handler_update_key`: Tests updating API key dynamically.
   - `test_cli_backend_flag`: Verifies `--backend agent` runs end-to-end with stubbed input.
2. **Regression Tests:**
   - Run existing test suite: `python -m unittest discover -s tests -v`.
   - Run `git diff --check`.
