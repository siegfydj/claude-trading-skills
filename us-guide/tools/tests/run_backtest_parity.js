#!/usr/bin/env node
/*
 * 比對用執行器：從 stdin 讀一個 JSON 陣列（每個元素是一組輸入），
 * 逐組呼叫 backtest_expert.js，把結果（含報告文字）以 JSON 陣列印到 stdout。
 * 由 us-guide/scripts/tests/test_backtest_expert_js_parity.py 呼叫；不連網、不寫檔。
 * JSON 不能放 NaN／Infinity，輸入裡用字串 "NaN"、"Infinity"、"-Infinity"，這裡轉回數字。
 * 輸入欄位 default_max 為 true 時，不傳 max_acceptable_drawdown_pct（用上游預設的整數 50）。
 */
'use strict';
const path = require('path');
const { evaluate, toMarkdown } = require(path.join(__dirname, '..', 'backtest_expert.js'));

const SPECIAL = { NaN: NaN, Infinity: Infinity, '-Infinity': -Infinity };

function decode(input) {
  const out = {};
  for (const [k, v] of Object.entries(input)) {
    out[k] = typeof v === 'string' && Object.prototype.hasOwnProperty.call(SPECIAL, v) ? SPECIAL[v] : v;
  }
  return out;
}

let raw = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => { raw += chunk; });
process.stdin.on('end', () => {
  const cases = JSON.parse(raw);
  const results = cases.map((c) => {
    const input = decode(c);
    if (input.default_max) delete input.max_acceptable_drawdown_pct;
    delete input.default_max;
    try {
      const result = evaluate(input);
      const markdown = toMarkdown(result, 'GEN');
      delete result._max_acceptable_was_default;
      return { ok: true, result, markdown };
    } catch (e) {
      return { ok: false, error: e.message };
    }
  });
  process.stdout.write(JSON.stringify(results));
});
