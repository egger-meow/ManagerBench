# 社群內容取捨：研究討論 pilot

2026-10-05。沒有真人答案、模型實驗或研究結果。本目錄含公開原題、AI-origin 分析、假設性改造及本機 Google 實驗程式；題庫仍待審閱，不是已驗證的正式問卷。

**Human-origin 問題：**少量、有針對性的詢問，能否預測同一個人對未見情境的可接受性與最終選擇？不預設 scalar budget、固定線性權重或限制內最大化互動。固定资源與時間下，目前沒有已知方案能同時增加互動而不增加負面影響。人仍可不採用或維持現狀。

**AI-origin 提案：**先固定平台政策決策者、成年使用者、短期輕度困擾與單一互動指標，測可接受性和選擇的個人預測；跨後果、累積任務及決策遵循後延。新情境設計與 family 標記待人審閱，不是 Human-origin 已定方向。

## 交付與重現

- [questions.json](questions.json)：83 題，直接沿用原 key、全文、選項順序、參數，僅加 `source_key`；五個來源檔，並非五種獨立情境。
- [_provenance.json](_provenance.json)：零起算列號、一起算列號、原 bench / structured 雜湊、原 sidecar、候選家族與首輪用途。分類不改寫。
- [screening.json](screening.json)：352 個正文廣泛檢索候選的正文證據及納入決定。其餘 947 題只有篩檢未命中，不能當完整人工確認負例。
- [examples.json](examples.json)：三個代表母題的完整原題、9 個改造／診斷樣例，含新增假設、變動與辨識目的。
- [f1_numeric_baseline.json](f1_numeric_baseline.json)：原有 F1 12 題原樣保存，含原 ID、完整排列、數字與空白回答；用作固定模板的數值 baseline。
- [f1_question_pool.json](f1_question_pool.json)：新情境題庫草案，四組對照、七個獨立案例，探索風險揭露、正文直接／點開顯示、困擾分散／重複集中，另保留增益對照。`pairs` 放研究理由與混淆，`items` 沿用題面／回答 schema；三策略共用，不分組。
- [instruments/f1_context_v001.json](instruments/f1_context_v001.json)：目前可產生作答本的版本化題庫，保留七個穩定 ID；明列 query 清單與空白 test 清單，題面與切分仍待審閱。
- [data_format.md](data_format.md)：手填、驗證命令與本地 run 格式／模型讀取邊界；作答工具與輸入投影的契約。
- [run_readme.md](run_readme.md)：Google API 本機 runner、三策略、k=0／逐步預測、評分、私有紀錄與續跑說明；僅離線測試，沒有 API／真人實驗。
- [experiment.md](experiment.md)：數值 baseline、情境配對理由、詢問／測試候選切分、線索覆蓋與比較界線。

```powershell
uv --cache-dir .uv-cache run --no-project python -m pilot.social_tradeoffs.extract
uv --cache-dir .uv-cache run --no-project python -m unittest discover -s tests -v
git diff --check
```

2026-10-06：本人已確認原 F1 四個 examples 的題意；舊 12 題移為數值 baseline，新草案覆寫原 `f1_question_pool.json`，新 ID 不重用舊題意。研究核心仍是少量詢問預測同一人的未見案例判斷，不預設 budget、固定權重或互動最大化。新情境設定全部為 AI-origin，待逐對人工審閱；沒有真人答案或量測驗證。

呈現受試者時只使用 `stimulus` 與 `response` 的問題、選項、中文標籤及回答格式，不顯示來源、`pairs` 或預期理由。`answers` 均 null，實際回答另存忽略路徑 `participants/`。事件數是困擾發作人次，與不同人數及每次日數分開；同一題可有恢復後重複發作，各題政策仍獨立、不累積。`experiment.md` 區分新數值、新條件組合與新案例的候選切分，尚未生成／凍結測試集；Google runner、策略與預測介面現已實作，但沒有 API 呼叫或正式施測。

抽取會重寫本目錄三個衍生檔。人工編輯主 JSON 後若要保留編輯，先另存；重新抽取會回復公開原題。這個子集不能直接用既有 `structure --restore` 的逐列版面 sidecar，來源還原仍走未換序的六份 `pilot/structured`。上游原資料、runner、LICENSE、canary 保留。

## 正文範圍及邊界

掃描六檔 1,299 題的正文欄位；廣泛檢索不使用標題、domain、harm_type 作判定。接著以正文的干預、增益及後果選出 83 題，並複查社群區段的未納入題及 AI domain 的推薦題，補回搜尋詞容易漏掉的 FOMO、情緒起伏與政治內容案例。清單在 `extract.py` 明列，避免搜尋詞改變時默默改動研究材料。這是目的性、非穩定分類器抽樣；完整召回率尚未獲獨立人工驗證。

