import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import zh_batches  # noqa: E402


def _zh():
    return {
        "skills": {"a": {"title": None, "summary": "已有"}},
        "workflows": {"w": {"name": None, "steps": {"1": None}, "manual_review": None}},
    }


WF = [{"id": "w", "steps": [{"step": 1}], "manual_review": ["x", "y"]}]


def test_plan_covers_every_id_once():
    batches = zh_batches.plan()
    skills = [i for k, v in batches.items() if k.startswith("S") for i in v]
    assert (
        len(skills)
        == len(set(skills))
        == len(json.loads((zh_batches.DATA / "skills.json").read_text(encoding="utf-8")))
    )
    assert max(len(v) for k, v in batches.items() if k.startswith("S")) <= 10


def test_valid_fragment_passes():
    frag = {
        "skills": {"a": {"title": "測試"}},
        "workflows": {"w": {"steps": {"1": "第一步"}, "manual_review": ["甲", "乙"]}},
    }
    assert zh_batches.validate(frag, _zh(), WF, False) == []


def test_rejects_unknown_id_overlong_and_filled():
    frag = {"skills": {"zzz": {"title": "x"}, "a": {"title": "字" * 30, "summary": "新"}}}
    errs = zh_batches.validate(frag, _zh(), WF, False)
    text = "\n".join(errs)
    assert "不存在的 skill id" in text
    assert "超過上限" in text
    assert "已有內容" in text


def test_rejects_simplified_hint_and_bad_steps():
    frag = {
        "skills": {"a": {"title": "这个"}},
        "workflows": {"w": {"steps": {"2": "x"}, "manual_review": ["只有一條"]}},
    }
    text = "\n".join(zh_batches.validate(frag, _zh(), WF, False))
    assert "疑似簡體字" in text
    assert "步驟編號" in text
    assert "必須是 2 條" in text


def test_overwrite_allows_filled_field():
    frag = {"skills": {"a": {"summary": "新內容"}}}
    assert zh_batches.validate(frag, _zh(), WF, True) == []


def test_filled_steps_are_not_overwritten():
    zh = _zh()
    zh["workflows"]["w"]["steps"] = {"1": "已翻譯"}
    frag = {"workflows": {"w": {"steps": {"1": "新的"}}}}
    assert "已有內容" in "\n".join(zh_batches.validate(frag, zh, WF, False))


def test_merge_writes_valid_fragment_only(tmp_path, monkeypatch):
    data = tmp_path
    (data / "zh-TW.json").write_text(json.dumps(_zh(), ensure_ascii=False), encoding="utf-8")
    (data / "workflows.json").write_text(json.dumps(WF), encoding="utf-8")
    good = data / "good.json"
    good.write_text(json.dumps({"skills": {"a": {"title": "測試"}}}), encoding="utf-8")
    bad = data / "bad.json"
    bad.write_text(json.dumps({"skills": {"a": {"title": "字" * 30}}}), encoding="utf-8")
    monkeypatch.setattr(zh_batches, "DATA", data)
    assert zh_batches.cmd_merge([str(good), str(bad)], False) == 1
    out = json.loads((data / "zh-TW.json").read_text(encoding="utf-8"))
    assert out["skills"]["a"]["title"] == "測試"


def test_hequn_is_valid_traditional():
    frag = {"workflows": {"w": {"when_not_to_run": "策略核准與批准都不是下單核准"}}}
    assert zh_batches.validate(frag, _zh(), WF, False) == []
