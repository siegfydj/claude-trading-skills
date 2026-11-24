# 繁中翻譯片段

每個 AI／人各翻一個批次，輸出成一個片段檔（例如 `S01.json`）放在這裡，不要直接改 `../zh-TW.json`。

批次清單：`python3 us-guide/scripts/zh_batches.py plan`
驗證並合併：`python3 us-guide/scripts/zh_batches.py merge us-guide/data/zh-batches/S01.json`
格式與字數上限見 `us-guide/scripts/zh_batches.py` 檔頭。

## W-decision-gates.md
W01、W02 的決策關卡問題完整繁中譯文（ChatGPT 產出，2026-11-24）。看板 JSON 的 `steps` 限 80 字，放不下完整問題，所以另存這份當對照；37 條關卡的流程 id、步驟編號、skill 已對過 `workflows.json`，沒有疑似簡體字。目前看板尚未顯示這些文字。

