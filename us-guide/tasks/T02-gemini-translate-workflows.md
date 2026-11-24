# T02（Gemini）：14 條工作流程的繁中說明

## 目標
填寫 `us-guide/data/zh-TW.json` 中 `workflows.<workflow-id>`：`name`、`when_to_run`、`when_not_to_run`、`steps`（以步驟編號為 key）、`manual_review`（字串陣列，順序與原文一致）。

## 輸入
- `us-guide/data/workflows.json`（英文原文）。
- `workflows/<id>.yaml`（含日文欄位，僅供對照，以英文為準）。

## 規則
- 同 T01：繁體中文、保留英文專有名詞與 skill id、不補沒寫的內容、不給買賣建議。
- 「決策關卡」的問題句保持原意，不弱化也不加強。
- `when_not_to_run` 的警語要完整保留。

## 驗收
- JSON 合法，`steps` 的 key 與 workflows.json 的步驟編號完全一致。
- 看板「工作流程」分頁顯示中文，步驟與關卡標記沒有消失。
