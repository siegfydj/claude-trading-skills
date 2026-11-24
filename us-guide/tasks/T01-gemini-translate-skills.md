# T01（Gemini）：74 個 skill 的繁中說明

## 目標
填寫 `us-guide/data/zh-TW.json` 中 `skills.<skill-id>` 的五個欄位，目前都是 `null`。

## 輸入
- `us-guide/data/skills.json`：每個 skill 的 `summary`、`inputs`、`outputs`、`integrations`、`scripts`。
- `skills/<skill-id>/SKILL.md`：完整說明（英文）。

## 輸出（只改 zh-TW.json 的 null 欄位，不要改 key、不要刪欄位）
| 欄位 | 內容 | 長度 |
|---|---|---|
| `title` | 中文名稱（可保留英文專有名詞，例如「VCP 篩選器」） | 20 字內 |
| `summary` | 這個 skill 做什麼，一到兩句 | 80 字內 |
| `when_to_use` | 什麼情況該用它（依 SKILL.md 的 When to Use） | 120 字內 |
| `how_to_start` | 最小可行的第一步（需要什麼輸入或金鑰） | 120 字內 |
| `cautions` | 限制與常見誤用（資料依賴、不是買賣訊號等） | 120 字內 |

## 規則
- 繁體中文，美股用語（例如：突破、停損、部位、財報、法說）。
- ticker、指標名（ATR、RSI、MA50）、skill id、檔名、指令保留英文。
- 只根據 SKILL.md 與 skills.json 的內容，沒寫到的不要補。不確定就留 `null` 並在 PR 說明列出。
- 不給買賣建議，不加入預測。
- 一批 10 個 skill，一個 commit，最後整理成一個 PR。

## 驗收
- `python3 -c "import json;json.load(open('us-guide/data/zh-TW.json'))"` 通過。
- 重跑 `build_guide.py` 後，看板右上顯示的翻譯進度增加，且頁面無錯誤。
- 抽查 5 個 skill，內容與 SKILL.md 一致（交給 T05 校對）。
