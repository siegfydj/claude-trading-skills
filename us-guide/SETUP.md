# SETUP — 重建清單

1. `git clone https://github.com/siegfydj/claude-trading-skills` 並切到 main。
2. 需要 Python 3.11 以上與 PyYAML：`pip install pyyaml`。
3. `python3 us-guide/scripts/build_guide.py`
4. 用瀏覽器打開 `us-guide/index.html`。

不需要任何金鑰。若之後做網頁執行層，金鑰放後端環境變數（FMP_API_KEY、FINVIZ_API_KEY、ALPACA_API_KEY、ALPACA_SECRET_KEY），不進 repo。
