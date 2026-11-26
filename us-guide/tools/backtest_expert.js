/*
 * backtest_expert.js — 上游 skills/backtest-expert/scripts/evaluate_backtest.py 的瀏覽器版移植。
 *
 * 目標：同一組輸入，分數、判定、紅旗、報告文字與上游 Python 完全相同。
 * 勝率×平均賺賠的期望值與獲利因子，上游用 Decimal（精度 100 位）算，這裡沿用
 * position_sizer.js 的 BigInt 有理數做法；其餘分數用雙精度，與 Python 的 float 運算相同。
 *
 * 不移植：寫檔（write_outputs）與命令列。報告裡的時間戳由呼叫端傳入。
 * 限制：整數欄位（交易筆數、年數、參數個數）限 JS 安全整數；不支援輸入 -0.0（網頁會先轉成 0）。
 *
 * 僅為數學試算，不是買賣或部位建議。資訊整理，非投資建議。
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory(require('./position_sizer.js'));
  else root.BacktestExpert = factory(root.PositionSizer);
})(typeof self !== 'undefined' ? self : this, function (PS) {
  'use strict';

  const X = PS._internals;
  const Q = X.Q;
  const P100 = (q) => X.roundPrec(q, 100);

  // ---- Python 格式化 ----

  // Python repr(float)：最短往返數字；十進位指數 < -4 或 >= 16 時用科學記號
  function pyRepr(x) {
    if (Number.isNaN(x)) return 'nan';
    if (x === Infinity) return 'inf';
    if (x === -Infinity) return '-inf';
    if (x === 0) return Object.is(x, -0) ? '-0.0' : '0.0';
    const neg = x < 0;
    const m = /^(\d)(?:\.(\d+))?e([+-]\d+)$/.exec(Math.abs(x).toExponential());
    const digits = m[1] + (m[2] || '');
    const exp10 = parseInt(m[3], 10);
    const decpt = exp10 + 1;
    let out;
    if (exp10 < -4 || exp10 >= 16) {
      const mant = digits.length > 1 ? digits[0] + '.' + digits.slice(1) : digits;
      const ae = Math.abs(exp10);
      out = mant + 'e' + (exp10 < 0 ? '-' : '+') + (ae < 10 ? '0' + ae : String(ae));
    } else if (decpt <= 0) {
      out = '0.' + '0'.repeat(-decpt) + digits;
    } else if (decpt >= digits.length) {
      out = digits + '0'.repeat(decpt - digits.length) + '.0';
    } else {
      out = digits.slice(0, decpt) + '.' + digits.slice(decpt);
    }
    return neg ? '-' + out : out;
  }

  // Python f"{x:.{places}f}"：依雙精度的精確值四捨五入，剛好在中間時取偶數
  function fmtFixed(x, places) {
    const negative = x < 0 || Object.is(x, -0);
    const ex = X.exactFromDouble(Math.abs(x));
    const n = ex.n * X.pow10(places);
    let f = n / ex.d;
    const twice = (n % ex.d) * 2n;
    if (twice > ex.d || (twice === ex.d && f % 2n === 1n)) f += 1n;
    let s = f.toString().padStart(places + 1, '0');
    if (places > 0) s = s.slice(0, s.length - places) + '.' + s.slice(s.length - places);
    return (negative ? '-' : '') + s;
  }

  // ---- 精確的期望值與獲利因子（對應 _exact_components 等）----

  // 回傳 { profit, loss }：win_rate*avg_win 與 (100-win_rate)*avg_loss（都放大 100 倍），精度 100 位
  function exactComponents(winRate, avgWin, avgLoss) {
    const w = X.fromFloat(winRate);
    const a = X.fromFloat(avgWin);
    const l = X.fromFloat(avgLoss);
    const profit = P100(Q(w.n * a.n, w.d * a.d));
    const rest = P100(Q(100n * w.d - w.n, w.d));
    const loss = P100(Q(rest.n * l.n, rest.d * l.d));
    return { profit, loss };
  }
  const cmp = (a, b) => {
    const l = a.n * b.d;
    const r = b.n * a.d;
    return l > r ? 1 : l < r ? -1 : 0;
  };
  function expectancySign(winRate, avgWin, avgLoss) {
    const c = exactComponents(winRate, avgWin, avgLoss);
    return cmp(c.profit, c.loss);
  }
  function calcProfitFactor(winRate, avgWin, avgLoss) {
    const c = exactComponents(winRate, avgWin, avgLoss);
    if (c.loss.n === 0n) return c.profit.n > 0n ? Infinity : 0;
    return X.toFloat(P100(Q(c.profit.n * c.loss.d, c.profit.d * c.loss.n)));
  }
  function calcExpectancy(winRate, avgWin, avgLoss) {
    const c = exactComponents(winRate, avgWin, avgLoss);
    const diff = P100(Q(c.profit.n * c.loss.d - c.loss.n * c.profit.d, c.profit.d * c.loss.d));
    return X.toFloat(P100(Q(diff.n, diff.d * 100n)));
  }

  // ---- 五個構面（各 0～20 分）----

  const int = Math.trunc;

  function scoreSampleSize(totalTrades) {
    if (totalTrades < 30) return 0;
    if (totalTrades < 100) return 8 + int(((totalTrades - 30) / 70) * 7);
    if (totalTrades < 200) return 15 + int(((totalTrades - 100) / 100) * 5);
    return 20;
  }

  function scoreExpectancy(winRate, avgWin, avgLoss) {
    if (expectancySign(winRate, avgWin, avgLoss) <= 0) return 0;
    const exp = calcExpectancy(winRate, avgWin, avgLoss);
    if (exp < 0.5) return 5 + int((exp / 0.5) * 5);
    if (exp < 1.5) return 10 + int(((exp - 0.5) / 1.0) * 8);
    return 20;
  }

  function scoreRiskManagement(maxDd, winRate, avgWin, avgLoss) {
    if (maxDd >= 50) return 0;
    const ddScore = maxDd < 20 ? 12 : int((12 * (50 - maxDd)) / 30);
    const pf = calcProfitFactor(winRate, avgWin, avgLoss);
    let pfScore;
    if (expectancySign(winRate, avgWin, avgLoss) <= 0) pfScore = 0;
    else if (pf >= 3.0) pfScore = 8;
    else pfScore = int(((pf - 1.0) / 2.0) * 8);
    return Math.min(20, ddScore + pfScore);
  }

  function scoreRobustness(years, params) {
    let yearsScore;
    if (years < 5) yearsScore = 0;
    else if (years >= 10) yearsScore = 15;
    else yearsScore = 5 + int(((years - 5) / 5) * 10);
    let paramScore;
    if (params <= 4) paramScore = 5;
    else if (params <= 6) paramScore = 3;
    else if (params === 7) paramScore = 1;
    else paramScore = 0;
    return Math.min(20, yearsScore + paramScore);
  }

  const scoreExecutionRealism = (slippageTested) => (slippageTested ? 20 : 0);

  function getVerdict(total) {
    if (total >= 70) return 'Deploy';
    if (total >= 40) return 'Refine';
    return 'Abandon';
  }

  // ---- 紅旗 ----

  function detectRedFlags(p) {
    const flags = [];
    if (p.total_trades < 30) {
      flags.push({
        id: 'small_sample',
        severity: 'high',
        message: 'Only ' + p.total_trades + ' trades — minimum 30 required for statistical confidence.',
      });
    }
    if (!p.slippage_tested) {
      flags.push({
        id: 'no_slippage_test',
        severity: 'high',
        message: 'Slippage/friction not tested — results may not survive real-world execution.',
      });
    }
    if (p.max_drawdown_pct >= 50) {
      flags.push({
        id: 'excessive_drawdown',
        severity: 'high',
        message: 'Max drawdown ' + pyRepr(p.max_drawdown_pct) + '% meets or exceeds the 50% hard ceiling — catastrophic risk.',
      });
    }
    if (p.num_parameters >= 7) {
      flags.push({
        id: 'over_optimized',
        severity: 'medium',
        message: p.num_parameters + ' parameters suggests over-optimization / curve-fitting risk.',
      });
    }
    if (p.years_tested < 5) {
      flags.push({
        id: 'short_test_period',
        severity: 'medium',
        message: 'Only ' + p.years_tested + ' years tested — may miss regime changes (minimum 5 recommended).',
      });
    }
    const exp = calcExpectancy(p.win_rate, p.avg_win_pct, p.avg_loss_pct);
    if (expectancySign(p.win_rate, p.avg_win_pct, p.avg_loss_pct) < 0) {
      flags.push({
        id: 'negative_expectancy',
        severity: 'high',
        message: 'Negative expectancy (' + fmtFixed(exp, 3) + '%) — strategy loses money on average.',
      });
    }
    if (p.win_rate > 90 && p.max_drawdown_pct < 5) {
      flags.push({
        id: 'too_good',
        severity: 'medium',
        message: 'Results look too good — audit for look-ahead bias or data issues.',
      });
    }
    return flags;
  }

  // ---- 輸入檢查（訊息與上游相同）----

  function validateInputs(p) {
    for (const name of ['total_trades', 'years_tested', 'num_parameters']) {
      const v = p[name];
      if (typeof v !== 'number' || !Number.isInteger(v) || !Number.isSafeInteger(v)) {
        throw new Error(name + ' must be an integer');
      }
    }
    for (const name of ['win_rate', 'avg_win_pct', 'avg_loss_pct', 'max_drawdown_pct', 'max_acceptable_drawdown_pct']) {
      const v = p[name];
      if (typeof v !== 'number' || !Number.isFinite(v)) throw new Error(name + ' must be a finite number');
    }
    if (typeof p.slippage_tested !== 'boolean') throw new Error('slippage_tested must be boolean');
    if (p.total_trades < 0) throw new Error('total_trades must be >= 0');
    if (!(p.win_rate >= 0 && p.win_rate <= 100)) throw new Error('win_rate must be between 0 and 100');
    if (p.avg_win_pct < 0) throw new Error('avg_win_pct must be >= 0');
    if (p.avg_loss_pct < 0) throw new Error('avg_loss_pct must be >= 0');
    if (!(p.max_drawdown_pct >= 0 && p.max_drawdown_pct <= 100)) throw new Error('max_drawdown_pct must be between 0 and 100');
    if (!(p.max_acceptable_drawdown_pct >= 0 && p.max_acceptable_drawdown_pct <= 100)) {
      throw new Error('max_acceptable_drawdown_pct must be between 0 and 100');
    }
    if (p.years_tested < 0) throw new Error('years_tested must be >= 0');
    if (p.num_parameters < 0) throw new Error('num_parameters must be >= 0');
    const winFraction = p.win_rate / 100.0;
    const lossFraction = 1.0 - winFraction;
    if (p.win_rate > 0 && p.avg_win_pct > 0 && winFraction * p.avg_win_pct === 0) {
      throw new Error('win_rate and avg_win_pct produce an unrepresentable gross profit');
    }
    if (p.win_rate < 100 && p.avg_loss_pct > 0 && lossFraction * p.avg_loss_pct === 0) {
      throw new Error('avg_loss_pct produces an unrepresentable gross loss');
    }
  }

  // ---- 主評估 ----

  // input.max_acceptable_drawdown_pct 省略時用 50（上游預設值，是整數 50）
  function evaluate(input) {
    const defaulted = input.max_acceptable_drawdown_pct === undefined;
    const p = Object.assign({}, input, { max_acceptable_drawdown_pct: defaulted ? 50 : input.max_acceptable_drawdown_pct });
    validateInputs(p);
    const d1 = scoreSampleSize(p.total_trades);
    const d2 = scoreExpectancy(p.win_rate, p.avg_win_pct, p.avg_loss_pct);
    const d3 = scoreRiskManagement(p.max_drawdown_pct, p.win_rate, p.avg_win_pct, p.avg_loss_pct);
    const d4 = scoreRobustness(p.years_tested, p.num_parameters);
    const d5 = scoreExecutionRealism(p.slippage_tested);
    const total = Math.max(0, Math.min(100, d1 + d2 + d3 + d4 + d5));

    const expectancy = calcExpectancy(p.win_rate, p.avg_win_pct, p.avg_loss_pct);
    const profitFactor = calcProfitFactor(p.win_rate, p.avg_win_pct, p.avg_loss_pct);
    const grossProfit = (p.win_rate / 100.0) * p.avg_win_pct;
    const grossLoss = (1 - p.win_rate / 100.0) * p.avg_loss_pct;
    const redFlags = detectRedFlags(p);

    const blocking = [];
    if (grossLoss > 0 && profitFactor === Infinity) blocking.push('profit_factor_overflow');
    if (p.total_trades < 30) blocking.push('small_sample');
    const sign = expectancySign(p.win_rate, p.avg_win_pct, p.avg_loss_pct);
    if (sign < 0) blocking.push('negative_expectancy');
    else if (sign === 0) blocking.push('zero_expectancy');
    if (p.max_drawdown_pct >= 50) blocking.push('excessive_drawdown');
    if (p.max_acceptable_drawdown_pct < 50 && p.max_drawdown_pct > p.max_acceptable_drawdown_pct) blocking.push('risk_limit_exceeded');
    if (!p.slippage_tested) blocking.push('no_slippage_test');
    if (p.years_tested < 5) blocking.push('short_test_period');
    if (redFlags.some((f) => f.id === 'too_good')) blocking.push('too_good');

    const has = (r) => blocking.includes(r);
    let decision;
    if (has('small_sample') || has('profit_factor_overflow')) decision = 'NOT_EVALUABLE';
    else if (has('negative_expectancy') || has('zero_expectancy') || has('excessive_drawdown')) decision = 'REJECT';
    else if (has('risk_limit_exceeded')) decision = 'RISK_LIMIT_EXCEEDED';
    else if (has('no_slippage_test') || has('short_test_period') || has('too_good')) decision = 'VALIDATION_REQUIRED';
    else decision = getVerdict(total).toUpperCase();

    const scoreVerdict = getVerdict(total);
    let verdict;
    if (decision === 'REJECT') verdict = 'Abandon';
    else if (decision === 'NOT_EVALUABLE' || decision === 'RISK_LIMIT_EXCEEDED' || decision === 'VALIDATION_REQUIRED') {
      verdict = scoreVerdict === 'Abandon' ? 'Abandon' : 'Refine';
    } else verdict = scoreVerdict;

    let reportedPf;
    let pfStatus;
    if (grossLoss === 0 && grossProfit > 0) { reportedPf = null; pfStatus = 'NO_LOSSES'; }
    else if (grossLoss === 0 && grossProfit === 0) { reportedPf = null; pfStatus = 'UNDEFINED_ZERO_GROSS'; }
    else if (profitFactor === Infinity) { reportedPf = null; pfStatus = 'OVERFLOW'; }
    else { reportedPf = profitFactor; pfStatus = 'FINITE'; }

    return {
      total_score: total,
      quality_score: total,
      decision: decision,
      blocking_reasons: blocking,
      verdict: verdict,
      dimensions: [
        { name: 'Sample Size', score: d1, max_score: 20 },
        { name: 'Expectancy', score: d2, max_score: 20 },
        { name: 'Risk Management', score: d3, max_score: 20 },
        { name: 'Robustness', score: d4, max_score: 20 },
        { name: 'Execution Realism', score: d5, max_score: 20 },
      ],
      red_flags: redFlags,
      profit_factor: reportedPf,
      profit_factor_status: pfStatus,
      expectancy: expectancy,
      inputs: {
        total_trades: p.total_trades,
        win_rate: p.win_rate,
        avg_win_pct: p.avg_win_pct,
        avg_loss_pct: p.avg_loss_pct,
        max_drawdown_pct: p.max_drawdown_pct,
        years_tested: p.years_tested,
        num_parameters: p.num_parameters,
        slippage_tested: p.slippage_tested,
        max_acceptable_drawdown_pct: p.max_acceptable_drawdown_pct,
      },
      // 只供顯示：上游預設的 50 是整數，印出來是 "50" 而不是 "50.0"
      _max_acceptable_was_default: defaulted,
    };
  }

  // 上游 to_markdown；generated 是呼叫端給的時間字串（上游用 datetime.now()）
  function toMarkdown(result, generated) {
    const INT_KEYS = ['total_trades', 'years_tested', 'num_parameters'];
    const lines = [
      '# Backtest Evaluation Report',
      '',
      '**Generated**: ' + generated,
      '',
      '## Decision: ' + result.decision,
      '',
      '**Quality Score: ' + result.quality_score + ' / 100**',
      '**Legacy Verdict: ' + result.verdict + '**',
      '',
      '## Blocking Reasons',
      '',
    ];
    if (result.blocking_reasons.length) result.blocking_reasons.forEach((r) => lines.push('- ' + r));
    else lines.push('None.');
    lines.push('', '## Dimension Scores', '', '| Dimension | Score | Max |', '|-----------|------:|----:|');
    result.dimensions.forEach((d) => lines.push('| ' + d.name + ' | ' + d.score + ' | ' + d.max_score + ' |'));
    lines.push('', '## Key Metrics', '');
    let pfLine;
    if (result.profit_factor_status === 'FINITE') pfLine = '- **Profit Factor**: ' + fmtFixed(result.profit_factor, 2);
    else if (result.profit_factor_status === 'NO_LOSSES') pfLine = '- **Profit Factor**: Inf (no losing trades)';
    else if (result.profit_factor_status === 'UNDEFINED_ZERO_GROSS') pfLine = '- **Profit Factor**: Undefined (zero gross wins and losses)';
    else pfLine = '- **Profit Factor**: Overflow (nonzero gross losses; evaluation required)';
    lines.push(pfLine, '- **Expectancy**: ' + fmtFixed(result.expectancy, 3) + '% per trade');
    if (result.red_flags.length) {
      lines.push('', '## Red Flags', '');
      result.red_flags.forEach((f) => lines.push('- ' + (f.severity === 'high' ? '🔴' : '🟡') + ' **' + f.id + '**: ' + f.message));
    } else {
      lines.push('', '## Red Flags', '', 'No red flags detected.');
    }
    lines.push('', '## Input Parameters', '');
    Object.keys(result.inputs).forEach((key) => {
      const v = result.inputs[key];
      let text;
      if (typeof v === 'boolean') text = v ? 'True' : 'False';
      else if (INT_KEYS.indexOf(key) >= 0) text = String(v);
      else if (key === 'max_acceptable_drawdown_pct' && result._max_acceptable_was_default) text = String(v);
      else text = pyRepr(v);
      lines.push('- **' + key + '**: ' + text);
    });
    lines.push('');
    return lines.join('\n');
  }

  return { evaluate, toMarkdown, pyRepr, fmtFixed, calcExpectancy, calcProfitFactor, expectancySign };
});
