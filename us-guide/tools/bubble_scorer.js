/*
 * 美股泡沫風險計分（Bubble-O-Meter v2.1）瀏覽器版。
 * 移植自 skills/us-market-bubble-detector/scripts/bubble_scorer.py 的
 * BubbleScorer.calculate_score() 與 format_output()。只做整數加總與分級，不連網。
 * 與上游的差異：不輸出 timestamp（由呼叫端自己加）；輸入的 1.0 與 1 在 JS 無法區分（上游 1.0 會報錯）。
 * 比對測試：us-guide/scripts/tests/test_bubble_scorer_js_parity.py
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.BubbleScorer = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const QUANT = {
    put_call_ratio: ['Put/Call Ratio', 2, 'CBOE equity put/call ratio optimism threshold'],
    volatility_suppression: ['Volatility Suppression + New Highs', 2, 'Low VIX combined with major index proximity to 52-week highs'],
    leverage: ['Leverage', 2, 'FINRA margin debt growth and all-time-high behavior'],
    ipo_heat: ['IPO Market Overheating', 2, 'IPO count and first-day return versus five-year averages'],
    breadth_anomaly: ['Breadth Anomaly', 2, 'New highs with narrow S&P 500 participation above 50DMA'],
    price_acceleration: ['Price Acceleration', 2, 'Three-month return percentile versus the past 10 years'],
  };
  const QUAL = {
    social_penetration: ['Social Penetration', 1, 'Direct, specific, repeated non-investor recommendations'],
    media_search_trends: ['Media/Search Trends', 1, 'Measured 5x+ search interest plus mainstream coverage'],
    valuation_disconnect: ['Valuation Disconnect', 1, 'Documented fundamentals-ignored narrative without double-counting'],
  };
  const has = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
  const MAX_SCORE = 15;

  function validate(scores, schema) {
    const actual = Object.keys(scores);
    const missing = Object.keys(schema).filter((k) => !has(scores, k)).sort();
    const unknown = actual.filter((k) => !has(schema, k)).sort();
    if (missing.length) throw new Error('Missing score(s): ' + missing.join(', '));
    if (unknown.length) throw new Error('Unknown score(s): ' + unknown.join(', '));
    for (const k of actual) {
      const v = scores[k];
      if (typeof v !== 'number' || !Number.isInteger(v)) throw new Error(k + ' must be an integer');
      if (!(v >= 0 && v <= schema[k][1])) throw new Error(k + ' must be between 0 and ' + schema[k][1]);
    }
  }

  function classify(t) {
    if (t <= 4) return ['Normal', 'Low', '100%', 'Continue normal investment strategy'];
    if (t <= 7) return ['Caution', 'Medium', '70-80%', 'Start partial profit-taking and reduce sizing'];
    if (t <= 9) return ['Elevated Risk', 'Medium-High', '50-70%', 'Reduce risk budget and tighten trailing stops'];
    if (t <= 12) return ['Euphoria', 'High', '40-50%', 'Accelerate staged profit-taking and reduce total risk budget'];
    return ['Critical', 'Extreme', '20-30%', 'Prioritize major profit-taking, hedging, and halt new entries'];
  }

  function minsky(q, t) {
    const pa = has(q, 'price_acceleration') ? q.price_acceleration : 0;
    const vol = has(q, 'volatility_suppression') ? q.volatility_suppression : 0;
    const br = has(q, 'breadth_anomaly') ? q.breadth_anomaly : 0;
    if (t <= 4) return 'Displacement/Early Boom';
    if (t <= 7) return pa >= 1 && vol >= 1 ? 'Boom' : 'Displacement/Early Boom';
    if (t <= 9) return 'Late Boom/Elevated Risk';
    if (t <= 12) return pa >= 2 && br >= 2 ? 'Euphoria' : 'Late Boom/Early Euphoria';
    return 'Peak Euphoria/Profit Taking';
  }

  function details(scores, schema) {
    return Object.keys(scores).map((k) => {
      const v = scores[k];
      const max = schema[k][1];
      return {
        indicator: schema[k][0],
        score: v,
        max_score: max,
        status: v === max ? 'high' : v > 0 ? 'medium' : 'low',
        description: schema[k][2],
      };
    });
  }

  const sum = (o) => Object.keys(o).reduce((a, k) => a + o[k], 0);

  /* 等同上游 calculate_score(quantitative, qualitative)；qualitative 省略（null/undefined）時視為九個鍵的平面物件。 */
  function calculateScore(quantitative, qualitative) {
    if (qualitative === undefined || qualitative === null) {
      const flat = quantitative;
      const unknown = Object.keys(flat).filter((k) => !has(QUANT, k) && !has(QUAL, k)).sort();
      if (unknown.length) throw new Error('Unknown score(s): ' + unknown.join(', '));
      quantitative = {};
      qualitative = {};
      for (const k of Object.keys(flat)) {
        if (has(QUANT, k)) quantitative[k] = flat[k];
        else qualitative[k] = flat[k];
      }
    }
    validate(quantitative, QUANT);
    validate(qualitative, QUAL);
    const qt = sum(quantitative);
    const ql = sum(qualitative);
    const total = qt + ql;
    const c = classify(total);
    return {
      quantitative_score: qt,
      qualitative_adjustment: ql,
      total_score: total,
      max_score: MAX_SCORE,
      percentage: Number((total / MAX_SCORE * 100).toFixed(1)),
      phase: c[0],
      risk_level: c[1],
      risk_budget: c[2],
      minsky_phase: minsky(quantitative, total),
      recommended_action: c[3],
      quantitative_scores: quantitative,
      qualitative_scores: qualitative,
      indicator_scores: Object.assign({}, quantitative, qualitative),
      detailed_quantitative_indicators: details(quantitative, QUANT),
      detailed_qualitative_adjustments: details(qualitative, QUAL),
    };
  }

  /* 等同上游 format_output；timestamp 由呼叫端傳入。 */
  function formatOutput(r, timestamp) {
    const bar = '='.repeat(60);
    const L = [
      bar, 'US Market Bubble Risk - Bubble-O-Meter v2.1', bar,
      'Evaluated at: ' + timestamp, '',
      'Quantitative: ' + r.quantitative_score + '/12',
      'Qualitative adjustment: +' + r.qualitative_adjustment + '/3',
      'Final score: ' + r.total_score + '/' + r.max_score + ' (' + pct(r.percentage) + '%)',
      'Phase: ' + r.phase + ' (Risk: ' + r.risk_level + ')',
      'Risk budget: ' + r.risk_budget,
      'Minsky phase: ' + r.minsky_phase,
      'Recommended action: ' + r.recommended_action, '',
      'Quantitative indicators:',
    ];
    r.detailed_quantitative_indicators.forEach((d) => L.push('- ' + d.indicator + ': ' + d.score + '/' + d.max_score + ' (' + d.status + ')'));
    L.push('', 'Qualitative adjustments:');
    r.detailed_qualitative_adjustments.forEach((d) => L.push('- ' + d.indicator + ': +' + d.score + '/' + d.max_score + ' (' + d.status + ')'));
    L.push(bar);
    return L.join('\n');
  }
  // Python 的 float 一律印出小數點（100.0、0.0）
  function pct(x) { return Number.isInteger(x) ? x.toFixed(1) : String(x); }

  return { calculateScore, formatOutput, QUANT, QUAL };
});
