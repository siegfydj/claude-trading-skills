# 美股看板：完整決策關卡繁中譯文

看板 JSON 的 steps 依原規格限 80 字並保留技能 ID，因此步驟使用精簡名稱／關卡摘要。此文件逐一保留原始 decision_gate 問題的完整譯文，不變更 JSON schema 或 manual_review 條數。

## W01

### core-portfolio-weekly

**步驟 2**（portfolio-manager）

配置檢視前，依 portfolio-manager/references/position-reconciliation.md，使用完整且同帳戶的券商與 ACTIVE／PARTIALLY_CLOSED 記憶快照執行 portfolio-manager/scripts/reconcile_positions.py。保留 JSON 及 Markdown 的 reconciliation_report。若 can_continue 為 false，或完整性、帳戶歸屬、時效性仍未確認，立即停止。確認相符後，產業及單一標的集中度是否在目標區間內？若否，交易者提出何種具體重新配置？

**步驟 4**（portfolio-manager）

下週將執行哪些再平衡行動（如有）？確認明確買進、賣出、持有清單與部位大小。

### earnings-weekly

**步驟 1**（drawdown-circuit-breaker）

帳戶熔斷關卡是否已放行（TRADING_ALLOWED），允許本週新增財報動能交易風險？

**步驟 3**（pead-screener）

哪些已評級個股處於 BREAKOUT 或 SIGNAL_READY，值得圖表檢視？哪些 MONITORING 或 EXPIRED 個股留在觀察清單或移除？是否使用第2步的 JSON 以 Mode B 執行篩選，且刻意選定最低評級？

**步驟 4**（technical-analyst）

週線是否確認清楚的財報後漂移，且下跌 K 棒低點為合理停損、流動性可接受、無破壞假設的消息？即使階段與評分良好，週線不明確仍須拒絕。

**步驟 6**（trader-memory-core）

哪些已驗證個股值得登錄財報後漂移假設，寫明進場、停損與部位大小？哪些僅保留觀察？登錄的假設僅為 IDEA，不是下單核准。

**步驟 7**（pre-trade-discipline-gate）

人工券商下單前，各可執行候選是否通過書面計畫、預設停損、部位大小、近期虧損、市場狀態與帳戶熔斷紀律檢查？觀察清單僅記錄為不行動日誌，不是下單核准。

### kanchi-dividend-weekly

**步驟 3**（kanchi-dividend-sop）

每個候選的 Kanchi 判定是否達可執行級別 CLEAN-PASS、PASS-CAUTION 或 CONDITIONAL-PASS？HOLD-REVIEW、STEP1-RECHECK、FAIL 一律阻擋，在此停止，不進入部位計算或登錄。可用第1、2步篩選器（如可取得）或人工 ticker 清單，兩個篩選器皆非本步必需。

**步驟 6**（trader-memory-core）

對每個可執行候選，先將 kanchi_candidates 判定登錄成 IDEA 假設，再以 thesis_store.link_report() 連結已儲存的 stock_memo 檔案，以及可取得的稅務／帳戶配置意見和監控警示。完整 Kanchi 備忘錄須成為可稽核紀錄的一部分，而非只在文字中提及。下單前確認沒有未解決阻礙，並核對部位大小、產業集中度及分批計畫。實際券商成交前絕不轉為 ACTIVE；本步只到 IDEA／ENTRY_READY。

### market-regime-daily

**步驟 4**（exposure-coach）

依今日市場廣度、上升趨勢參與率與頭部風險，新增波段交易風險應為允許、限制或現金優先？

### monthly-performance-review

**步驟 2**（signal-postmortem）

本月結果出現哪些重複模式？依交易假設品質、執行、市場環境與隨機性分類。

**步驟 3**（trade-performance-coach）

下月哪些操作規則應接受、修改、延後或僅記入日誌？

**步驟 6**（trader-memory-core）

依本月證據，下月將變更哪些具體規則？若已執行教練檢視，記錄接受、修改、延後或僅記錄的決定；最終核准保留該決定但不啟用規則。交易端規則與儲存庫端改善應分開。

### multi-asset-opportunity-daily

**步驟 4**（trade-hypothesis-ideator）

每項假設的第一層（總體）與第二層（主題）是否一致？已反映於價格的預期是否仍有利？若與市場共識的差距不明確或已消失，拒絕該卡。

**步驟 6**（trader-memory-core）

哪些假設應從 IDEA 提升至 ENTRY_READY？哪些保留 IDEA 以待進一步確認？哪些應拒絕？

### portfolio-holdings-review

原文無決策關卡。

## W02

### shapiro-contrarian

**步驟 1**（cot-contrarian-detector）

本週哪些期貨市場的3年 COT Index 達擁擠極端值（CROWDED_LONG／CROWDED_SHORT）？僅擁擠並非訊號，只將極端值傳至下一步。

**步驟 2**（news-reaction-failure-analyzer）

每個擁擠市場的價格是否未對有利於擁擠方向的消息產生預期反應（使用 WebSearch 整理第一手或通訊社事件檔案，判定 CONFIRMED）？排除 NOT_CONFIRMED／INSUFFICIENT_EVIDENCE 市場。

