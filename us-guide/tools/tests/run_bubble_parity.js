#!/usr/bin/env node
/*
 * 比對用執行器：stdin 讀 JSON 陣列，每個元素 {quant, qual}（qual 為 null 表示平面輸入），
 * 逐組呼叫 bubble_scorer.js，印出 {ok,result,text}。text 的時間戳固定為 'GEN'。
 * 由 us-guide/scripts/tests/test_bubble_scorer_js_parity.py 呼叫；不連網、不寫檔。
 */
'use strict';
const path = require('path');
const { calculateScore, formatOutput } = require(path.join(__dirname, '..', 'bubble_scorer.js'));
let raw = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (c) => { raw += c; });
process.stdin.on('end', () => {
  const out = JSON.parse(raw).map((c) => {
    try {
      const result = calculateScore(c.quant, c.qual);
      return { ok: true, result, text: formatOutput(result, 'GEN') };
    } catch (e) {
      return { ok: false, error: e.message };
    }
  });
  process.stdout.write(JSON.stringify(out));
});
