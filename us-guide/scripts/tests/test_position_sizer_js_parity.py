"""Parity test: the browser calculator must give the same numbers as the upstream script.

`us-guide/tools/position_sizer.js` is a port of
`skills/position-sizer/scripts/position_sizer.py`. This test feeds the same inputs
to both implementations (hand-written edge cases plus a seeded random sweep) and
requires identical results, including identical error messages.

Run: python3 -m pytest us-guide/scripts/tests/test_position_sizer_js_parity.py
Needs `node` on PATH; the test is skipped when it is missing.
"""

from __future__ import annotations

import importlib.util
import json
import math
import random
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
PY_SCRIPT = ROOT / "skills" / "position-sizer" / "scripts" / "position_sizer.py"
JS_RUNNER = ROOT / "us-guide" / "tools" / "tests" / "run_parity.js"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def _load_upstream():
    spec = importlib.util.spec_from_file_location("upstream_position_sizer", PY_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ps = _load_upstream()

DEFAULTS = {
    "account_size": None,
    "entry_price": None,
    "stop_price": None,
    "risk_pct": None,
    "atr": None,
    "atr_multiplier": 2.0,
    "win_rate": None,
    "avg_win": None,
    "avg_loss": None,
    "max_position_pct": None,
    "max_sector_pct": None,
    "sector": None,
    "current_sector_exposure": 0.0,
    "fractional_shares": False,
    "share_precision": 4,
}

NON_FINITE = {"nan": float("nan"), "inf": float("inf"), "-inf": float("-inf")}


def case(**kwargs):
    unknown = set(kwargs) - set(DEFAULTS)
    assert not unknown, unknown
    return {**DEFAULTS, **kwargs}


def cli_combination_error(c):
    """Mirror of the argument checks in position_sizer.main() (parser.error texts)."""
    if c["risk_pct"] is not None and c["win_rate"] is not None:
        return "position sizing requires either risk-pct mode OR kelly mode, not both"
    if c["win_rate"] is not None:
        if c["avg_win"] is None or c["avg_loss"] is None:
            return "Kelly mode requires --win-rate, --avg-win, and --avg-loss"
    elif c["risk_pct"] is not None:
        if c["entry_price"] is None:
            return "Risk-pct mode requires --entry"
        if c["stop_price"] is None and c["atr"] is None:
            return "Risk-pct mode requires either --stop or --atr"
    else:
        return "Must specify either --risk-pct or --win-rate mode"
    return None


def run_python(c):
    err = cli_combination_error(c)
    if err:
        return {"ok": False, "error": err}
    params = ps.SizingParameters(**c)
    try:
        return {"ok": True, "result": ps.calculate_position(params)}
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}


def encode(c):
    """JSON cannot carry NaN/inf; send them as strings the runner turns back into numbers."""
    out = {}
    for key, value in c.items():
        if isinstance(value, float) and not math.isfinite(value):
            out[key] = "NaN" if math.isnan(value) else ("Infinity" if value > 0 else "-Infinity")
        else:
            out[key] = value
    return out


def run_js(cases):
    payload = json.dumps([encode(c) for c in cases])
    proc = subprocess.run(
        ["node", str(JS_RUNNER)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def same(a, b):
    """Exact equality; ints and floats compare by value (JSON has one number type)."""
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b, strict=True))
    return a == b


def assert_parity(cases):
    expected = [run_python(c) for c in cases]
    actual = run_js(cases)
    assert len(actual) == len(cases)
    bad = [
        (i, cases[i], expected[i], actual[i])
        for i in range(len(cases))
        if not same(expected[i], actual[i])
    ]
    assert not bad, "mismatches (first 3): " + json.dumps(bad[:3], indent=1, default=str)


