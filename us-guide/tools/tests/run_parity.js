#!/usr/bin/env node
/*
 * 比對用執行器：從 stdin 讀一個 JSON 陣列（每個元素是一組輸入），
 * 逐組呼叫 position_sizer.js，把結果以 JSON 陣列印到 stdout。
 * 由 us-guide/scripts/tests/test_position_sizer_js_parity.py 呼叫；不連網、不寫檔。
 * JSON 不能放 NaN／Infinity，所以輸入裡用字串 "NaN"、"Infinity"、"-Infinity"，這裡轉回數字。
 */
'use strict';
const path = require('path');
const { calculatePosition, checkCombination } = require(path.join(__dirname, '..', 'position_sizer.js'));

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
    const combo = checkCombination(input);
    if (combo) return { ok: false, error: combo };
    try {
      return { ok: true, result: calculatePosition(input) };
    } catch (e) {
      return { ok: false, error: e.message };
    }
  });
  process.stdout.write(JSON.stringify(results));
});