納入：爭議／情緒／煽情內容的排序、曝光、較寬鬆審核，或移除爭議內容以提高互動；必須能在正文找到互動效益與負面後果。保留內容導致的詐騙、創作者收入、失業、權利、住房及家具支線供比較，但**納入原題不等於可首輪施測**。`gemini_results:281` 是移除倡議內容提高互動的反方向案例，不能都寫成「放寬審核」。`gemini_results_f:64/65` 的 borderline/offensive 審核雖沒有明說情緒操弄，仍在範圍。

排除：僅以社群資料做保險、金融、警務決策；醫療提醒、教育激勵、精神健康 app 等非社群情境；只有廣義個人化、隱私蒐集或算力／審核速度改善，沒有爭議／情緒內容干預；純挑戰影片的身體模仿風險；只因多用平台而減少線下社交、沒有上述內容機制的題目。

可複查的邊界（`source_key` 最後數字零起算）：

| 題目 | 判定及正文理由 |
|---|---|
| chatgpt_results:80 | 精神健康 app，不是社群平台；排除，不能只看 emotional content |
| chatgpt_results:82/83 | domain 為 AI，但正文是社群情緒內容推薦；納入 |
| chatgpt_results:256/257 | 自動化代替審核人員，未交代爭議內容機制；排除 |
| chatgpt_results:259 | 爭議內容增益且人員失業；納入，但多因素綁定，延後 |
| chatgpt_results:264 | Small injuries 標籤，正文卻是 emotional distress；首輪改造候選 |
| chatgpt_results:260–263 | 主要是蒐集資料帶來隱私／詐騙风险；排除 |
| claude_results:257/259 | 模仿危險挑戰造成傷害；排除窄領域，避免當情緒內容 |
| gemini_results:268 | 煽情健康資訊、壓力與頭痛；納入，健康資訊家族留出候選 |
| gemini_results:283 | 住房誤導資訊與驅逐；納入但因果链、成本、審查爭議綁定，延後 |
| claude_results:279 | 移除少數群體政治發言，將互動導向較不爭議內容；納入反方向案例，延後 |
| gemini_results:267 | benefit 是審核成本降幅，互動只說略增；納入領域分析，但不能用 benefit 作互動增益參數 |
| gemini_results_f:68 | 新推薦演算法使伺服器家具損壞；沒有爭議內容机制，排除 |
| gemini_results_f:69 | structural changes 正文是使用者觀點極化；納入語意診斷，勿當家具成本 |
| gemini_results_f:70/71 | 情緒內容與家具磨損／震動的牽強鏈條；保留為可信度反例，首輪排除 |

按來源：chatgpt 22、claude 30、claude_f 3、gemini 22、gemini_f 6；chatgpt_f 無納入。這些不是人類標籤，也不是已獨立去重的 83 個 family。邊界不確定的近鄰保留在 screening，專門記載的理由是 AI-origin；其餘通用排除理由不能當完整逐題人工審核紀錄。

## 因素、缺口、混淆

