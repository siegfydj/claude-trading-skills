#!/usr/bin/env python3
"""Plan, validate and merge zh-TW translation batches for the US-guide.

Several AI agents can translate in parallel without touching data/zh-TW.json:
each agent writes one fragment file under us-guide/data/zh-batches/ and this
script validates the fragments and merges them (fills null fields only).

Usage:
    python3 us-guide/scripts/zh_batches.py plan
    python3 us-guide/scripts/zh_batches.py merge us-guide/data/zh-batches/S01.json [...]
    python3 us-guide/scripts/build_guide.py      # rebuild the page afterwards

Fragment shape (same field names as data/zh-TW.json):
    {"skills": {"<skill-id>": {"title": "...", "summary": "...", ...}},
     "workflows": {"<workflow-id>": {"name": "...", "when_to_run": "...",
                    "when_not_to_run": "...", "steps": {"1": "..."},
                    "manual_review": ["..."]}}}
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "us-guide" / "data"

SKILL_LIMITS = {
    "title": 20,
    "summary": 80,
    "when_to_use": 120,
    "how_to_start": 120,
    "cautions": 120,
}
WORKFLOW_LIMITS = {"name": 40, "when_to_run": 400, "when_not_to_run": 400}
STEP_LIMIT = 80
REVIEW_LIMIT = 200
N_SKILL_BATCHES = 8
N_WORKFLOW_BATCHES = 2

# Heuristic only: common simplified-only characters. A hit means "look again".
SIMPLIFIED_HINTS = set(
    "这个们为产务经对时应开发关业东车长门问间题专书买卖亏损涨线图总结级实验员价额风险"
    "们还让说话认识设计试达远运选择记录属报结构类别组织标准规则样户币资债财务压势"
)


def _load(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def balanced_chunks(items: list[str], n: int) -> list[list[str]]:
    size, extra = divmod(len(items), n)
    out, start = [], 0
    for i in range(n):
        end = start + size + (1 if i < extra else 0)
        out.append(items[start:end])
        start = end
    return out


def plan() -> dict[str, list[str]]:
    skills = sorted(s["id"] for s in _load("skills.json"))
    flows = sorted(w["id"] for w in _load("workflows.json"))
    batches: dict[str, list[str]] = {}
    for i, chunk in enumerate(balanced_chunks(skills, N_SKILL_BATCHES), 1):
        batches[f"S{i:02d}"] = chunk
    for i, chunk in enumerate(balanced_chunks(flows, N_WORKFLOW_BATCHES), 1):
        batches[f"W{i:02d}"] = chunk
    return batches


def _is_filled(value) -> bool:
    """True when a zh-TW slot already holds a translation (null/empty = not filled)."""
    if isinstance(value, dict):
        return any(_is_filled(v) for v in value.values())
    if isinstance(value, list):
        return any(_is_filled(v) for v in value)
    return bool(value)


def _check_text(where: str, value, limit: int, errs: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errs.append(f"{where}: 必須是非空字串")
        return
    if len(value) > limit:
        errs.append(f"{where}: {len(value)} 字，超過上限 {limit}")
    hits = sorted(set(value) & SIMPLIFIED_HINTS)
    if hits:
        errs.append(f"{where}: 疑似簡體字 {''.join(hits)}（請改繁體）")


def validate(frag: dict, zh: dict, workflows: list[dict], overwrite: bool) -> list[str]:
    errs: list[str] = []
    extra = set(frag) - {"skills", "workflows"}
    if extra:
        errs.append(f"未知的頂層欄位：{sorted(extra)}")
    wf_by_id = {w["id"]: w for w in workflows}
    for sid, fields in (frag.get("skills") or {}).items():
        if sid not in zh["skills"]:
            errs.append(f"skills.{sid}: 不存在的 skill id")
            continue
        for key, val in fields.items():
            if key not in SKILL_LIMITS:
                errs.append(f"skills.{sid}.{key}: 未知欄位")
                continue
            _check_text(f"skills.{sid}.{key}", val, SKILL_LIMITS[key], errs)
            if _is_filled(zh["skills"][sid].get(key)) and not overwrite:
                errs.append(f"skills.{sid}.{key}: 已有內容，不覆蓋")
    for wid, fields in (frag.get("workflows") or {}).items():
        wf = wf_by_id.get(wid)
        if wf is None:
            errs.append(f"workflows.{wid}: 不存在的流程 id")
            continue
        for key, val in fields.items():
            where = f"workflows.{wid}.{key}"
            if key in WORKFLOW_LIMITS:
                _check_text(where, val, WORKFLOW_LIMITS[key], errs)
            elif key == "steps":
                want = {str(s["step"]) for s in wf["steps"]}
                if not isinstance(val, dict) or set(val) != want:
                    errs.append(f"{where}: 步驟編號必須剛好是 {sorted(want)}")
                else:
                    for n, text in val.items():
                        _check_text(f"{where}.{n}", text, STEP_LIMIT, errs)
            elif key == "manual_review":
                want_n = len(wf["manual_review"])
                if not isinstance(val, list) or len(val) != want_n:
                    errs.append(f"{where}: 必須是 {want_n} 條的字串陣列")
                else:
                    for i, text in enumerate(val):
                        _check_text(f"{where}[{i}]", text, REVIEW_LIMIT, errs)
            else:
                errs.append(f"{where}: 未知欄位")
            if _is_filled(zh["workflows"].get(wid, {}).get(key)) and not overwrite:
                errs.append(f"{where}: 已有內容，不覆蓋")
    return errs


def merge_fragment(frag: dict, zh: dict) -> None:
    for sid, fields in (frag.get("skills") or {}).items():
        zh["skills"][sid].update(fields)
    for wid, fields in (frag.get("workflows") or {}).items():
        zh["workflows"][wid].update(fields)


def cmd_merge(files: list[str], overwrite: bool) -> int:
    path = DATA / "zh-TW.json"
    zh = json.loads(path.read_text(encoding="utf-8"))
    workflows = _load("workflows.json")
    bad = 0
    merged = 0
    for f in files:
        try:
            frag = json.loads(Path(f).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[略過] {f}: 讀取或 JSON 格式錯誤：{exc}", file=sys.stderr)
            bad += 1
            continue
        errs = validate(frag, zh, workflows, overwrite)
        if errs:
            bad += 1
            print(f"[略過] {f}：{len(errs)} 個問題", file=sys.stderr)
            for e in errs:
                print(f"  - {e}", file=sys.stderr)
            continue
        merge_fragment(frag, zh)
        merged += 1
        print(f"[合併] {f}")
    if merged:
        path.write_text(json.dumps(zh, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"合併 {merged} 個、略過 {bad} 個")
    return 1 if bad else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("plan", help="列出各批次要翻譯的 id")
    m = sub.add_parser("merge", help="驗證並合併片段檔")
    m.add_argument("files", nargs="+")
    m.add_argument("--overwrite", action="store_true", help="允許覆蓋已有的譯文")
    args = ap.parse_args(argv)
    if args.cmd == "plan":
        for name, ids in plan().items():
            print(f"{name} ({len(ids)}): {', '.join(ids)}")
        return 0
    return cmd_merge(args.files, args.overwrite)


if __name__ == "__main__":
    sys.exit(main())
