# NOTES — us-guide

## 進度（2026-11-24）
- [x] 取得 fork 推送權限，建立 `us-guide/`
- [x] 產生器 `scripts/build_guide.py`（讀 skills-index.yaml／workflows／skillsets，輸出 JSON 與自含式 index.html）
- [x] 看板 v0（英文原文＋繁中介面；五個分頁；已用無頭 Chrome 驗證無錯誤）
- [x] 網頁執行規劃與分工任務單（已移到作者的私有庫，不放在這個公開 fork）
- [ ] 繁中說明填入 `data/zh-TW.json`（74 個 skill＋14 條流程）→ 交給 Gemini（任務單 T01、T02 在私有庫）
- [ ] 美股名詞對照、第一週閱讀路線 → 交給 ChatGPT 對話版（任務單 T03～T05 在私有庫）

## 執行層 P2（2026-11-26）
- [x] `tools/position-sizer.html`：position-sizer 的離線瀏覽器版（固定風險比例／ATR／Kelly；可選部位與產業上限、碎股）。純計算、無後端、無金鑰。
- [x] `tools/position_sizer.js`：用 BigInt 有理數模擬 Python Decimal（28 位有效數字、half-even、`int()` 截斷、Python `round()` 對二進位精確值的銀行家捨入），錯誤訊息與上游相同。
- [x] 比對測試：4,000 筆隨機＋手選邊界案例，與上游 `position_sizer.py` 逐欄位比對；另跑過 48,000 筆壓力向量，0 筆不一致；故意改壞捨入方式，測試會抓到。
- 上游若改了 `position_sizer.py` 的算法，比對測試會失敗，需同步改 JS。
- 看板「網頁執行規劃」分頁已加連結。

## 執行層 P2b（2026-11-26）
- [x] `tools/backtest-expert.html`＋`tools/backtest_expert.js`：backtest-expert 的離線版（五構面 0～100 分、判定、紅旗、英文報告可複製）。期望值與獲利因子用精度 100 位的精確小數（BigInt 有理數），其餘雙精度，與上游相同；`position_sizer.js` 多匯出 `_internals` 供重用，`round28` 改由 `roundPrec` 實作（行為不變）。
- [x] 比對測試 3,500 筆隨機＋83 筆手選邊界（含上游註解提到的浮點雜訊案例、極大／極小數、平手進位、驗證錯誤）；故意改壞 6 處（取整方式、四捨五入規則、期望值符號與期望值改用浮點、repr 門檻、「勝率>90」改成≥）測試都會失敗；把 100 位精度改成 28 位則測不出差異（實際輸入下兩者等價），仍照上游用 100 位。
- 不移植：寫檔與命令列；不支援輸入 -0.0（網頁轉成 0）與超過 2^53 的整數。

## 待決定
- 網頁執行層放哪裡（規劃見私有庫）。D 層已決定「只準備提示包、不執行」
- 不使用 GitHub Pages（2026-11-24 使用者決定）；看板只在本機或自有主機開啟

## 部署
- 目前沒有部署步驟：本機打開 `index.html` 即可。
- 不修改上游的 `.github/workflows/`、`docs/`、`skills/`；同步上游後重跑 build_guide.py。