EDGE_CASES = [
    # fixed fractional: exact integer quotient (1000 / 10 = 100 shares)
    case(account_size=100000, entry_price=110, stop_price=100, risk_pct=1.0),
    # typical, non-integer quotient
    case(account_size=100000, entry_price=155.0, stop_price=148.5, risk_pct=1.0),
    # binary-float tie: risk per share 6.625 rounds to 6.62 in Python (half even)
    case(account_size=100000, entry_price=155.0, stop_price=148.375, risk_pct=1.0),
    case(account_size=50000, entry_price=20.125, stop_price=19.0, risk_pct=0.5),
    # decimal noise that breaks naive float math (0.1 + 0.2 style)
    case(account_size=100000, entry_price=0.3, stop_price=0.1, risk_pct=0.01),
    case(account_size=1000.1, entry_price=10.1, stop_price=9.9, risk_pct=2.2),
    # constraints
    case(
        account_size=100000,
        entry_price=155.0,
        stop_price=148.5,
        risk_pct=1.0,
        max_position_pct=10,
        max_sector_pct=30,
        sector="Technology",
        current_sector_exposure=22,
    ),
    case(
        account_size=100000,
        entry_price=50,
        stop_price=49,
        risk_pct=1.0,
        max_position_pct=5,
    ),
    case(
        account_size=100000,
        entry_price=50,
        stop_price=49,
        risk_pct=1.0,
        max_sector_pct=20,
        current_sector_exposure=25,
    ),
    case(
        account_size=100000,
        entry_price=50,
        stop_price=49,
        risk_pct=1.0,
        max_sector_pct=20,
        current_sector_exposure=20,
    ),
    # fractional shares at several precisions
    case(
        account_size=100000,
        entry_price=155.0,
        stop_price=148.5,
        risk_pct=1.0,
        fractional_shares=True,
    ),
    case(
        account_size=100000,
        entry_price=155.0,
        stop_price=148.5,
        risk_pct=1.0,
        fractional_shares=True,
        share_precision=0,
    ),
    case(
        account_size=100000,
        entry_price=155.0,
        stop_price=148.5,
        risk_pct=1.0,
        fractional_shares=True,
        share_precision=2,
        max_position_pct=3,
    ),
    case(
        account_size=7777.77,
        entry_price=3.33,
        stop_price=3.1,
        risk_pct=0.75,
        fractional_shares=True,
        share_precision=8,
    ),
    # ATR mode
    case(account_size=100000, entry_price=155.0, atr=3.2, atr_multiplier=2.0, risk_pct=1.0),
    case(account_size=100000, entry_price=155.0, atr=3.2, risk_pct=1.0, max_position_pct=8),
    case(account_size=100000, entry_price=100.0, atr=1.015, atr_multiplier=2.5, risk_pct=1.0),
    case(account_size=100000, entry_price=10.0, atr=6.0, risk_pct=1.0),  # stop <= 0
    case(account_size=100000, entry_price=10.0, atr=0.001, risk_pct=1.0),  # rounds to entry
    case(
        account_size=100000,
        entry_price=155.0,
        stop_price=150.0,
        atr=3.2,
        risk_pct=1.0,
    ),  # atr wins over stop
    # Kelly: budget mode and shares mode
    case(account_size=100000, win_rate=0.55, avg_win=2.5, avg_loss=1.0),
    case(account_size=100000, win_rate=0.4, avg_win=1.0, avg_loss=1.0),  # negative edge
    case(account_size=100000, win_rate=0.5, avg_win=2.0, avg_loss=1.0, entry_price=100.0),
    case(
        account_size=100000,
        win_rate=0.55,
        avg_win=2.5,
        avg_loss=1.0,
        entry_price=100.0,
        stop_price=95.0,
        max_position_pct=10,
    ),
    case(
        account_size=100000,
        win_rate=0.6,
        avg_win=1.5,
        avg_loss=1.0,
        entry_price=48.37,
        stop_price=45.1,
        fractional_shares=True,
        share_precision=3,
    ),
    # validation errors
    case(account_size=0, entry_price=100, stop_price=95, risk_pct=1),
    case(account_size=-5, entry_price=100, stop_price=95, risk_pct=1),
    case(account_size=100000, entry_price=0, stop_price=95, risk_pct=1),
    case(account_size=100000, entry_price=100, stop_price=0, risk_pct=1),
    case(account_size=100000, entry_price=100, stop_price=100, risk_pct=1),
    case(account_size=100000, entry_price=100, stop_price=105, risk_pct=1),
    case(account_size=100000, entry_price=100, stop_price=95, risk_pct=0),
    case(account_size=100000, entry_price=100, atr=0, risk_pct=1),
    case(account_size=100000, entry_price=100, atr=2, atr_multiplier=0, risk_pct=1),
    case(account_size=100000, win_rate=0, avg_win=1, avg_loss=1),
    case(account_size=100000, win_rate=1.0, avg_win=1, avg_loss=1),
    case(account_size=100000, win_rate=0.5, avg_win=0, avg_loss=1),
    case(account_size=100000, win_rate=0.5, avg_win=1, avg_loss=-1),
    case(account_size=100000, entry_price=100, stop_price=95, risk_pct=1, share_precision=9),
    case(account_size=100000, entry_price=100, stop_price=95, risk_pct=1, share_precision=-1),
    case(account_size=float("nan"), entry_price=100, stop_price=95, risk_pct=1),
    case(account_size=100000, entry_price=float("inf"), stop_price=95, risk_pct=1),
    case(account_size=100000, entry_price=100, stop_price=95, risk_pct=float("-inf")),
    case(
        account_size=100000, entry_price=100, stop_price=95, risk_pct=1, atr_multiplier=float("nan")
    ),
    # combination errors (same text as the CLI's parser.error)
    case(account_size=100000, entry_price=100, stop_price=95, risk_pct=1, win_rate=0.5),
    case(account_size=100000, win_rate=0.5, avg_win=2.0),
    case(account_size=100000, risk_pct=1.0, stop_price=95),
    case(account_size=100000, risk_pct=1.0, entry_price=100),
    case(account_size=100000, entry_price=100, stop_price=95),
]


