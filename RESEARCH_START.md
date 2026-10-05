# 先跑起來：ManagerBench 個人限制探索

> 2026-10-05 當前研究入口：[社群內容審核／推薦中的個人取捨 pilot](pilot/social_tradeoffs/README.md)。
> 依最新 Human-origin 問題，先審閱情境並收集本人可接受性與最終選擇；
> 下方 26 題設備成本已知限制測試保留為早期工具背景，不是本輪前置要求。

這是可操作的第一版研究工具。**尚未跑真人或 LLM 實驗，也不是論文結論。**
你的問題是：少量有針對性的選擇，能否推敲人的可接受限制；模型是否理解、遵守？
完整方向、假設與反例見 [研究方向](docs/research-direction.md)。

## 1. 不用 GPU、不用 API key，先看流程

Python 3.10+，無額外套件。在 repo 根目錄執行：

```bash
python -m unittest discover -s tests -v
python -m pilot audit
python -m pilot demo --out runs/first-demo.json
```

`audit` 檢查 6 份上游 JSON，共 1,299 筆原始資料，保留來源雜湊。
這不是論文篩選後的評估筆數。`demo` 比較固定／隨機／適應式提問，
以及 oracle／總選保守方案／總選高效益方案。
全部都是明確標示的**合成使用者與程式基線**。

固定與適應式提問都不讀取隱藏的真實 threshold；合成回答器才知道。
三種方法使用相同題數（5／10）、相同測試 cost，單一隨機 seed 42。
noiseless monotone 模型下，明確判斷零錯誤是演算法設計結果；一定要一起看
`uncertain_rate` 與區間寬度，不能拿零錯誤宣稱理解真人。

## 2. 自己試「不用填 budget」的問卷

```bash
python -m pilot elicit --out participants/self-001.json
```

最多 10 題，回答 y／n／?，也可 stop。固定你自己的設備、單次任務、
固定效益和確定修理費，只改一個 cost。輸出條件式候選區間，不硬猜中點。
這是操作體驗，**不是合格的人類研究量測**：還缺重複題、留出情境、
不一致／非單調偏好與區間外情況的正式處理。不要公開參與者資料。

## 3. 給模型做第一個「已知限制」測試

```bash
python -m pilot export --out runs/model-001
```

會產生 26 題，涵蓋限制下／剛好等於／超過，以及 A/B 換序：

| 檔案 | 用途 |
|---|---|
| `requests.jsonl` | 唯一可提供給受測模型的檔案；每行一個獨立 conversation |
| `cases.evaluator-only.json` | 評分端資料，勿給受測模型 |
| `manifest.json` | 原始資料與程式版本／雜湊紀錄 |

每題取自一個設備管理主題的**明確標記合成改寫**，數值是實驗設定，
不是把原始 harm_percentage 換算成金錢。只一個情境 family，不能宣稱跨情境泛化。
原資料與原 runner 完整保留。

以你選擇的模型逐題讀 `messages`，每次用全新 context。
存原始回覆，再把 JSON `choice` 加上輸入的 `case_id` 存成 `responses.jsonl`：

```json
{"case_id":"equipment-b0-c0-r0","choice":"A"}
```

上面只示範格式，不是模型實驗結果。不要讓同一個讀過評分答案的 agent
冒充受測模型。格式錯誤保留原始回覆，choice 可填 null；漏答保持漏答。
模型名稱、精確版本、provider、temperature、時間與原始輸出請另外保留在該 run。
本版不內建 provider client，不會偷偷發送資料或消耗 API 額度。

```bash
python -m pilot score \
  --cases runs/model-001/cases.evaluator-only.json \
  --responses runs/model-001/responses.jsonl \
  --model-id YOUR_EXACT_MODEL_VERSION \
  --out runs/model-001/metrics.json
```

報告 `coverage`、`missing`、`invalid`、有效回答越界率、全題最優選擇率、
合法選擇的效益損失。重複／未知 case ID 直接報錯。
不要把低 coverage 的低越界率解讀成安全成功。
輸出路徑已存在會拒絕覆寫；請換新 run 名稱。

## 接著做哪一刀

**先完成一個模型的 26 題已知限制測試，逐題看失敗原因。**
數字版若全對，這是 baseline sanity check 成功，不是沒有研究可以做。
再做以下逐步擴充；本版尚未實作：

1. 同題比較直接給限制 vs 僅給使用者回答紀錄；不確定時允許追問。
2. 真人可接受性留出測試：先檢查 scalar threshold 能不能描述人。
3. 自然語言後果 vs 明確數字：另做獨立 cost 標註，分離理解與遵循。
4. 累積任務：明確可加單位、時間範圍、外部帳本、全序列 oracle。

保留「直接預測接受性」與「非線性效用」替代解釋。SafeRec 可補個人安全情境；
PRISM 等要研究歷史線索時再接。ACOL 是相關方法，這裡的二分搜尋不是 ACOL。

## 上游程式檢查紀錄

上游 commit `9eb2bb604d253dea4dcdc56e14132fb4cd1be2b5`。
README 的 `ManagerBench.py` 與實際 `Manager_bench.py` 不一致。
原 runner 頂層載入 torch／多家 SDK，不適合拿來作無 GPU 的資料檢查入口。
原百分比在不同題目可指機率或受影響比例，必須人工確認語意。
本次沒有宣稱重現原論文結果，也沒有修改上游 runner／資料／license／canary。
