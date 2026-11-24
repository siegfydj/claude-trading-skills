# NOTES — us-guide

## 進度（2026-11-24）
- [x] 取得 fork 推送權限，建立 `us-guide/`
- [x] 產生器 `scripts/build_guide.py`（讀 skills-index.yaml／workflows／skillsets，輸出 JSON 與自含式 index.html）
- [x] 看板 v0（英文原文＋繁中介面；五個分頁；已用無頭 Chrome 驗證無錯誤）
- [x] 網頁執行規劃與分工任務單
- [ ] 繁中說明填入 `data/zh-TW.json`（74 個 skill＋14 條流程）→ 交給 Gemini，見 `tasks/`
- [ ] 美股名詞對照、第一週閱讀路線 → 交給 ChatGPT，見 `tasks/`

## 待決定
- 網頁執行的實作階段（見 `docs/WEB_EXECUTION_PLAN.md` 第 6 節）
- 看板要不要用 GitHub Pages 對外發布（fork 是公開 repo；目前只需本機打開）

## 部署
- 目前沒有部署步驟：本機打開 `index.html` 即可。
- 不修改上游的 `.github/workflows/`、`docs/`、`skills/`；同步上游後重跑 build_guide.py。
