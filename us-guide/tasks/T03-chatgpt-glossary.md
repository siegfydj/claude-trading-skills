# T03（ChatGPT，不寫程式）：美股名詞對照表

## 目標
建立 `us-guide/docs/GLOSSARY.md`，把 `skills/*/SKILL.md` 與 `skills/*/references/` 中反覆出現的美股與技術分析名詞整理成繁中對照。

## 輸入
- `us-guide/data/skills.json`（skill 摘要，用來找出名詞）。
- 使用者貼給你的幾個 SKILL.md 段落。

## 輸出格式
Markdown 表格：英文｜台灣慣用中文｜一句白話解釋｜出現在哪些 skill（填 skill id）。至少涵蓋：VCP、CANSLIM、PEAD、FTD、Distribution Day、Breadth、Uptrend Ratio、ATR、MFE／MAE、R-multiple、Stage 2、Pivot、Gap、Episodic Pivot、Momentum Burst。

## 規則
- 只解釋名詞，不評論策略好壞，不給買賣建議。
- 台灣與中國用語不同的詞，用台灣用語。
- 不確定的解釋標「待確認」，不要猜。

## 驗收
Claude 抽查 10 條，與 SKILL.md／references 的定義一致。
