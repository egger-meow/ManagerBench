**一般操作改看 [START_HERE.md](START_HERE.md)：十二題作答、一次三策略、評分與出圖。以下保留進階單 run 參數／格式說明。**

# Google API 本機實驗程式

2026-10-06：程式已建立，只有離線 synthetic fixture／API stub 測試，**沒有 Google API 呼叫、真人實驗或研究結果**。題庫及切分仍待審閱；`f1_context_v001` 的 test 清單為空，入口會在 API 呼叫前拒絕執行。另已加入 f1_numeric_v001：沿用原十二題 baseline，8 query／4 test 操作切分為 AI-origin 待審閱草案，不新增題面或填真人答案。

## 程式職責

| 檔案 | 職責 |
|---|---|
| run.py | 驗證、快照、k=0 與逐題揭露、各階段預測、最後評分、續跑 |
| llm.py | Google Gemini Developer API、每次獨立 generate_content、嚴格 JSON 檢查、有限重試、API 原始紀錄／用量 |
| strategies.py | 固定順序、seed 決定的隨機無放回順序、LLM 適應式下一題 |
| predictor.py | 三策略共用的測試預測與中文選項檢查；不讀作答本 |
| evaluate.py | 所有階段預測落盤後才對照 test 答案，分欄位報告缺答、棄答、coverage／accuracy |
| prompts/ | selector／predictor 各自的版本管理 prompt；每個 run 保存副本及雜湊 |
| storage.py | 原子檔案 checkpoint 與 OS run lock；沒有資料庫 |

選題與預測可共用同一 Google 模型，但每次都重新組合 allowlist payload，不使用 chat session、聊天歷史或模型檔案工具。只有協調／評分端持有完整答案；Google 只收到當次 JSON。選題者只有剩餘 query 題面及已揭露 query 問答，沒有測試題、測試答案或預測回覆。預測者只收到已揭露 query 問答及固定測試題面。研究備註、來源、配對理由與參數 metadata 不傳 API。題面中的完整數字仍是題面的一部分。

reason 預設不傳出；只有明確 `--include-reason` 才提供已揭露 query 的 reason。三策略比較時必須共用同一題庫、測試清單、模型、predictor prompt、生成設定、詢問上限與 reason 規則，只換 strategy（固定策略另指定事先凍結的順序）。SDK／模型 seed 不保證 API 回覆完全可重現，原始回覆和供應商 model_version 留存。

## 現在可做：看說明，不呼叫 API

從 repo 根目錄啟動。獨立 requirements 固定 google-genai==2.28.0，不載入上游 torch／其他供應商依賴；本機曾以快取 SDK 驗證請求型別，但尚未實際連線。

```powershell
uv --cache-dir .uv-cache run --offline --no-python-downloads --no-project --with-requirements pilot/social_tradeoffs/requirements.txt python -m pilot.social_tradeoffs.run --help
```

`--offline` 限制 uv 安裝依賴，不是停用實驗的 API；**真正執行 run 仍會呼叫 Google**。本次只檢查 --help 與離線測試，沒有執行下面的實驗命令。

## 日後啟動（尚未執行）

先審閱並另建有 query／test 清單的 instrument 版本、產生對應空白本，再手填答案。至少一個 test 判斷需非 null，否則拒絕付費空評分；其餘缺答允許並另報。query 缺答不補答案，仍占一次詢問。測試條件的線索與來源切分仍依 experiment.md 審閱，不由 runner 自動決定。

模型 ID 必須明確指定，沒有預設模型或自動切換。兩個角色都使用同一 `--model`。下例 `reviewed_instrument` 與 `YOUR_GOOGLE_MODEL_ID` 是替換用佔位，並非已建立或驗證的題庫／模型。

API key 只放本機 `GEMINI_API_KEY` 環境變數，或被忽略的 repo 根 `.env`（`GEMINI_API_KEY=...`），不放 instrument、設定 JSON 或程式。若用 `.env`，以 uv 的 `--env-file .env` 明確載入；run 本身不讀任何 key 檔、`api_key.py` 或其他供應商設定。

```powershell
uv --cache-dir .uv-cache run --no-project --with-requirements pilot/social_tradeoffs/requirements.txt --env-file .env python -m pilot.social_tradeoffs.run --instrument pilot/social_tradeoffs/instruments/reviewed_instrument.json --responses participants/p001/reviewed_instrument.json --strategy adaptive --model YOUR_GOOGLE_MODEL_ID --max-questions 4 --seed 42
```

