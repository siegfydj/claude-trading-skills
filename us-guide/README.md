# 美股 Skill 閱讀指南（us-guide）

這個資料夾專門放「美股版」的 skill 閱讀指南與相關規劃，與上游檔案分開，同步上游時不會衝突。

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
| `docs/WEB_EXECUTION_PLAN.md` | 「在網頁上執行全部 skill」的規劃 |
| `docs/AI_COLLAB.md` | 多 AI 分工與交接規則 |
| `tasks/` | 派給 Gemini／ChatGPT 的任務單 |
| `NOTES.md`、`SETUP.md` | 進度與重建清單 |

## 更新方式

```bash
pip install pyyaml
python3 us-guide/scripts/build_guide.py
```

同步上游後重跑一次即可；`zh-TW.json` 中已翻譯的內容會保留。

## 注意

- 僅供教育與流程參考，不是投資建議。
- 上游把多數 skill 的驗證欄位標為「未驗證」，規則與分數請當參考。
- 金鑰一律放環境變數，不要寫進這個資料夾的任何檔案。
