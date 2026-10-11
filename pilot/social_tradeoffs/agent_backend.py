"""Agent / manual interactive backend.

Allows an external agent (such as Antigravity, Codex, or a web chat) to act as the
predictor/selector mimic, using dual-channel (inbox/outbox file or terminal paste) handover.
"""
import json
import os
from pathlib import Path
import sys
import time


def format_agent_prompt(request):
    model = request.get('model', 'unknown')
    role = request.get('role', 'unknown')
    prompt = request.get('prompt', '')
    payload_json = json.dumps(request.get('payload', {}), ensure_ascii=False, indent=2)
    schema_json = json.dumps(request.get('response_schema', {}), ensure_ascii=False, indent=2)

    return f"""======================== [AGENT TASK PROMPT] ========================
你是本實驗指定的預測模型模擬窗口。請根據以下系統提示詞與題目資料，
以模型【{model}】的視角作答，並嚴格依照指定 JSON Schema 輸出純 JSON。
角色：{role}

[系統指示 (System Instruction)]:
{prompt}

[輸入資料 (Input Payload)]:
{payload_json}

[輸出格式要求 (JSON Schema)]:
{schema_json}

重要：請只輸出符合上述 Schema 的合法 JSON，不加任何 Markdown 語法標記或額外對話說明。
=====================================================================
"""


def strip_markdown_fences(text):
    text = text.strip()
    if text.startswith('```'):
        lines = text.splitlines()
        if lines[0].startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        text = '\n'.join(lines).strip()
    return text


class AgentBackend:
    def __init__(self, folder=None, inbox_path=None, outbox_path=None, interactive=True):
        self.folder = Path(folder) if folder else None
        self.inbox_path = Path(inbox_path) if inbox_path else (self.folder / 'agent_inbox.md' if self.folder else None)
        self.outbox_path = Path(outbox_path) if outbox_path else (self.folder / 'agent_outbox.json' if self.folder else None)
        self.interactive = interactive

    def generate(self, request, clean_outbox=True):
        prompt_text = format_agent_prompt(request)
        model = request.get('model', 'unknown')

        # 1. 寫入 inbox 檔案
        if self.inbox_path:
            self.inbox_path.parent.mkdir(parents=True, exist_ok=True)
            self.inbox_path.write_text(prompt_text, encoding='utf-8')

        # 2. 清除舊的 outbox 避免讀取過期結果
        if clean_outbox and self.outbox_path and self.outbox_path.exists():
            try:
                self.outbox_path.unlink()
            except OSError:
                pass

        # 3. 輸出至終端機
        print('\n' + prompt_text, flush=True)
        if self.inbox_path and self.outbox_path:
            print(f"📋 [檔案交接] 任務已寫入：{self.inbox_path}", flush=True)
            print(f"👉 請在 New Chat 指示 Agent 完成並存至：{self.outbox_path}", flush=True)
            print("👉 或者：直接在下方貼上 JSON（以 END 換行結尾），或儲存 outbox 後直接按 [Enter]：", flush=True)

        text = None
        if not self.interactive or not sys.stdin.isatty():
            # 非交互模式：等待 outbox.json 出現
            if self.outbox_path:
                print(f"等待 {self.outbox_path} 寫入...", flush=True)
                for _ in range(300):
                    if self.outbox_path.exists():
                        content = self.outbox_path.read_text(encoding='utf-8').strip()
                        if content:
                            text = content
                            break
                    time.sleep(1)
            if text is None:
                raise RuntimeError("非交互環境下未偵測到 agent_outbox.json 回覆。")
        else:
            # 互動模式：支援檔案寫入後 Enter 或終端貼上
            while True:
                try:
                    line = input("> ").strip()
                except (EOFError, KeyboardInterrupt):
                    raise RuntimeError("使用者中斷輸入。") from None

                if not line:
                    # 使用者按 Enter：檢查 outbox.json 是否已產生
                    if self.outbox_path and self.outbox_path.exists():
                        content = self.outbox_path.read_text(encoding='utf-8').strip()
                        if content:
                            text = content
                            print(f"✅ 已自 {self.outbox_path} 讀取回覆！", flush=True)
                            break
                        else:
                            print(f"⚠️ {self.outbox_path} 內容為空，請儲存後再次按 Enter，或直接在此貼上 JSON：", flush=True)
                    else:
                        target = self.outbox_path if self.outbox_path else "outbox"
                        print(f"⚠️ 尚未偵測到 {target}。請儲存檔案後按 Enter，或在此直接貼上 JSON：", flush=True)
                else:
                    # 使用者開始輸入/貼上多行內容
                    lines = [line]
                    if line.startswith('{') and line.endswith('}'):
                        # 單行完整 JSON
                        text = line
                        break
                    while True:
                        try:
                            l = input()
                        except EOFError:
                            break
                        if l.strip() == 'END':
                            break
                        lines.append(l)
                    text = '\n'.join(lines).strip()
                    if text:
                        break

        text = strip_markdown_fences(text)
        return {
            'text': text,
            'raw': {
                'origin': 'agent_interactive',
                'model_mimic': model,
                'text': text,
            },
            'usage': {'prompt_token_count': None, 'candidates_token_count': None},
            'model_version': f"agent-mimic:{model}",
        }

    def close(self):
        pass