**步驟 3**（technical-analyst）

週線圖是否出現與擁擠方向相反的反轉（關鍵反轉、突破失敗或極端值失敗），判定 CONFIRMED 並具明確波段停損？拒絕 NOT_CONFIRMED／INSUFFICIENT_DATA。

**步驟 4**（contrarian-setup-gate）

關卡是否達 READY_FOR_PLAN（擁擠、消息反應失敗及價格行為全數 CONFIRMED，未通過即阻擋）？僅 READY_FOR_PLAN 市場可計算部位；CROWDED、WATCHING_PRICE、REJECTED、INSUFFICIENT_EVIDENCE 在此停止。

**步驟 6**（trader-memory-core）

只登錄 sizing_status 為 SIZED 的反向計畫，絕不登錄 NO_TRADE。依序：(1) 先建立 IDEA 假設（人工登錄或 register()；attach-futures-position 只附加至已存在的假設，不會建立假設）；(2) 使用 attach-futures-position 附加 SIZED 報告，將合約口數、方向、乘數、USD 幣別及風險保存於假設部位；(3) 以 thesis_store.link_report() 連結上游 cot_crowding_report、news_failure_verdict、price_action_confirmation_report 及 contrarian_setup_gate_report，使完整證據鏈可稽核；(4) 僅在券商實際成交後，使用 open-position 轉為 ACTIVE。確認單筆風險符合計算器輸出，整體部位風險在預算內。

### stockbee-20pct-study-daily

**步驟 4**（stockbee-20pct-study）

哪些20%漲跌型態具有足夠樣本數、穩定的後續結果與執行可行性，可提升至交易優勢研究，而非僅記入日誌的觀察？

**步驟 5**（trader-memory-core）

哪些發現可接受為操作規則候選？哪些拒絕？哪些仍待更多案例？

### stockbee-ep-daily

**步驟 1**（drawdown-circuit-breaker）

帳戶熔斷關卡是否已放行（TRADING_ALLOWED），允許今天新增 EP 交易風險？

**步驟 4**（stockbee-episodic-pivot-analyzer）

哪些候選具真正改變基本情勢的催化因素，並有價量確認？區分 ACTIONABLE_DAY1 與 DELAYED_EP_WATCH，拒絕僅標題驅動的低品質波動。

**步驟 5**（technical-analyst）

圖表是否確認清楚的 EP 反應，且收盤品質、流動性及至 EP 當日低點的風險可接受？

**步驟 8**（trader-memory-core）

哪些候選值得建立有效追蹤的交易假設？哪些應放入延後 EP／PEAD 觀察清單？哪些即使初始評分高也應略過？

**步驟 9**（pre-trade-discipline-gate）

人工券商下單前，ACTIONABLE_DAY1 或 ENTRY_READY 的 EP 候選是否通過書面計畫、預設停損、部位大小、近期虧損、市場狀態及熔斷紀律檢查？延後 EP、PEAD 交接、略過或拒絕的候選應作為不行動日誌，不是下單核准。

### stockbee-fluency-loop

**步驟 3**（stockbee-setup-fluency-trainer）

哪些型態標籤已有足夠到期案例，可提升、降級或繼續監控？變更交易規則前須檢視代表性圖表。

**步驟 4**（trader-memory-core）

哪些發現可接受為操作規則變更？哪些仍應僅記入日誌、等待更多案例？

### strategy-research-pipeline

**步驟 3**（edge-candidate-agent）

是否使用與第1步相同的本地 OHLCV 檔案及 --as-of 日期，以 --hints 指向第2步 hints.yaml，並使用獨立輸出目錄？是否有值得測試的最終提案？否則在此停止。

**步驟 4**（backtest-expert）

呼叫評估器前，操作者能否確認所有指標均對應最終提案的策略、股票池、期間與成本假設？必要指標是否全部齊備，且實際測試過滑價？任何答案是否定或未知，均 HOLD 且不給評級。Deploy／Refine／Abandon 評分絕非真實資金交易核准。

### swing-opportunity-daily

**步驟 1**（drawdown-circuit-breaker）

帳戶熔斷關卡是否已放行（TRADING_ALLOWED），允許今天新增交易風險？

**步驟 7**（technical-analyst）

哪些候選有清楚的週線型態（Stage 2 上升趨勢、緊密底部，或從受控制底部出現 Stockbee 式振幅擴張），且通過人工圖表檢視？賣壓耗竭錘形須確認回檔未破壞假設，且至當日低點的風險可接受。拒絕未通過者。

**步驟 10**（trader-memory-core）

對每個通過驗證的候選，登錄進場、停損、目標的交易假設。確認單筆風險符合 position-sizer 輸出，整體部位風險在預算內。

**步驟 11**（pre-trade-discipline-gate）

在人工券商下單前，每個可執行候選是否通過書面計畫、預設停損、部位大小、近期虧損、市場狀態與帳戶熔斷紀律檢查？

### trade-memory-loop

**步驟 2**（signal-postmortem）

結果的根因為何：交易假設品質、執行、市場環境，或隨機性？分類並記錄。

**步驟 3**（trade-performance-coach）

下次交易時段哪些操作規則應接受、修改、延後，或僅記入日誌？

