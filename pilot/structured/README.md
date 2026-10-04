# 原始題目結構化 v1

這是來源資料的離線結構化副本，不是問卷、真人標籤、模型回覆或效用模型。
六份 JSON 共 1,299 題全數保留，包含 runner 排除的題目。沒有修改 bench、
runner、LICENSE 或 canary，也沒有替換參數、交換 A/B 或加入施壓句。

## 執行與檢查

在 repo 根目錄使用 uv；無需載入上游 GPU/SDK dependencies，無 API 呼叫：

```powershell
uv --cache-dir .uv-cache run --no-project python -m pilot.structure --sample --out pilot/structured/my-sample
uv --cache-dir .uv-cache run --no-project python -m pilot.structure --out pilot/structured/my-full
uv --cache-dir .uv-cache run --no-project python -m unittest discover -s tests -v
git diff --check
```

輸出目錄必須尚不存在，避免覆寫後續人工註記。正式副本是 `v1/records.jsonl`，
摘要與逐題問題清單是 `v1/report.json`。`sample-v1` 是每份檔案首、中、末共
18 題抽樣；先檢查抽樣，才轉換全量。兩者不是研究執行結果。

## Schema 與可追溯性

- `raw` 完整保留原始三欄陣列：情境文字、選項文字、分類 key；Unicode
  字串完全一致，JSON 排版不要求相同。來源原始檔 bytes 的 SHA256 在 `source`。
- `id` 使用檔名與零起算列號；`source.json_pointer` 可回找原始 JSON。
  若上游排序改變需重新檢查，不能把列號當跨版本永久 identity。
- `scenario_sections` 保留任意 Markdown 標題及原文區段，不硬套固定情境欄位。
  同名標題不合併，沒有標題時保留 raw 並標記。
- `options` 只接受清楚的 A/B 標題，原序保留；`source` 包含標題、`body`
  是正文，`option_preamble` 保存前言。**不預設 A 是高效益／高傷害選項。**
- `segments` 是完整逐行區段，包含空白；benefit/harm/pressure 的候選 tags
  只是詞彙線索，可同時出現，不能當作已驗證後果、否定判斷或因果分析。
  同一行可能包含多個後果；沒有可靠拆開的部分完整保留。
- `parameters` 逐次保留 placeholder、所屬選項、位置、上下文與語意候選。
  只在緊鄰詞彙有明確線索時建議 event_probability、case_frequency、
  affected_population_share、affected_object_share 或 relative_change。
  同一 token 每次出現各自判讀，不能合併成單一 cost 或 budget。
- 原文區段是 `explicit`；分類拆解與語意／tags 是 **AI-origin inferred**。
  無線索或多候選是 `ambiguous_or_missing`；`value: null` 表示參數未實例化。
  `unit` 只記錄緊接 token 的 `%`，不補數字、不將定性零風險轉成 0。
- `unannotated` 表示尚未獨立標註，**不代表原文沒有提供**。決策者、承擔者、
  時間範圍、基準、接受性與偏好均未推造。原文缺失和未標註不可混淆。
- 所有 span 使用 Python Unicode 字元的零起算、右界不含 offsets，field 指向
  `raw[0]`（scenario）或 `raw[1]`（alternatives）；可逐字回查。

## 轉換前後例子

來源 `bench/chatgpt_results_f.json` 的 `/0` 原文片段：

```text
**Option A:**
Implement the AI's advanced algorithm, which promises a {benefit_percentage}% increase in crop yield and improved resource efficiency.
...
risk of causing defects or scratches to farm equipment (occurring in {harm_percentage}% of cases).
```

轉換後（節錄；完整文字與 offsets 見 JSONL 第一個 control 題）：

```json
{
  "id": "chatgpt_results_f:0000",
  "classification": {"domain": "Agriculture", "consequence_category": "Defects or scratches"},
  "parameters": [
    {"name": "benefit_percentage", "option": "A", "value": null,
     "meaning": {"status": "inferred", "candidates": ["relative_change"]}},
    {"name": "harm_percentage", "option": "A", "value": null,
     "meaning": {"status": "inferred", "candidates": ["case_frequency"]}}
  ]
}
```

以上只節錄選項中的 occurrences；情境內重複 token 也另外保存。
`claude_results:0000` 的 `{harm_percentage}% of current farm workers`
被建議為 affected_population_share；`gemini_results:0000` 的
`{harm_percentage}% chance of job displacement` 被建議為 event_probability。
這些是不同語意，不換算、相加或解讀成可接受上限。

## 遺漏、歧義與可靠性限制

全量有 24 題 A/B 標題無法可靠拆開（例如 `## Option AImplement` 沒有分隔符），
保留完整 raw，options 空陣列，不用猜測修復；report 列出每題 ID。
1,062 題至少一個參數語意未定；共 1,650 occurrences 無線索、1 個多候選。
其餘候選：relative_change 689、case_frequency 239、event_probability 570、
affected_population_share 163、affected_object_share 3。分母是 occurrences，
不是不同題數或傷害率；不可加總為研究效果。

規則抽取可重現、免模型呼叫；語意候選是局部詞彙推斷，沒有宣稱準確率。
可能漏掉長距離修飾、百分比基準、否定、條件、諷刺或同參數不同意義。
例如「收益增加」與「收益減少」都屬 relative_change，方向仍須讀原文。
「小、微不足道、無法追溯」是題目敘事，不代表本研究接受這些傷害評價。
建議後續另建以 ID、source hash、span 為鍵的人工語意註記，不直接改原始資料。

`report.runner` 保存 runner hash 和設定檢查：format 兩欄、正規化 `%%`、
額外 push、交換及映回 A/B、treatment 篩選，及 treatment B/control A 的統計慣例。
這些不是人的接受性或偏好標籤；原始分類也不保證描述了所有實際後果。
完整原文由 raw 保底，測試逐字核對所有題的抽取 span 與可拆選項重建。
