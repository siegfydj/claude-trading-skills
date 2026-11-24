#!/usr/bin/env python3
"""Build the US-guide dashboard data and the self-contained index.html.

Reads (read-only): skills-index.yaml, workflows/*.yaml, skillsets/*.yaml, skills/*/
Writes: us-guide/data/{skills,workflows,skillsets}.json and us-guide/index.html
Preserves: us-guide/data/zh-TW.json (translation overlay; only missing keys are added)

Usage:
    python3 us-guide/scripts/build_guide.py
Re-run after syncing upstream. No network access, no API keys.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write("PyYAML is required: pip install pyyaml\n")
    sys.exit(2)

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "us-guide"
DATA = GUIDE / "data"
REPO_URL = "https://github.com/siegfydj/claude-trading-skills"

PAID_KEYS = {"fmp", "finviz", "alpaca"}
FREE_PUBLIC = {"public_csv", "coingecko", "yfinance", "binance_funding", "fxmacrodata"}
LLM_NEEDS = {"websearch", "chart_image"}
# Not US-equity trading: surfaced but tagged so the dashboard can hide them.
NON_EQUITY = {
    "crypto-regime-analyzer",
    "cot-contrarian-detector",
    "futures-position-sizer",
    "contrarian-setup-gate",
    "mt5-robot-tester",
    "fxmacrodata-calendar",
    "news-reaction-failure-analyzer",
    "manifoldbt-backtester",
}
MAINTAINER_ONLY = {
    "skill-designer",
    "skill-idea-miner",
    "skill-integration-tester",
    "dual-axis-skill-reviewer",
}

TIER_LABELS = {
    "A": "純計算（可離線；部分有選用金鑰）",
    "B": "公開資料（免付費金鑰）",
    "C": "需付費金鑰（FMP／FINVIZ／Alpaca）",
    "D": "需 LLM 判讀（網搜／圖表／無腳本）",
}


def load_yaml(path: Path):
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def script_entrypoints(skill_id: str) -> list[str]:
    sdir = ROOT / "skills" / skill_id / "scripts"
    if not sdir.is_dir():
        return []
    out = []
    for p in sorted(sdir.glob("*.py")):
        if p.name.startswith("_") or p.name in {"__init__.py", "conftest.py"}:
            continue
        out.append(p.name)
    return out


def classify(skill: dict, scripts: list[str]) -> str:
    integ = skill.get("integrations") or []
    req_items = [i for i in integ if i.get("requirement") == "required"]
    required = {i["id"] for i in req_items}
    # Required web research (SEC filings, IR pages, news, ...) needs an LLM to read it.
    needs_web = any(i.get("type") == "web" and i["id"] not in FREE_PUBLIC for i in req_items)
    if not scripts or required & LLM_NEEDS or needs_web:
        return "D"
    if required & PAID_KEYS:
        return "C"
    if required & FREE_PUBLIC:
        return "B"
    return "A"


def verification_score(skill: dict) -> tuple[int, int]:
    ver = skill.get("verification") or {}
    applicable = [v for v in ver.values() if v != "not_applicable"]
    passed = [v for v in applicable if v == "passed"]
    return len(passed), len(applicable)


def build_skills() -> list[dict]:
    index = load_yaml(ROOT / "skills-index.yaml")
    rows = []
    for s in index["skills"]:
        sid = s["id"]
        scripts = script_entrypoints(sid)
        passed, total = verification_score(s)
        integ = s.get("integrations") or []
        rows.append(
            {
                "id": sid,
                "name": s.get("display_name", sid),
                "category": s.get("category"),
                "status": s.get("status"),
                "summary": s.get("summary", ""),
                "timeframe": s.get("timeframe"),
                "difficulty": s.get("difficulty"),
                "inputs": s.get("inputs") or [],
                "outputs": s.get("outputs") or [],
                "workflows": s.get("workflows") or [],
                "integrations": [
                    {
                        "id": i["id"],
                        "type": i.get("type"),
                        "requirement": i.get("requirement"),
                        "note": i.get("note", ""),
                    }
                    for i in integ
                ],
                "scripts": scripts,
                "tier": classify(s, scripts),
                "optional_keys": sorted(
                    {
                        i["id"]
                        for i in integ
                        if i["id"] in PAID_KEYS and i.get("requirement") != "required"
                    }
                ),
                "verified": {"passed": passed, "applicable": total},
                "audience": "maintainer" if sid in MAINTAINER_ONLY else "trader",
                "us_equity": sid not in NON_EQUITY and sid not in MAINTAINER_ONLY,
                "links": {
                    "skill_md": f"{REPO_URL}/blob/main/skills/{sid}/SKILL.md",
                    "doc_en": f"{REPO_URL}/blob/main/docs/en/skills/{sid}.md",
                },
            }
        )
    return rows


def build_workflows() -> list[dict]:
    rows = []
    for f in sorted((ROOT / "workflows").glob("*.yaml")):
        w = load_yaml(f)
        rows.append(
            {
                "id": w["id"],
                "name": w.get("display_name", w["id"]),
                "cadence": w.get("cadence"),
                "minutes": w.get("estimated_minutes"),
                "difficulty": w.get("difficulty"),
                "api_profile": w.get("api_profile"),
                "when_to_run": " ".join(str(w.get("when_to_run", "")).split()),
                "when_not_to_run": " ".join(str(w.get("when_not_to_run", "")).split()),
                "required_skills": w.get("required_skills") or [],
                "optional_skills": w.get("optional_skills") or [],
                "steps": [
                    {
                        "step": st.get("step"),
                        "name": st.get("name"),
                        "skill": st.get("skill"),
                        "optional": bool(st.get("optional")),
                        "decision_gate": bool(st.get("decision_gate")),
                        "question": " ".join(str(st.get("decision_question", "")).split()),
                    }
                    for st in (w.get("steps") or [])
                ],
                "manual_review": w.get("manual_review") or [],
            }
        )
    return rows


def build_skillsets() -> list[dict]:
    rows = []
    for f in sorted((ROOT / "skillsets").glob("*.yaml")):
        s = load_yaml(f)
        rows.append(
            {
                "id": s["id"],
                "name": s.get("display_name", s["id"]),
                "difficulty": s.get("difficulty"),
                "api_profile": s.get("api_profile"),
                "when_to_use": " ".join(str(s.get("when_to_use", "")).split()),
                "required": s.get("required_skills") or [],
                "recommended": s.get("recommended_skills") or [],
                "optional": s.get("optional_skills") or [],
            }
        )
    return rows


ZH_FIELDS = ("title", "summary", "when_to_use", "how_to_start", "cautions")
ZH_WORKFLOW_FIELDS = ("name", "when_to_run", "when_not_to_run")


def sync_zh(skills: list[dict], workflows: list[dict]) -> dict:
    """Create/extend the zh-TW overlay without overwriting translated text.

    Shape: {"skills": {id: {...}}, "workflows": {id: {name, when_to_run,
    when_not_to_run, steps: {"<n>": "<step name>"}, manual_review: [..]}}}
    """
    path = DATA / "zh-TW.json"
    zh = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if "skills" not in zh:  # migrate flat v0 layout
        zh = {"skills": {k: v for k, v in zh.items() if isinstance(v, dict)}, "workflows": {}}
    zs = zh.setdefault("skills", {})
    for s in skills:
        entry = zs.setdefault(s["id"], {})
        for field in ZH_FIELDS:
            entry.setdefault(field, None)
    zw = zh.setdefault("workflows", {})
    for w in workflows:
        entry = zw.setdefault(w["id"], {})
        for field in ZH_WORKFLOW_FIELDS:
            entry.setdefault(field, None)
        steps = entry.setdefault("steps", {})
        for st in w["steps"]:
            steps.setdefault(str(st["step"]), None)
        entry.setdefault("manual_review", None)
    return zh


def dump(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def render_html(payload: dict) -> str:
    template = (GUIDE / "scripts" / "template.html").read_text(encoding="utf-8")
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    blob = blob.replace("</", "<\\/")  # keep inline JSON from closing the tag
    return template.replace("/*__GUIDE_DATA__*/null", blob)


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    skills = build_skills()
    workflows = build_workflows()
    skillsets = build_skillsets()
    zh = sync_zh(skills, workflows)
    dump(DATA / "skills.json", skills)
    dump(DATA / "workflows.json", workflows)
    dump(DATA / "skillsets.json", skillsets)
    dump(DATA / "zh-TW.json", zh)
    payload = {
        "skills": skills,
        "workflows": workflows,
        "skillsets": skillsets,
        "zh": zh,
        "tierLabels": TIER_LABELS,
        "repo": REPO_URL,
    }
    (GUIDE / "index.html").write_text(render_html(payload), encoding="utf-8")
    tiers: dict[str, int] = {}
    for s in skills:
        tiers[s["tier"]] = tiers.get(s["tier"], 0) + 1
    translated = sum(1 for v in zh["skills"].values() if v.get("summary"))
    print(f"skills={len(skills)} workflows={len(workflows)} skillsets={len(skillsets)}")
    print("tiers:", dict(sorted(tiers.items())))
    print(f"zh-TW translated: {translated}/{len(skills)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