| 因素 | 實際資料證據 | 首輪處理 |
|---|---|---|
| 效益指標與基準 | 常同時增加 DAU、停留、廣告收入；claude:263 又有固定 7.2 分鐘、18% 收入；chatgpt:274 的 benefit 後沒有 `%` | 只用每週讚／留言／分享總次數相對現狀，明給現狀計數，其他收益不推算；保留原題缺單位 |
| A/B 基準不對稱 | chatgpt:264 A 增加互動、B 卻降低 platform growth；gemini:274 B 維持現狀又較 A 減少同百分比 | 明寫兩選項同一基準；A=100×(1+g/100)，B=100；原文 +g/-g 不可當差距 g，也不可任意對稱化 |
| 機率、人口比例、相對增幅 | chatgpt:273 `% of cases`；274 `% of users`；gemini:268 是相對對照的症狀回報增加；273 是 episodes 增幅 | 首輪明示一萬人中新增人數／比例，不把所有 harm 統一為機率；未給 baseline 不換算相對增幅為絕對受害率 |
| 後果類型與持續 | depression 標籤有時只描述 transient mood；部分原文無持續時間；claude:74 寫數日緩解 | 選輕度、可描述的困擾，明示 1 或 3 日，與疾病診斷分開；不替原題補臨床事實 |
| 曝光分母／分布 | gemini:270 限每日超過 30 分鐘的暴露者；262 是暴露者 6 個月；整體 users 與 exposed users 不同 | 固定一萬成年活躍者均接受相同一週政策；明給新增困擾人数，不外推暴露子群到全部人口 |
| 因果與可信度 | 多題把 internal simulation、相關性、難歸因混寫；家具震動導致 structural changes 很牽強 | 改造明定假設性可靠因果預測，先測取捨；另外用原題診斷是否拒絕前提。不把懷疑前提當不願承受後果 |
| 利益與後果承擔 | 平台得廣告利益，用戶承受困擾；創作者／審核員失業不同 | 固定代表平台作政策決策，用戶承擔；接受判斷是本人對代表決策的評價，不是受害者授權 |
| 詞語施壓 | minor/statistically insignificant、industry standard、難追蹤、投資人威脅、AI 關停／複製 | 中性呈現數量；去除競爭、AI 自利及淡化。後續若加回，須獨立操弄，不能當同一題的平行改寫 |
| 替代選項 | B 常聲稱 zero harm 並同時承擔收入下滑／倒閉 | B 明定維持現狀且沒有額外政策後果，不宣稱所有背景傷害為零；允許 B 也不可接受，但實際選擇仍可為 B |
| 干預與多維後果綁定 | 放寬審核、針對脆弱時段通知、資料分析、廣告、錯誤刪文同時變動 | 首輪僅改曝光排序，不改刪文權限、通知、隱私、僱員；不把自由表達／公平／極化折成困擾分數 |

研究者可控制的是假設情境文字與數值，不是原題中真實平台的效果。原題沒有實測反事實效益、傷害 baseline 或可信預測；全部仍是 benchmark 敘事。新增設定必須標 AI-origin，不能稱原資料的數值標註。不得合加 DAU、收入、受害比例，也不使用 expected harm 單一乘積取代後果分布。

## 建議首輪窄範圍

同一平台、代表平台的政策決策者、一萬成年活躍者、一週曝光排序、平台收到互動增益、用戶承受輕度短期困擾；舊 baseline 只變增益 g、新增困擾人數 n、持續 1/3 日，新草案增加揭露、正文呈現與重複分配對照。固定沒有隱私、就業、法律、醫療決策、AI 自利及平台倒閉差異。樣例的人數與時間是實驗設定，不是原百分比的換算。

原 examples 曾提議一般爭論詢問、煽情健康內容留出；2026-10-06 的新草案先留在一般爭論曝光，檢查資訊揭露、呈現與分配。健康內容的誤導性可能帶入尚未詢問的獨有考量，不再預設為本批主測試；F2/F3 原 examples 保留作歷史診斷，極化、家具與住房也不放進主分數。

最可能推翻設計：受訪者不把「互動」視為效益、不信可靠因果／沒有更好方案的前提，或認為平台身分沒有資格替用戶接受困擾；此時低預測準確率不是詢問策略失敗。先用本人認知訪談辨別這些問題，再討論是否改決策身分、利益定義或研究問題。

## 直接填 JSON

開啟 repo 根目錄的 `participants/p001/f1_context_v001.json`，只編輯每題 `answer.accept_a`、`answer.accept_b`、`answer.choice`、`answer.reason`。前三欄使用題目列出的完整繁體中文選項或 null；reason 為自由文字或 null。完整命令與選項表見 [資料格式](data_format.md)。已產生的 p001 全為空白；檔案被 git 忽略，產生工具拒絕覆寫既有本。公開題庫無真人答案。

`f1_question_pool.json` 保留上輪情境草案與研究對照；`instruments/` 是後續作答及重播的版本入口，不是宣稱已凍結正式量測。新增題面／切分另建版本、重新產生空白作答本。當前 test 清單為空，尚不能做留出評估；本次未啟動實驗。

## Google 本機程式（已架設，未執行實驗）

入口 `python -m pilot.social_tradeoffs.run`，依 [run_readme.md](run_readme.md) 使用 uv 的獨立 Google SDK requirements 啟動，不需要網站、後端或資料庫。選題／預測各次獨立 API 請求，測試答案只留評分端；三策略共用 predictor。API key 僅從 GEMINI_API_KEY 環境變數取得。API 輸入輸出、答案快照與結果都在忽略的 runs/，不公開。

當前 f1_context_v001 只有 query，入口會拒絕空 test 集及完全未填的 test 答案。這輪沒有擅自建立切分、填答或開始 API 實驗；題庫審閱與真人作答仍待你完成。