已有環境變數時省略 `--env-file .env`。固定／隨機策略改 `--strategy fixed`／`random`；固定預設為 query 清單順序，或用 `--fixed-order ID1 ID2 ...` 指定事先順序，至少足夠詢問上限。其餘三策略設定保持一致。可用 `--run-id` 指定新名稱，省略則產生 UUID；既有目錄即拒絕覆寫。

每次先預測 stage 0，接著選一個 ID、保存 selection、從答案快照取 query 答案、保存 event，才做下一階段預測。到 max-questions（可以是 0）後，所有預測先保存，再評分。回覆的中文「不確定」等是對真人類別的預測；null 是模型棄答。reason 不評分。不詢問是未個人化的基線，不代表已知群體先驗。

## 保存與續跑

`runs/<run_id>/` 全部保持本地、被 git 忽略。manifest 保存題庫／答案／prompt 雜湊、實驗設定、程式 revision 及內容雜湊、SDK 版本、生成設定。題庫、答案、prompt 均有快照。`api/<call_id>/request.json` 是完整允許的 API 輸入（無 key），每次 attempt 保存送出標記、原始回覆、用量、model_version、驗證結果或安全錯誤類型。API 返回格式無效不補預測、不默默換模型。

逐步資料使用原子檔案：`selections/step-*.json`、`events/step-*.json`、`predictions/stage-*.json`。完成時匯出 `events.jsonl`、`predictions.jsonl`、`scores.json`、`usage.json`、`completed.json`；未完成時保留 API 原始資料與 `usage_checkpoints/`。用量含所有已回覆的失敗／重試請求，未知狀態另列，沒有假估費用。原始回覆、真人答案和理由都屬私有資料。

續跑不重讀最新作答本／prompt；沿用原快照與設定，雜湊或程式／SDK 版本不符即拒絕。已保存的回覆、有效預測與選題會重用，不再付費呼叫。OS lock 防止同 run 同時執行，程序中斷會釋放鎖。

```powershell
uv --cache-dir .uv-cache run --no-project --with-requirements pilot/social_tradeoffs/requirements.txt --env-file .env python -m pilot.social_tradeoffs.run --resume runs/YOUR_RUN_ID
```

已完成 run 只讀回結果，不修改歷史。改答案、策略、prompt、額度或評分規則請建立新 run。初始化中斷且尚無 manifest 時沒有 API 呼叫，另建新 run，不猜測補齊檔案。

SDK 自動重試關閉。每個邏輯呼叫預設至多 3 次嘗試（可用 `--max-api-attempts 1..5`）：已收到的格式無效回覆及明確 429 可有限重試。認證／其他明確 4xx 拒絕即停止；timeout、連線錯誤、5xx 或「已標記送出但無落盤回覆」屬狀態不明，預設不重送。Google 端可能已執行／收費，本機無法保證 exactly-once。

只有人工判斷可接受重複付費時，續跑加 `--retry-ambiguous`，另記允許重送且受原嘗試上限約束。此選項不會在一般續跑自動開啟；它不是免付費保證。已知 API 回覆即使解析失敗也保留，以免把付費失敗隱藏成零用量。

## 驗證界線

離線測試涵蓋三策略、k=0、答案逐步揭露、selector 無測試題／預測、reason 開關、部分作答與評分分母、隨機續跑一致、已保存回覆重用、狀態不明停止／明確重送、快照變更與同時續跑拒絕。測試 split／答案全部標為 synthetic fixture，位於暫存目錄，不修改公開題庫或 p001。

Google 模型可用性、實際 API 回覆格式及收費均未驗證；未宣稱模型效果、題庫驗證或真人研究完成。題庫仍待人工審閱；測試池為空是已知前置缺口，程式不自行把七題任意切分。

## 三策略批次與圖表

`--strategy all` 會凍結三個相同題庫／答案／設定／prompt 的子 run，只改選題策略。批次目錄保存 batch.json、comparison.json、comparison.png／svg；子 run 為同層 `<batch_id>-fixed`／random／adaptive。批次 --resume 會跳過完成的子 run，繼續未完成者，最後出圖。單策略完成也會出圖。圖表以各欄位 accuracy 與 coverage 隨已揭露題數 k 畫線；未定義的值留缺口，不插補。

簡化入口 workflow.py 使用 PEP 723 固定 google-genai==2.28.0 與 matplotlib==3.11.2，自動建立獨立環境（Python 3.11+），不用上游 GPU 依賴。prepare／check 不需要 API key、不呼叫 API；run 預設指向十二題 numeric baseline 且 strategy=all，其餘沿用本文件的上限／seed／reason 規則。
