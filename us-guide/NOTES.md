# NOTES — us-guide

## 進度（2026-11-24）
- [x] 取得 fork 推送權限，建立 `us-guide/`
- [x] 產生器 `scripts/build_guide.py`（讀 skills-index.yaml／workflows／skillsets，輸出 JSON 與自含式 index.html）
- [x] 看板 v0（英文原文＋繁中介面；五個分頁；已用無頭 Chrome 驗證無錯誤）
- [x] 網頁執行規劃與分工任務單（已移到作者的私有庫，不放在這個公開 fork）
- [ ] 繁中說明填入 `data/zh-TW.json`（74 個 skill＋14 條流程）→ 交給 Gemini（任務單 T01、T02 在私有庫）
- [ ] 美股名詞對照、第一週閱讀路線 → 交給 ChatGPT 對話版（任務單 T03～T05 在私有庫）

## 待決定
- 網頁執行層放哪裡（規劃見私有庫）。D 層已決定「只準備提示包、不執行」
- 不使用 GitHub Pages（2026-11-24 使用者決定）；看板只在本機或自有主機開啟

## 部署
- 目前沒有部署步驟：本機打開 `index.html` 即可。
- 不修改上游的 `.github/workflows/`、`docs/`、`skills/`；同步上游後重跑 build_guide.py。
