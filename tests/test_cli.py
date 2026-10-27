"""CLI（python -m agent_comparability）正常/错误路径回归（#16）。

退出码契约：
  0 = 产出 CDR（四种 admissibility 均为裁决成功，不是程序失败）
  2 = 输入错误（JSON 语法/契约字段缺失或类型错/文件不可读），诊断必须含出错路径
无效输入绝不允许被转换为貌似成功的裁决。
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

VALID = {
    "id": "cli-demo",
    "records": [
        {"task_id": "t1", "harness": "h1", "model": "m1", "reward": 1.0, "reward_status": "verified"},
        {"task_id": "t1", "harness": "h2", "model": "m1", "reward": 0.5, "reward_status": "verified"},
    ],
}


def run_cli(*args):
    return subprocess.run([sys.executable, "-m", "agent_comparability", *args],
                          capture_output=True, text=True, cwd=ROOT)


def _tmp_case(tmp_path, payload, raw=None, name="case.json"):
    p = tmp_path / name
    p.write_text(raw if raw is not None else json.dumps(payload), encoding="utf-8")
    return str(p)


def test_valid_input_exit0_admissible(tmp_path):
    r = run_cli(_tmp_case(tmp_path, VALID), "--claim", "score_comparison")
    assert r.returncode == 0, r.stderr
    cdr = json.loads(r.stdout)
    assert cdr["admissibility"] == "ADMISSIBLE"
    assert cdr["policy_version"] == "cmp/0.4.0"
    assert any("抗恶意篡改" in l for l in cdr["limitations"])
    for k in ("case_id", "requested_claim", "satisfied_conditions", "violated_conditions",
              "unknown_conditions", "supported_claims", "unsupported_claims",
              "evidence_refs", "comparison_scope"):
        assert k in cdr


@pytest.mark.parametrize("claim,expected", [
    ("causal", "INADMISSIBLE"),
    ("score_comparison", "ADMISSIBLE"),
])
def test_all_verdicts_are_exit0_not_program_failure(tmp_path, claim, expected):
    """INADMISSIBLE/PARTIAL/INCONCLUSIVE 与 ADMISSIBLE 同为 exit 0 —— 裁决 ≠ 程序失败。"""
    r = run_cli(_tmp_case(tmp_path, VALID), "--claim", claim)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["admissibility"] == expected


def test_inconclusive_and_partial_exit0(tmp_path):
    miss = {"id": "m", "records": [dict(VALID["records"][0], trajectory_available=False)]}
    r = run_cli(_tmp_case(tmp_path, miss, name="miss.json"), "--claim", "score_comparison")
    assert r.returncode == 0 and json.loads(r.stdout)["admissibility"] == "INCONCLUSIVE"
    mixed = {"id": "x", "records": [
        {"task_id": "t", "harness": "a", "model": "m", "reward": 0.0, "reward_status": "verified"},
        {"task_id": "t", "harness": "b", "model": "m", "reward": 0.0, "reward_status": "unresolved_zero"}]}
    r2 = run_cli(_tmp_case(tmp_path, mixed, name="mixed.json"), "--claim", "score_comparison")
    assert r2.returncode == 0 and json.loads(r2.stdout)["admissibility"] == "PARTIAL"


def test_unknown_claim_type_exit0_inconclusive(tmp_path):
    r = run_cli(_tmp_case(tmp_path, VALID), "--claim", "leaderboard_ranking")
    assert r.returncode == 0
    cdr = json.loads(r.stdout)
    assert cdr["admissibility"] == "INCONCLUSIVE"
    assert any("unrecognized_claim_type" in u for u in cdr["unknown_conditions"])


def test_unknown_fields_not_error_but_recorded(tmp_path):
    """SPEC §5：未知字段必须忽略（不报错）并记入 unknown_conditions —— CLI 不得比规范更严。"""
    payload = json.loads(json.dumps(VALID))
    payload["records"][0]["custom_extra"] = "keep-me-ignored"
    r = run_cli(_tmp_case(tmp_path, payload), "--claim", "score_comparison")
    assert r.returncode == 0, r.stderr
    cdr = json.loads(r.stdout)
    assert cdr["admissibility"] == "ADMISSIBLE"
    assert any("ignored_fields" in u and "custom_extra" in u for u in cdr["unknown_conditions"])


def test_output_file_flag(tmp_path):
    out = tmp_path / "cdr.json"
    r = run_cli(_tmp_case(tmp_path, VALID), "--claim", "score_comparison", "-o", str(out))
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == ""
    cdr = json.loads(out.read_text(encoding="utf-8"))
    assert cdr["admissibility"] == "ADMISSIBLE"


# ---------- 错误路径：全部 exit 2 + 诊断含路径 ----------

def test_missing_input_file_exit2(tmp_path):
    r = run_cli(str(tmp_path / "nope.json"), "--claim", "score_comparison")
    assert r.returncode == 2
    assert "nope.json" in r.stderr


def test_malformed_json_exit2(tmp_path):
    r = run_cli(_tmp_case(tmp_path, None, raw="{not valid json"), "--claim", "score_comparison")
    assert r.returncode == 2
    assert "JSON" in r.stderr


@pytest.mark.parametrize("payload,needle", [
    ({"records": VALID["records"]}, "id"),                                   # 缺 id
    ({"id": "x"}, "records"),                                                # 缺 records
    ({"id": "x", "records": []}, "records"),                                 # 空 records
    ({"id": 42, "records": VALID["records"]}, "id"),                         # id 类型错
    ({"id": "x", "records": [{"harness": "h", "model": "m", "reward": 1.0,
                              "reward_status": "verified"}]}, "task_id"),    # 缺必填字段
    ({"id": "x", "records": [dict(VALID["records"][0], reward="high")]}, "reward"),        # reward 类型错
    ({"id": "x", "records": [dict(VALID["records"][0], reward=True)]}, "reward"),          # bool 不是数值
    ({"id": "x", "records": [dict(VALID["records"][0], reward_status=0)]}, "reward_status"),  # status 类型错
])
def test_contract_violations_exit2_with_path(tmp_path, payload, needle):
    r = run_cli(_tmp_case(tmp_path, payload), "--claim", "score_comparison")
    assert r.returncode == 2, f"期望 exit 2，实际 {r.returncode}；stdout={r.stdout!r}"
    assert needle in r.stderr, r.stderr
    assert "records[0]" in r.stderr or needle == "records" or needle == "id" and "records" not in r.stderr


def test_bad_optional_field_types_exit2(tmp_path):
    rec = dict(VALID["records"][0], trajectory_available="yes")
    r = run_cli(_tmp_case(tmp_path, {"id": "x", "records": [rec]}), "--claim", "score_comparison")
    assert r.returncode == 2 and "trajectory_available" in r.stderr
    rec2 = dict(VALID["records"][0], score_scale="0..1")
    r2 = run_cli(_tmp_case(tmp_path, {"id": "x", "records": [rec2]}, name="c2.json"),
                 "--claim", "score_comparison")
    assert r2.returncode == 2 and "score_scale" in r2.stderr
    rec3 = dict(VALID["records"][0], repetition_count=0)
    r3 = run_cli(_tmp_case(tmp_path, {"id": "x", "records": [rec3]}, name="c3.json"),
                 "--claim", "score_comparison")
    assert r3.returncode == 2 and "repetition_count" in r3.stderr


def test_missing_claim_flag_exit2(tmp_path):
    r = run_cli(_tmp_case(tmp_path, VALID))
    assert r.returncode == 2  # argparse required 参数缺失 → 2（argparse 惯例），不得默认猜 claim


def test_no_args_exit2():
    assert run_cli().returncode == 2
