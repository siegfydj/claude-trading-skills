# 美股 Skill 閱讀指南（us-guide）

這個資料夾專門放「美股版」的 skill 閱讀指南（看板與產生器），與上游檔案分開，同步上游時不會衝突。規劃、分工與任務單放在作者的私有庫，不在這個公開 fork。

## 怎麼打開

直接用瀏覽器打開 `us-guide/index.html`（單一檔案、不需要網路、不需要金鑰）。

頁面分五個分頁：從這裡開始、全部 Skill、工作流程、網頁執行規劃、金鑰與費用。

## 資料夾內容

| 路徑 | 用途 |
|---|---|
| `index.html` | 看板本體（由腳本產生，請勿手改） |
| `data/skills.json` | 74 個 skill 的結構化資料（自動產生） |
| `data/workflows.json`、`data/skillsets.json` | 工作流程與安裝組合（自動產生） |
| `data/zh-TW.json` | 繁體中文說明（可手改或由 AI 協作填寫；腳本只補空欄位，不覆蓋） |
| `scripts/build_guide.py`、`scripts/template.html` | 產生器與頁面樣板 |
| `scripts/zh_batches.py`、`data/zh-batches/` | 多人／多 AI 並行翻譯：各自交一個片段檔，腳本驗證（欄位、字數、疑似簡體字）後合併進 `zh-TW.json` |
| `tools/position-sizer.html`、`tools/position_sizer.js` | 部位試算的離線網頁版（上游 `position-sizer` 的逐位元移植；直接用瀏覽器打開，不需網路、金鑰或後端） |
| `tools/backtest-expert.html`、`tools/backtest_expert.js` | 回測品質檢查的離線網頁版（上游 `backtest-expert` 評分的移植；沿用 `position_sizer.js` 的精確算術工具） |
| `scripts/tests/test_backtest_expert_js_parity.py` | 同上的比對測試：分數、判定、紅旗與報告文字都要與上游腳本完全相同 |
| `scripts/tests/test_position_sizer_js_parity.py` | 比對測試：同一批輸入餵給上游 Python 腳本與 JS 版，結果必須完全相同（需要 Node；沒有 Node 時自動略過） |
| `NOTES.md`、`SETUP.md` | 進度與重建清單 |

## 更新方式

```bash
pip install pyyaml
python3 us-guide/scripts/build_guide.py
```

同步上游後重跑一次即可；`zh-TW.json` 中已翻譯的內容會保留。

翻譯流程：`zh_batches.py plan` 看批次 → 各自產出片段檔放 `data/zh-batches/` → `zh_batches.py merge <檔>` 驗證並合併 → 重跑 `build_guide.py`。測試：`python3 -m pytest us-guide/scripts/tests`。

## 注意

- 僅供教育與流程參考，不是投資建議。
- 上游把多數 skill 的驗證欄位標為「未驗證」，規則與分數請當參考。
- 金鑰一律放環境變數，不要寫進這個資料夾的任何檔案。
