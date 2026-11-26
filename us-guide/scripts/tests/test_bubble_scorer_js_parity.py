"""Parity test: the browser version of the bubble scorer must match the upstream script.

`us-guide/tools/bubble_scorer.js` ports `BubbleScorer.calculate_score()` and `format_output()`
from `skills/us-market-bubble-detector/scripts/bubble_scorer.py`. Every valid score combination
(3**6 * 2**3 = 5,832, flat and nested form) plus invalid inputs must give identical results,
error messages and text report (the timestamp is excluded).

Not covered on purpose: the command line and interactive mode; JSON 1.0 (Python float) cannot be
told from 1 in JavaScript.

Run: python3 -m pytest us-guide/scripts/tests/test_bubble_scorer_js_parity.py
Needs `node` on PATH; the test is skipped when it is missing.
"""

from __future__ import annotations

import importlib.util
import itertools
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
PY_SCRIPT = ROOT / "skills" / "us-market-bubble-detector" / "scripts" / "bubble_scorer.py"
JS_RUNNER = ROOT / "us-guide" / "tools" / "tests" / "run_bubble_parity.js"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def _load_upstream():
    spec = importlib.util.spec_from_file_location("upstream_bubble_scorer", PY_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


up = _load_upstream()
SCORER = up.BubbleScorer()
QKEYS = list(SCORER.quantitative_indicators)
LKEYS = list(SCORER.qualitative_adjustments)


def run_python(quant, qual):
    try:
        result = SCORER.calculate_score(quant, qual)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    text = SCORER.format_output(result).replace(result["timestamp"], "GEN")
    del result["timestamp"]
    return {"ok": True, "result": result, "text": text}


def run_js(cases):
    proc = subprocess.run(
        ["node", str(JS_RUNNER)],
        input=json.dumps(cases),
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    return json.loads(proc.stdout)


def _compare(cases):
    js = run_js(cases)
    assert len(js) == len(cases)
    for c, got in zip(cases, js):
        assert got == run_python(c["quant"], c["qual"]), c


def _valid(q, n):
    return dict(zip(QKEYS, q)), dict(zip(LKEYS, n))


def test_every_valid_combination_nested_and_flat():
    cases = []
    for q in itertools.product(range(3), repeat=6):
        for n in itertools.product(range(2), repeat=3):
            quant, qual = _valid(q, n)
            cases.append({"quant": quant, "qual": qual})
            cases.append({"quant": {**quant, **qual}, "qual": None})
    assert len(cases) == 5832 * 2
    _compare(cases)


def test_every_total_percentage_matches():
    # 0..15 -> the rounding of total/15*100 must be identical
    cases = []
    for total in range(16):
        q = [min(2, max(0, total - 2 * i)) for i in range(6)]
        rest = total - sum(q)
        n = [1 if i < rest else 0 for i in range(3)]
        quant, qual = _valid(q, n)
        cases.append({"quant": quant, "qual": qual})
    _compare(cases)


def test_key_order_is_preserved_in_details():
    quant = dict(reversed(list(_valid([1, 0, 2, 1, 0, 2], [0, 0, 0])[0].items())))
    qual = dict(reversed(list(_valid([0] * 6, [1, 0, 1])[1].items())))
    _compare([{"quant": quant, "qual": qual}, {"quant": {**qual, **quant}, "qual": None}])


BASE_Q = dict.fromkeys(QKEYS, 1)
BASE_L = dict.fromkeys(LKEYS, 0)


def _bad(**over):
    return {**BASE_Q, **over}


def test_invalid_inputs_give_same_errors():
    cases = [
        {"quant": {}, "qual": {}},
        {"quant": {}, "qual": None},
        {"quant": BASE_Q, "qual": {}},
        {"quant": {k: v for k, v in BASE_Q.items() if k != "leverage"}, "qual": BASE_L},
        {"quant": {**BASE_Q, "extra": 1}, "qual": BASE_L},
        {"quant": {**BASE_Q, "alpha": 1, "zeta": 0}, "qual": BASE_L},
        {"quant": BASE_Q, "qual": {**BASE_L, "social_penetration": 2}},
        {"quant": BASE_Q, "qual": {**BASE_L, "nope": 0}},
        {"quant": {**BASE_Q, **BASE_L, "mystery": 1}, "qual": None},
        {"quant": {**BASE_Q, "leverage": 3}, "qual": BASE_L},
        {"quant": {**BASE_Q, "leverage": -1}, "qual": BASE_L},
        {"quant": {**BASE_Q, "leverage": 1.5}, "qual": BASE_L},
        {"quant": {**BASE_Q, "leverage": True}, "qual": BASE_L},
        {"quant": {**BASE_Q, "leverage": "1"}, "qual": BASE_L},
        {"quant": {**BASE_Q, "leverage": None}, "qual": BASE_L},
        {"quant": {**BASE_Q, "ipo_heat": 9, "leverage": "x"}, "qual": BASE_L},
        {"quant": {**BASE_Q, "leverage": 1}, "qual": {**BASE_L, "media_search_trends": 1.5}},
        {"quant": {**BASE_Q, "leverage": 1}, "qual": {**BASE_L, "media_search_trends": False}},
        {"quant": {**BASE_Q, **BASE_L}, "qual": None},
        {"quant": {**BASE_Q, **BASE_L, "leverage": 7}, "qual": None},
        {"quant": {**BASE_Q, **{"social_penetration": True}}, "qual": None},
    ]
    _compare(cases)