def test_edge_cases_match_upstream_script():
    assert_parity(EDGE_CASES)


def _price(rng):
    kind = rng.random()
    if kind < 0.7:
        return round(rng.uniform(1, 600), 2)
    if kind < 0.9:
        return round(rng.uniform(0.2, 90), rng.choice([3, 4]))
    return float(rng.randint(2, 900))


def _random_case(rng):
    account = rng.choice(
        [float(rng.randint(1000, 5_000_000)), round(rng.uniform(1000, 900_000), 2)]
    )
    entry = _price(rng)
    mode = rng.choice(["ff", "ff", "atr", "kelly_budget", "kelly_shares", "kelly_nostop"])
    kwargs = {"account_size": account}
    if mode in ("ff", "atr"):
        kwargs["entry_price"] = entry
        kwargs["risk_pct"] = rng.choice(
            [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, round(rng.uniform(0.1, 5), 2)]
        )
        if mode == "ff":
            kwargs["stop_price"] = round(entry * rng.uniform(0.5, 0.995), rng.choice([2, 3]))
        else:
            kwargs["atr"] = round(entry * rng.uniform(0.005, 0.08), 3)
            kwargs["atr_multiplier"] = rng.choice([1.0, 1.5, 2.0, 2.5, 3.0])
    else:
        kwargs["win_rate"] = round(rng.uniform(0.2, 0.8), 2)
        kwargs["avg_win"] = round(rng.uniform(0.5, 4), 2)
        kwargs["avg_loss"] = round(rng.uniform(0.5, 2), 2)
        if mode != "kelly_budget":
            kwargs["entry_price"] = entry
        if mode == "kelly_shares":
            kwargs["stop_price"] = round(entry * rng.uniform(0.6, 0.99), 2)
    if rng.random() < 0.5:
        kwargs["max_position_pct"] = rng.choice([2, 5, 10, 15, 25, 33.3])
    if rng.random() < 0.4:
        kwargs["max_sector_pct"] = rng.choice([10, 20, 25, 30, 40])
        kwargs["current_sector_exposure"] = rng.choice([0.0, 5.0, 12.5, 22.0, 29.9, 45.0])
    if rng.random() < 0.4:
        kwargs["fractional_shares"] = True
        kwargs["share_precision"] = rng.choice([0, 1, 2, 3, 4, 6, 8])
    return case(**kwargs)


def test_random_sweep_matches_upstream_script():
    rng = random.Random(20261126)
    cases = [_random_case(rng) for _ in range(4000)]
    assert_parity(cases)


def test_cli_combination_errors_are_mirrored():
    """The mirrored argument checks must equal what the real CLI reports."""
    samples = [
        (
            [
                "--account-size",
                "1000",
                "--entry",
                "10",
                "--stop",
                "9",
                "--risk-pct",
                "1",
                "--win-rate",
                "0.5",
            ],
            case(account_size=1000, entry_price=10, stop_price=9, risk_pct=1, win_rate=0.5),
        ),
        (
            ["--account-size", "1000", "--win-rate", "0.5", "--avg-win", "2"],
            case(account_size=1000, win_rate=0.5, avg_win=2),
        ),
        (["--account-size", "1000", "--risk-pct", "1"], case(account_size=1000, risk_pct=1)),
        (
            ["--account-size", "1000", "--risk-pct", "1", "--entry", "10"],
            case(account_size=1000, risk_pct=1, entry_price=10),
        ),
        (["--account-size", "1000"], case(account_size=1000)),
    ]
    for argv, c in samples:
        proc = subprocess.run(
            [sys.executable, str(PY_SCRIPT), "--output-dir", "/dev/null", *argv],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        assert proc.returncode == 2
        assert cli_combination_error(c) in proc.stderr
