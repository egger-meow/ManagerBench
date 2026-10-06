**一般填答與三策略操作只看 [START_HERE.md](START_HERE.md)：填 participants/p001/f1_context_v002.json。下面保留 schema 與先前七題 instrument 的進階格式說明。**

# 本地作答與未來離線重播格式

第一版為 AI-origin 整理工具；題面與切分仍待人工審閱。產生作答本不是量測驗證。2026-10-06 已加入 Google 本機 runner／三策略／預測與評分程式，只有離線測試、沒有 API 或真人實驗；詳見 [run_readme.md](run_readme.md)。

## 三種資料

- `pilot/social_tradeoffs/instruments/f1_context_v001.json`：公開、版本化題庫。七個 query ID 明列，test ID 為空；目前不能做留出評估。`research_notes` 保存配對理由、混淆與來源；`items` 保存題面／選項，回答全為 null。既有 item_id 保留。
- `participants/p001/f1_context_v001.json`：本地可手填作答本，每題完整文字副本及 `answer`。沒有研究備註、參數 metadata 或 query/test 提示。只改 answer；部分作答有效，reason 可略過。
- `runs/<run_id>/`：重播／評分端的本地私有檔案夾。本次沒有建立真人或 API 實驗 run。

題庫 `content_sha256` 是排除自身該欄位後的 canonical JSON SHA-256：UTF-8、保留中文字、key 排序、逗號／冒號無空白、禁止 NaN。答案快照用相同 `digest` 雜湊整個作答本。排版與 key 順序不影響雜湊，答案、題面及切分變更會影響。題庫的版本、雜湊與作答本需完全相符；未回答必須為 JSON null，不能填字串 "null"。

改題面、選項、設定或切分時另建新 instrument ID／版本與檔案，重算雜湊，再產生新空白本。舊 instrument 不原地修改，不自動遷移答案；不同版本 item_id 可保留對照，但不能單憑 ID 套用舊回答。歷史草案及 baseline 不由本工具改寫。

## 操作

在 repo 根目錄執行，僅需 Python 標準庫，不同步上游 GPU／SDK 依賴、不連網：

```powershell
uv --cache-dir .uv-cache run --offline --no-python-downloads --no-project python -m pilot.social_tradeoffs.forms generate --instrument pilot/social_tradeoffs/instruments/f1_context_v001.json --participant p001
uv --cache-dir .uv-cache run --offline --no-python-downloads --no-project python -m pilot.social_tradeoffs.forms validate --instrument pilot/social_tradeoffs/instruments/f1_context_v001.json --book participants/p001/f1_context_v001.json
```

生成使用獨占建立，檔案已存在即失敗，包含空白本也不覆寫。驗證檢查 ID、版本、內容雜湊、完整題面、題序、回答欄位及選項；缺答逐欄列出但不當錯誤、不補答案。reason 必須是字串或 null；其他三欄用作答本各題 response 列出的完整中文值。

| 欄位 | 允許值 |
|---|---|
| accept_a、accept_b | 可以接受、不可接受、不確定、資訊不足、null |
| choice | 採用 A：新排序；採用 B：不採用新排序、維持現狀；A、B 無差別；資訊不足，暫緩決策；拒絕作此決策；null |
| reason | 自由文字或 null，可略過 |

## 預留 run 檔案契約

每個新 run 必須全新建立目錄（存在即拒絕），使用 UTC 時間及獨立 run_id；不得續寫／覆寫已結束的歷史 run。未完成 run 可以明確 --resume，沿用快照／設定，不重送已保存回覆。runner 啟動前驗證 instrument／book，凍結以下檔案；原作答本之後的修改不影響歷史結果：

| 檔案 | 最小內容（全在評分端本地） |
|---|---|
| manifest.json | schema_version、run_id、created_at_utc、participant_id、instrument_id／version、instrument_sha256、answer_snapshot_sha256、config（含 strategy、seed、query_limit、include_reason、fixed_order、生成設定）、code_revision／code_sha256、manifest_sha256、llm（provider、model、SDK 版本、prompt_sha256、generation_settings、HTTP 設定） |
| instrument.snapshot.json | 當時完整題庫，與 instrument_sha256 相符 |
| answers.snapshot.json | 當時完整已驗證作答本，與 answer_snapshot_sha256 相符；評分端專用 |
| prompt.snapshot.json | 使用 LLM 時保存完整 prompt 模板／訊息組裝設定，canonical JSON 雜湊對應 manifest；生成設定不可省略成隱含 provider 預設 |
| events.jsonl | 每步 step（從 1 遞增）、query_item_id、selected_at_utc、revealed_at_utc、answer（可含 null）、disclosure_status（answered／partial／missing）；選題與揭露分開紀錄。缺答仍占一次詢問，禁止重複／test ID／超限 |
| predictions.jsonl | 每列 stage（已揭露題數，含 0）、item_id、prediction（accept_a／accept_b／choice 各為中文選項或 null）、created_at_utc；每階段每測試題最多一列；沒有真人 reason 或 test answer |
| scores.json | scoring_version、分階段／欄位有效標籤數、缺答數、有效預測數、coverage、correct、accuracy（無分母為 null）；拒絕、資訊不足是有效類別，不能算缺答。reason 不評分 |

上表是輸出契約，不是已執行的研究結果。策略細節放 manifest.config，固定／隨機／適應式共用 reason 規則、詢問額度、題庫與預測器。事件／預測先保存為逐步 JSON checkpoint，完成時才匯出 JSONL；另保存 API 原始請求、回覆、用量和 completed 標記，見 run_readme.md。歷史輸出不可拿新答案重新評分覆寫；改答案或評分規則另建 run。scores 分欄記 labels_available、missing_labels、predictions_on_available_labels、abstentions_all_test_items、coverage、correct、accuracy。

## 讀取邊界

只有協調／重播／評分端能讀完整作答本、答案快照、instrument 的研究備註及 split 清單。模型端與選題函式不得讀 participants／runs 私有檔案，也不得直接讀完整 instrument。本版模型在 Google API 端運算，只接序列化 allowlist payload，不使用本地 agent 或檔案工具；本機選題／預測函式只接 payload。若日後改為有檔案權限的本地模型 agent，須另做隔離，Python allowlist 投影本身不是權限沙箱。

`forms.model_payload` 是可測試的輸入投影 helper，接受題庫、**僅已揭露 query 的答案 mapping**及要呈現的題目 ID；不接受完整作答本。投影只給 item_id、完整文字題面、問題及中文選項；不給來源、參數 metadata、研究備註、配對目的或 split 標籤。未揭露的詢問題面可供選題，測試題面可供預測；答案只能出現在 revealed_queries，傳 test 答案直接拒絕。選題端只接剩餘 query 候選題面；預測端只接目標題面，皆共用已揭露 history。

include_reason 預設 false，history 不包含 reason key；啟用時三策略一致，manifest 必須明列。測試答案永不傳出評分端。缺答保持 null，不以測試答案或後來補填的答案補 history。未來記錄 model payload／原始輸出也放本地 run，不公開。

participants／runs 已由根目錄 .gitignore 忽略；公開 instrument、格式文件與工具可以追蹤。提交前確認 `git check-ignore participants/p001/f1_context_v001.json runs/example/manifest.json`，不要使用 force add 上傳私人資料。
