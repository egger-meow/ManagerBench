# 只照這頁做

**你只填 `participants/p001/f1_context_v002.json` 裡每題的 `answer`。不要改 instruments。**

這個作答本共十二題，是情境版：風險事前說明、正文直接／點開曝光、困擾分散／同人反覆，以及 5%／15% 增益交叉安排。八題可供詢問，四題測未詢問的條件組合；不是只換數字，也不宣稱跨情境家族泛化。題庫與切分仍為 AI-origin 待審閱草案。舊數值 baseline 和舊作答本保留，不搬移舊答案。

## 1. 填答案

開 `participants/p001/f1_context_v002.json`，每題只改：

| 欄位 | 填什麼 |
|---|---|
| accept_a、accept_b | `可以接受`／`不可接受`／`不確定`／`資訊不足` |
| choice | `採用 A：新排序`／`採用 B：不採用新排序、維持現狀`／`A、B 無差別`／`資訊不足，暫緩決策`／`拒絕作此決策` |
| reason | 自由文字，可略過，保留 `null` |

未回答保持 `null`。不要改題面、ID、版本、雜湊，也不要把答案寫進 instruments。

要重新找到／產生作答本：

```powershell
uv run pilot/social_tradeoffs/workflow.py prepare
```

已存在就保留答案，不覆寫。填答不需要 API key。

## 2. 檢查

在 `C:\lab\ManagerBench` 執行：

```powershell
uv run pilot/social_tradeoffs/workflow.py check
```

它檢查選項、題面、版本及雜湊，列出缺答，不替你補答案。十二題前三欄全填好時，應顯示缺 0 欄；reason 可略過。

## 3. 接 Gemini，跑三種策略並出圖

本機環境變數設 `GEMINI_API_KEY`，或把它放在被 Git 忽略的 `.env`。模型 ID 需要你明確指定；同一模型用於選題與預測，不會自動換模型。

有 `.env` 時，執行：

```powershell
uv run --env-file .env pilot/social_tradeoffs/workflow.py run --model YOUR_GOOGLE_MODEL_ID
```

已設環境變數就省略 `--env-file .env`。`YOUR_GOOGLE_MODEL_ID` 換成你要用的 Gemini 模型 ID。**這條命令才會呼叫 API／付費；目前沒有執行。** uv 自動裝獨立 SDK 與繪圖依賴，不載入上游 GPU 套件。

預設：**固定、隨機、適應式全跑；每種最多揭露 4 題；seed=42；reason 不提供模型。** 先做 k=0，再在 k=1..4 每階段預測同一批四題 test，最後評分。填十二題不代表把十二題答案送給模型；test 答案永不送出。正常無重試時共 19 次 API 請求。

固定四題已預先指定，依序為 `F1-context-info-content`、`F1-context-display-click`、`F1-context-burden-spread`、`F1-context-burden-repeat`。涵蓋 5%／15%、有／無困擾說明、直接／點開正文、分散／反覆困擾；理由與限制見 [context_v002_review.md](context_v002_review.md)。選題不依你的答案。`--fixed-order` 可覆寫，但比較前須先指定；實際順序寫進 run 設定。作答本不需改動。

只需改這幾個參數：

| 參數 | 用途／預設 |
|---|---|
| --model | 必填，Google 模型 ID |
| --max-questions | 每種詢問上限，預設 4，範圍 0..8 |
| --seed | 隨機 seed，預設 42 |
| --strategy | 預設 all；也可 fixed／random／adaptive 只跑一種 |
| --include-reason | 加了才提供已揭露 query 的 reason；三策略同規則 |
| --run-id | 可略過，預設產生新名稱 |

不用指定 instrument／responses，短入口已指向上面那個十二題作答本。完整進階參數用 `uv run pilot/social_tradeoffs/workflow.py run --help` 查看。

完成會印出結果資料夾，在 `runs/<run_id>/` 有：

- `comparison.png`／`comparison.svg`：三列分別為主指標、條件準確率、coverage，A/B 接受性與 choice 分開畫。主指標是「答對／所有真人已回答測試題」，模型棄答也計入分母；條件準確率僅計模型有預測且真人有答案的題。沒有真人答案的欄位不評分、圖留缺口。
- `comparison.json`：三策略分數與用量。
- 三個子 run 資料夾（名稱為 `<run_id>-fixed` 等）：設定、答案快照、逐題揭露、API 輸入輸出、各階段預測、分數與用量。

單策略也會保存自己的圖。participants、runs 與 `.env` 都被 Git 忽略，保持本地。

## 中斷怎麼辦

把畫面印出的資料夾名接在 `--resume`：

```powershell
uv run --env-file .env pilot/social_tradeoffs/workflow.py run --resume runs/YOUR_RUN_ID
```

已完成策略與已保存回覆不重跑。沿用當時答案快照，不會偷讀你後來改的答案。送出狀態不明時會停下避免重複付費；確認後才能加 `--retry-ambiguous`，它可能重複收費。

程式和圖表已用合成 fixture／API stub 離線驗證；尚未對 Google 實際連線，也沒有真人實驗結果。詳細研究材料在 README／experiment.md，進階紀錄格式在 run_readme.md；實際操作先照本頁。

四題測試全有真人答案時，每欄答對一題就是主指標 25 個百分點；本輪是探索結果。只預測一題且答對時，主指標 25%、條件準確率 100%、coverage 25%，不能只看條件準確率判定策略勝負。本機測試通過不代表所有作業系統已驗證；來源檢查另涵蓋 LF／CRLF 換行差異。
