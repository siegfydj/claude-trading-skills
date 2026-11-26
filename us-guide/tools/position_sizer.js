/*
 * position_sizer.js — 瀏覽器與 Node 共用的部位試算核心。
 *
 * 逐段對應 skills/position-sizer/scripts/position_sizer.py（上游），結果必須和它完全相同。
 * 上游用 Python 的 Decimal（28 位有效數字、四捨六入五成雙）做股數運算，用 float 做其餘運算，
 * 所以這裡：
 *   - 股數、風險金額用 BigInt 有理數 ＋ 每步四捨到 28 位有效數字，重現 Decimal 的行為；
 *   - 其餘運算直接用 JS 的雙精度（和 Python float 是同一種 IEEE 754 運算）；
 *   - Python 的 round(x, 2)（對雙精度精確值做五成雙）用 pyRound2 重現。
 * 改動這個檔案後，執行 python3 -m pytest us-guide/scripts/tests/test_position_sizer_js_parity.py。
 *
 * 輸入欄位名稱沿用上游（snake_case）；null／undefined 代表 Python 的 None。
 * 錯誤訊息用上游的英文原文（頁面再翻成中文）。
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.PositionSizer = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  // ---------- 精確有理數（{n, d}，d > 0，已約分）----------
  const ZERO = 0n;
  const ONE = 1n;
  const TEN = 10n;

  function absBig(a) { return a < ZERO ? -a : a; }
  function gcd(a, b) {
    a = absBig(a); b = absBig(b);
    while (b) { const t = a % b; a = b; b = t; }
    return a;
  }
  function Q(n, d) {
    if (d === undefined) d = ONE;
    if (d < ZERO) { n = -n; d = -d; }
    const g = gcd(n, d) || ONE;
    return { n: n / g, d: d / g };
  }
  function pow10(k) { return TEN ** BigInt(k); }

  // Decimal(str(x))：以 JS 最短往返字串精確轉成有理數（和 Python str(float) 的數值相同）
  function fromFloat(x) {
    const m = /^([+-]?)(\d*)(?:\.(\d*))?(?:[eE]([+-]?\d+))?$/.exec(String(x));
    if (!m) throw new Error('cannot convert to decimal: ' + x);
    const ip = m[2] || '';
    const fp = m[3] || '';
    const exp = parseInt(m[4] || '0', 10);
    let n = BigInt((ip + fp) || '0');
    if (m[1] === '-') n = -n;
    const scale = fp.length - exp;
    return scale >= 0 ? Q(n, pow10(scale)) : Q(n * pow10(-scale), ONE);
  }
  function fromInt(i) { return Q(BigInt(i), ONE); }

  // Python Decimal 預設環境：每個運算結果四捨五成雙到 28 位有效數字
  function round28(q) {
    if (q.n === ZERO) return q;
    const neg = q.n < ZERO;
    const n = neg ? -q.n : q.n;
    const d = q.d;
    const ge = (k) => (k >= 0 ? n >= pow10(k) * d : n * pow10(-k) >= d); // 值 >= 10^k
    let e = n.toString().length - d.toString().length - 1;
    while (!ge(e)) e -= 1;
    while (ge(e + 1)) e += 1;
    const s = 27 - e; // 保留的小數位數（可為負）
    const num = s >= 0 ? n * pow10(s) : n;
    const den = s >= 0 ? d : d * pow10(-s);
    let f = num / den;
    const twice = (num % den) * 2n;
    if (twice > den || (twice === den && f % 2n === ONE)) f += ONE;
    const r = s >= 0 ? Q(f, pow10(s)) : Q(f * pow10(-s), ONE);
    return neg ? Q(-r.n, r.d) : r;
  }
  const add = (a, b) => round28(Q(a.n * b.d + b.n * a.d, a.d * b.d));
  const sub = (a, b) => round28(Q(a.n * b.d - b.n * a.d, a.d * b.d));
  const mul = (a, b) => round28(Q(a.n * b.n, a.d * b.d));
  const div = (a, b) => round28(Q(a.n * b.d, a.d * b.n));

  function floorBig(q) {
    let f = q.n / q.d;
    if (q.n % q.d !== ZERO && q.n < ZERO) f -= ONE;
    return f;
  }
  function truncBig(q) { return q.n / q.d; }

  // 把「十進位有限小數」的有理數轉成最接近的雙精度（等同 Python float(Decimal)）
  function toFloat(q) {
    for (let k = 0; k <= 400; k += 1) {
      const p = pow10(k);
      if (p % q.d === ZERO) {
        const scaled = q.n * (p / q.d); // 值 = scaled / 10^k
        const neg = scaled < ZERO;
        let digits = (neg ? -scaled : scaled).toString();
        if (k > 0) {
          digits = digits.padStart(k + 1, '0');
          digits = digits.slice(0, digits.length - k) + '.' + digits.slice(digits.length - k);
        }
        return Number((neg ? '-' : '') + digits);
      }
    }
    throw new Error('value is not a finite decimal');
  }

  // 雙精度的精確值（尾數 × 2^指數）
  function exactFromDouble(x) {
    const buf = new DataView(new ArrayBuffer(8));
    buf.setFloat64(0, x);
    const bits = buf.getBigUint64(0);
    const neg = (bits >> 63n) === ONE;
    const expBits = Number((bits >> 52n) & 0x7ffn);
    const frac = bits & ((ONE << 52n) - ONE);
    const mant = expBits === 0 ? frac : frac | (ONE << 52n);
    const e = (expBits === 0 ? 1 : expBits) - 1075;
    const n = neg ? -mant : mant;
    return e >= 0 ? Q(n << BigInt(e), ONE) : Q(n, ONE << BigInt(-e));
  }

  // Python round(x, 2)：對雙精度精確值取到 0.01，剛好在中間時取偶數
  function pyRound2(x) {
    if (!Number.isFinite(x)) return x;
    const ex = exactFromDouble(x);
    const neg = ex.n < ZERO;
    const n = (neg ? -ex.n : ex.n) * 100n;
    const d = ex.d;
    let f = n / d;
    const twice = (n % d) * 2n;
    if (twice > d || (twice === d && f % 2n === ONE)) f += ONE;
    const s = f.toString().padStart(3, '0');
    const out = Number(s.slice(0, s.length - 2) + '.' + s.slice(s.length - 2));
    return neg ? -out : out;
  }

  // Decimal.quantize(0.01, ROUND_HALF_UP) 後轉 float
  function quantizeCentHalfUp(q) {
    const neg = q.n < ZERO;
    const n = (neg ? -q.n : q.n) * 100n;
    let f = n / q.d;
    if ((n % q.d) * 2n >= q.d) f += ONE;
    const s = f.toString().padStart(3, '0');
    const out = Number(s.slice(0, s.length - 2) + '.' + s.slice(s.length - 2));
    return neg ? -out : out;
  }

  // ---------- 對應 position_sizer.py ----------
  const FLOAT_FIELDS = [
    'account_size', 'entry_price', 'stop_price', 'risk_pct', 'atr', 'win_rate',
    'avg_win', 'avg_loss', 'max_position_pct', 'max_sector_pct', 'current_sector_exposure',
  ];
  const isNone = (v) => v === null || v === undefined;

  function normalize(input) {
    const p = {
      account_size: input.account_size,
      entry_price: isNone(input.entry_price) ? null : input.entry_price,
      stop_price: isNone(input.stop_price) ? null : input.stop_price,
      risk_pct: isNone(input.risk_pct) ? null : input.risk_pct,
      atr: isNone(input.atr) ? null : input.atr,
      atr_multiplier: isNone(input.atr_multiplier) ? 2.0 : input.atr_multiplier,
      win_rate: isNone(input.win_rate) ? null : input.win_rate,
      avg_win: isNone(input.avg_win) ? null : input.avg_win,
      avg_loss: isNone(input.avg_loss) ? null : input.avg_loss,
      max_position_pct: isNone(input.max_position_pct) ? null : input.max_position_pct,
      max_sector_pct: isNone(input.max_sector_pct) ? null : input.max_sector_pct,
      sector: isNone(input.sector) ? null : input.sector,
      current_sector_exposure: isNone(input.current_sector_exposure) ? 0.0 : input.current_sector_exposure,
      fractional_shares: Boolean(input.fractional_shares),
      share_precision: isNone(input.share_precision) ? 4 : input.share_precision,
    };
    return p;
  }

  function validateParameters(p) {
    for (const name of FLOAT_FIELDS) {
      const v = p[name];
      if (!isNone(v) && !Number.isFinite(v)) throw new Error(name + ' must be finite');
    }
    if (p.account_size <= 0) throw new Error('account_size must be positive');
    if (!isNone(p.entry_price) && p.entry_price <= 0) throw new Error('entry_price must be positive');
    if (!isNone(p.stop_price) && p.stop_price <= 0) {
      throw new Error('stop_price must be positive (and below entry_price) for long trades');
    }
    if (!isNone(p.stop_price) && !isNone(p.entry_price) && p.stop_price >= p.entry_price) {
      throw new Error('stop_price must be below entry_price for long trades');
    }
    if (!isNone(p.risk_pct) && p.risk_pct <= 0) throw new Error('risk_pct must be positive');
    if (!isNone(p.atr) && p.atr <= 0) throw new Error('atr must be positive');
    if (!Number.isFinite(p.atr_multiplier) || p.atr_multiplier <= 0) {
      throw new Error('atr_multiplier must be finite and positive');
    }
    if (!isNone(p.win_rate) && (p.win_rate <= 0 || p.win_rate >= 1.0)) {
      throw new Error('win_rate must be between 0 and 1 (exclusive)');
    }
    if (!isNone(p.avg_win) && p.avg_win <= 0) throw new Error('avg_win must be positive');
    if (!isNone(p.avg_loss) && p.avg_loss <= 0) throw new Error('avg_loss must be positive');
    if (p.share_precision < 0 || p.share_precision > 8) {
      throw new Error('share_precision must be between 0 and 8');
    }
  }

  const D = fromFloat; // to_decimal

  // floor_share_quantity：整股取整數部分（int()），碎股往下取到指定小數位
  function floorShareQuantity(q, p) {
    if (!p.fractional_shares) return Number(truncBig(q));
    const scaled = floorBig(Q(q.n * pow10(p.share_precision), q.d));
    return toFloat(Q(scaled, pow10(p.share_precision)));
  }

  function calculateFixedFractional(p) {
    const riskPerShare = sub(D(p.entry_price), D(p.stop_price));
    const dollarRisk = div(mul(D(p.account_size), D(p.risk_pct)), fromInt(100));
    const shares = floorShareQuantity(div(dollarRisk, riskPerShare), p);
    return {
      method: 'fixed_fractional',
      shares,
      risk_per_share: pyRound2(toFloat(riskPerShare)),
      dollar_risk: pyRound2(toFloat(dollarRisk)),
      stop_price: p.stop_price,
    };
  }

  function calculateAtrBased(p) {
    const entry = D(p.entry_price);
    const stopDistance = mul(D(p.atr), D(p.atr_multiplier));
    const stopPrice = pyRound2(toFloat(sub(entry, stopDistance)));
    if (!(stopPrice > 0 && stopPrice < p.entry_price)) {
      throw new Error('ATR-derived stop price must be positive and below entry price');
    }
    const riskPerShare = sub(entry, D(stopPrice));
    const dollarRisk = div(mul(D(p.account_size), D(p.risk_pct)), fromInt(100));
    const shares = floorShareQuantity(div(dollarRisk, riskPerShare), p);
    return {
      method: 'atr_based',
      shares,
      risk_per_share: toFloat(riskPerShare),
      dollar_risk: pyRound2(toFloat(dollarRisk)),
      stop_price: stopPrice,
      atr: p.atr,
      atr_multiplier: p.atr_multiplier,
    };
  }

  function calculateKelly(p) {
    const w = p.win_rate;
    const r = p.avg_win / p.avg_loss;
    let kellyPct = w - (1 - w) / r;
    kellyPct = Math.max(0.0, kellyPct) * 100;
    const halfKellyPct = kellyPct / 2;
    return {
      method: 'kelly',
      kelly_pct: pyRound2(kellyPct),
      half_kelly_pct: pyRound2(halfKellyPct),
    };
  }

  function applyConstraints(shares, p) {
    const constraints = [];
    const candidates = [shares];
    let binding = null;

    if (!isNone(p.max_position_pct) && p.entry_price) {
      const maxByPos = floorShareQuantity(
        div(div(mul(D(p.account_size), D(p.max_position_pct)), fromInt(100)), D(p.entry_price)),
        p
      );
      constraints.push({ type: 'max_position_pct', limit: p.max_position_pct, max_shares: maxByPos, binding: false });
      candidates.push(maxByPos);
    }

    if (!isNone(p.max_sector_pct) && p.entry_price) {
      const remainingPct = sub(D(p.max_sector_pct), D(p.current_sector_exposure));
      const remainingDollars = mul(div(remainingPct, fromInt(100)), D(p.account_size));
      const maxBySector = Math.max(0, floorShareQuantity(div(remainingDollars, D(p.entry_price)), p));
      constraints.push({
        type: 'max_sector_pct',
        limit: p.max_sector_pct,
        current: p.current_sector_exposure,
        max_shares: maxBySector,
        binding: false,
      });
      candidates.push(maxBySector);
    }

    const final = Math.max(0, Math.min(...candidates));
    for (const c of constraints) {
      if (c.max_shares === final && final < shares) {
        c.binding = true;
        binding = c.type;
      }
    }
    return { final, constraints, binding };
  }

  function calculatePosition(input) {
    const p = normalize(input);
    validateParameters(p);

    const isKelly = !isNone(p.win_rate);
    const hasEntry = !isNone(p.entry_price);
    const result = { schema_version: '1.0', parameters: {} };

    if (isKelly && !hasEntry) {
      const kelly = calculateKelly(p);
      result.mode = 'budget';
      result.parameters = {
        win_rate: p.win_rate,
        avg_win: p.avg_win,
        avg_loss: p.avg_loss,
        account_size: p.account_size,
      };
      result.calculations = { kelly, fixed_fractional: null, atr_based: null };
      const budget = (p.account_size * kelly.half_kelly_pct) / 100;
      result.recommended_risk_budget = pyRound2(budget);
      result.recommended_risk_budget_pct = kelly.half_kelly_pct;
      result.note = 'To calculate shares, re-run with --entry and --stop';
      return result;
    }

    result.mode = 'shares';
    result.parameters = { entry_price: p.entry_price, account_size: p.account_size };
    const calculations = { fixed_fractional: null, atr_based: null, kelly: null };
    let riskShares = 0;

    if (isKelly) {
      const kelly = calculateKelly(p);
      calculations.kelly = kelly;
      const budget = div(mul(D(p.account_size), D(kelly.half_kelly_pct)), fromInt(100));
      if (!isNone(p.stop_price)) {
        const riskPerShare = sub(D(p.entry_price), D(p.stop_price));
        riskShares = floorShareQuantity(div(budget, riskPerShare), p);
        result.parameters.stop_price = p.stop_price;
      } else {
        riskShares = floorShareQuantity(div(budget, D(p.entry_price)), p);
      }
    } else if (!isNone(p.atr)) {
      const atrResult = calculateAtrBased(p);
      calculations.atr_based = atrResult;
      riskShares = atrResult.shares;
      result.parameters.stop_price = atrResult.stop_price;
      result.parameters.risk_pct = p.risk_pct;
    } else {
      const ff = calculateFixedFractional(p);
      calculations.fixed_fractional = ff;
      riskShares = ff.shares;
      result.parameters.stop_price = p.stop_price;
      result.parameters.risk_pct = p.risk_pct;
    }

    result.calculations = calculations;
    if (p.fractional_shares) {
      result.parameters.fractional_shares = true;
      result.parameters.share_precision = p.share_precision;
    }

    const { final, constraints, binding } = applyConstraints(riskShares, p);
    result.constraints_applied = constraints;
    result.final_recommended_shares = final;
    result.final_position_value = pyRound2(final * p.entry_price);

    const stopPrice = result.parameters.stop_price;
    if (!isNone(stopPrice)) {
      const riskPerShare = sub(D(p.entry_price), D(stopPrice));
      const riskTotal = mul(D(final), riskPerShare);
      result.final_risk_dollars = quantizeCentHalfUp(riskTotal);
      result.final_risk_pct = quantizeCentHalfUp(mul(div(riskTotal, D(p.account_size)), fromInt(100)));
    } else {
      result.final_risk_dollars = null;
      result.final_risk_pct = null;
      result.risk_note = 'Stop-loss not defined. Specify --stop to calculate risk dollars.';
    }
    result.binding_constraint = binding;
    return result;
  }

  // 對應 position_sizer.main() 的參數組合檢查（parser.error 的訊息）
  function checkCombination(input) {
    const p = normalize(input);
    if (!isNone(p.risk_pct) && !isNone(p.win_rate)) {
      return 'position sizing requires either risk-pct mode OR kelly mode, not both';
    }
    if (!isNone(p.win_rate)) {
      if (isNone(p.avg_win) || isNone(p.avg_loss)) {
        return 'Kelly mode requires --win-rate, --avg-win, and --avg-loss';
      }
    } else if (!isNone(p.risk_pct)) {
      if (isNone(p.entry_price)) return 'Risk-pct mode requires --entry';
      if (isNone(p.stop_price) && isNone(p.atr)) return 'Risk-pct mode requires either --stop or --atr';
    } else {
      return 'Must specify either --risk-pct or --win-rate mode';
    }
    return null;
  }

  return { calculatePosition, checkCombination, pyRound2, round28, fromFloat };
});
