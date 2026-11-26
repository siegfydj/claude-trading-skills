"""Parity test: the browser version of backtest-expert must match the upstream script.

`us-guide/tools/backtest_expert.js` is a port of
`skills/backtest-expert/scripts/evaluate_backtest.py` (`evaluate()` and `to_markdown()`).
The same inputs go to both implementations (hand-written edge cases plus a seeded random
sweep); results, error messages and the markdown report (except the timestamp) must be
identical.

Not covered on purpose: file output, the command line, integers above 2**53 and
negative-zero inputs (the web page turns -0 into 0).

Run: python3 -m pytest us-guide/scripts/tests/test_backtest_expert_js_parity.py
Needs `node` on PATH; the test is skipped when it is missing.
"""

from __future__ import annotations

import importlib.util
import json
import math
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
PY_SCRIPT = ROOT / "skills" / "backtest-expert" / "scripts" / "evaluate_backtest.py"
JS_RUNNER = ROOT / "us-guide" / "tools" / "tests" / "run_backtest_parity.js"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def _load_upstream():
    spec = importlib.util.spec_from_file_location("upstream_evaluate_backtest", PY_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


up = _load_upstream()

NON_FINITE = {"nan": float("nan"), "inf": float("inf"), "-inf": float("-inf")}


def case(**kwargs):
    base = {
        "total_trades": 150,
        "win_rate": 55.0,
        "avg_win_pct": 2.0,
        "avg_loss_pct": 1.0,
        "max_drawdown_pct": 15.0,
        "years_tested": 8,
        "num_parameters": 4,
        "slippage_tested": True,
        "max_acceptable_drawdown_pct": 50.0,
        "default_max": False,
    }
    base.update(kwargs)
    return base


def run_python(c):
    """Mirror the CLI: argparse gives floats for float options, ints for int options."""
    kwargs = {
        "total_trades": c["total_trades"],
        "win_rate": c["win_rate"],
        "avg_win_pct": c["avg_win_pct"],
        "avg_loss_pct": c["avg_loss_pct"],
        "max_drawdown_pct": c["max_drawdown_pct"],
        "years_tested": c["years_tested"],
        "num_parameters": c["num_parameters"],
        "slippage_tested": c["slippage_tested"],
    }
    if not c["default_max"]:
        kwargs["max_acceptable_drawdown_pct"] = c["max_acceptable_drawdown_pct"]
    try:
        result = up.evaluate(**kwargs)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    markdown = re.sub(r"\*\*Generated\*\*: .*", "**Generated**: GEN", up.to_markdown(result))
    return {"ok": True, "result": json.loads(json.dumps(result)), "markdown": markdown}


def encode(c):
    out = {}
    for k, v in c.items():
        if isinstance(v, float) and not math.isfinite(v):
            out[k] = "NaN" if math.isnan(v) else ("Infinity" if v > 0 else "-Infinity")
        else:
            out[k] = v
    return out


def run_js(cases):
    proc = subprocess.run(
        ["node", str(JS_RUNNER)],
        input=json.dumps([encode(c) for c in cases]),
        capture_output=True,
        text=True,
        check=True,
        timeout=180,
    )
    return json.loads(proc.stdout)


def assert_parity(cases):
    expected = [run_python(c) for c in cases]
    actual = run_js(cases)
    assert len(actual) == len(expected)
    bad = [(c, e, a) for c, e, a in zip(cases, expected, actual, strict=True) if e != a]
    assert not bad, f"{len(bad)} mismatches; first: {bad[0]}"


EDGE_CASES = [
    case(),
    case(total_trades=0),
    case(total_trades=29),
    case(total_trades=30),
    case(total_trades=99),
    case(total_trades=100),
    case(total_trades=199),
    case(total_trades=200),
    case(win_rate=0.0),
    case(win_rate=100.0),
    case(win_rate=100.0, avg_loss_pct=0.0),
    case(win_rate=0.0, avg_win_pct=0.0),
    case(win_rate=50.0, avg_win_pct=0.0, avg_loss_pct=0.0),
    case(win_rate=40.0, avg_win_pct=3.0, avg_loss_pct=2.0),  # break-even: exp exactly 0
    case(win_rate=40.0, avg_win_pct=3.0, avg_loss_pct=2.0, slippage_tested=False),
    case(win_rate=30.0, avg_win_pct=1.0, avg_loss_pct=2.0),  # negative
    case(win_rate=58.0, avg_win_pct=1.2, avg_loss_pct=0.9),
    case(win_rate=58.0, avg_win_pct=0.5, avg_loss_pct=0.5),
    case(win_rate=95.0, max_drawdown_pct=3.0),  # too good
    case(win_rate=95.0, max_drawdown_pct=5.0),
    case(max_drawdown_pct=0.0),
    case(max_drawdown_pct=19.999999999999996),
    case(max_drawdown_pct=20.0),
    case(max_drawdown_pct=35.5),
    case(max_drawdown_pct=49.99999999999999),
    case(max_drawdown_pct=50.0),
    case(max_drawdown_pct=100.0),
    case(max_drawdown_pct=1e-07),
    case(max_drawdown_pct=55.0, max_acceptable_drawdown_pct=20.0),
    case(max_drawdown_pct=25.0, max_acceptable_drawdown_pct=20.0),
    case(max_drawdown_pct=25.0, default_max=True),
    case(max_drawdown_pct=25.0, max_acceptable_drawdown_pct=0.0),
    case(years_tested=0),
    case(years_tested=4),
    case(years_tested=5),
    case(years_tested=7),
    case(years_tested=9),
    case(years_tested=10),
    case(years_tested=50),
    case(num_parameters=0),
    case(num_parameters=4),
    case(num_parameters=5),
    case(num_parameters=6),
    case(num_parameters=7),
    case(num_parameters=8),
    case(slippage_tested=False),
    case(win_rate=40.0, avg_win_pct=3.0, avg_loss_pct=2.0, total_trades=10),
    # float-noise cases quoted in the upstream comments
    case(win_rate=30.0, avg_win_pct=3.5e9, avg_loss_pct=1.5e9),
    case(win_rate=10.1, avg_win_pct=8.99e16, avg_loss_pct=1.01e16),
    case(win_rate=1e-300, avg_win_pct=1e-300, avg_loss_pct=1e300),
    case(win_rate=99.99999999999999, avg_win_pct=1e300, avg_loss_pct=1e-300),
    case(win_rate=50.0, avg_win_pct=1e308, avg_loss_pct=1e-300),
    case(win_rate=50.0, avg_win_pct=1e-300, avg_loss_pct=1e308),
    case(win_rate=1e-10, avg_win_pct=1e-300, avg_loss_pct=1e300),
    case(win_rate=5e-324, avg_win_pct=1e300, avg_loss_pct=1.0),
    case(win_rate=50.0, avg_win_pct=5e-324, avg_loss_pct=1.0),
    case(win_rate=50.0, avg_win_pct=1.0, avg_loss_pct=5e-324),
    case(win_rate=99.9, avg_win_pct=1.0, avg_loss_pct=5e-324),
    case(win_rate=0.1 + 0.2, avg_win_pct=1.0, avg_loss_pct=1.0),
    case(win_rate=6.625, avg_win_pct=0.0625, avg_loss_pct=0.0625),
    case(win_rate=50.0, avg_win_pct=0.0625, avg_loss_pct=0.0625),
    case(win_rate=50.0, avg_win_pct=0.1255, avg_loss_pct=0.125),
    # validation errors
    case(total_trades=-1),
    case(win_rate=-0.001),
    case(win_rate=100.0000001),
    case(avg_win_pct=-1.0),
    case(avg_loss_pct=-1.0),
    case(max_drawdown_pct=-1.0),
    case(max_drawdown_pct=100.5),
    case(max_acceptable_drawdown_pct=-1.0),
    case(max_acceptable_drawdown_pct=101.0),
    case(years_tested=-1),
    case(num_parameters=-1),
    case(win_rate=float("nan")),
    case(win_rate=float("inf")),
    case(avg_win_pct=float("inf")),
    case(avg_loss_pct=float("nan")),
    case(max_drawdown_pct=float("-inf")),
    case(max_acceptable_drawdown_pct=float("nan")),
    case(win_rate=1e-200, avg_win_pct=1e-200),
    case(win_rate=50.0, avg_loss_pct=1e-320, max_drawdown_pct=10.0),
    case(win_rate=1.0, avg_win_pct=5e-324),
    case(win_rate=99.0, avg_loss_pct=5e-324),
]


def test_edge_cases_match_upstream_script():
    assert_parity(EDGE_CASES)


def _pct(rng, hi=100.0):
    mode = rng.random()
    if mode < 0.25:
        return float(rng.randint(0, int(hi)))
    if mode < 0.5:
        return round(rng.uniform(0, hi), rng.choice([1, 2, 3]))
    if mode < 0.65:
        return rng.choice([0.0, hi, hi / 2, 0.1, 0.5, 5.0, 20.0, 50.0])
    if mode < 0.85:
        return rng.uniform(0, hi)
    return float(f"{rng.uniform(0, hi):.{rng.randint(4, 15)}g}")


def _gain(rng):
    mode = rng.random()
    if mode < 0.3:
        return round(rng.uniform(0, 10), rng.choice([1, 2]))
    if mode < 0.5:
        return float(rng.randint(0, 20))
    if mode < 0.8:
        return rng.uniform(0, 12)
    if mode < 0.9:
        return rng.choice([0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 0.25, 0.125])
    return 10 ** rng.uniform(-6, 12)


def _random_case(rng):
    return case(
        total_trades=rng.choice([rng.randint(0, 40), rng.randint(0, 400), rng.randint(90, 110)]),
        win_rate=_pct(rng),
        avg_win_pct=_gain(rng),
        avg_loss_pct=_gain(rng),
        max_drawdown_pct=_pct(rng),
        years_tested=rng.choice([rng.randint(0, 12), rng.randint(3, 11)]),
        num_parameters=rng.randint(0, 10),
        slippage_tested=rng.random() < 0.7,
        max_acceptable_drawdown_pct=_pct(rng) if rng.random() < 0.6 else 50.0,
        default_max=rng.random() < 0.3,
    )


def _break_even_case(rng):
    """Cases built to sit exactly on the expectancy = 0 boundary."""
    win = rng.choice([20.0, 25.0, 40.0, 50.0, 60.0, 75.0, 80.0])
    loss_unit = rng.choice([0.5, 1.0, 2.0, 3.0])
    avg_loss = loss_unit * rng.choice([1.0, 2.0, 4.0])
    avg_win = (100.0 - win) * avg_loss / win
    delta = rng.choice([0.0, 0.0, 1e-9, -1e-9])
    return case(win_rate=win, avg_win_pct=avg_win + delta, avg_loss_pct=avg_loss)


def test_random_sweep_matches_upstream_script():
    rng = random.Random(20261126)
    cases = [_random_case(rng) for _ in range(3000)] + [_break_even_case(rng) for _ in range(500)]
    assert_parity(cases)


def test_python_float_formatting_helpers():
    """pyRepr / fmtFixed must agree with Python's repr() and format()."""
    rng = random.Random(7)
    xs = [
        0.0,
        1.0,
        50.0,
        100.0,
        0.1,
        1e-4,
        9.9e-5,
        1e-5,
        1e15,
        9999999999999998.0,
        1e16,
        1.5e16,
        1e22,
        1.7976931348623157e308,
        5e-324,
        123456.789,
    ]
    xs += [rng.uniform(-1, 1) * 10 ** rng.randint(-8, 20) for _ in range(500)]
    src = (
        "const {pyRepr,fmtFixed}=require(process.argv[1]);"
        "let raw='';process.stdin.on('data',c=>raw+=c).on('end',()=>{"
        "const xs=JSON.parse(raw);"
        "process.stdout.write(JSON.stringify(xs.map(x=>[pyRepr(x),fmtFixed(x,3),fmtFixed(x,2)])));});"
    )
    proc = subprocess.run(
        ["node", "-e", src, str(ROOT / "us-guide" / "tools" / "backtest_expert.js")],
        input=json.dumps(xs),
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    got = json.loads(proc.stdout)
    for x, (r, f3, f2) in zip(xs, got, strict=True):
        assert r == repr(x), (x, r)
        assert f3 == f"{x:.3f}", (x, f3)
        assert f2 == f"{x:.2f}", (x, f2)
