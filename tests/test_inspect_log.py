"""Inspect EvalLog 转换器回归（#20）——真实日志验收 + 显式映射政策负向路径。

fixture 实际运行 inspect eval（mockllm/model，零 API 调用）产生 .eval——
验收用真实日志，非手写模拟（#20 验收标准）。
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

_LOG_PATH = None


def real_log() -> str:
    """session 级真实日志：实际运行 inspect eval 产生。"""
    global _LOG_PATH
    if _LOG_PATH is None:
        from inspect_ai import Task, eval
        from inspect_ai.dataset import Sample
        from inspect_ai.scorer import exact
        from inspect_ai.solver import generate
        task = Task(dataset=[Sample(input="2+2?", target="4"),
                             Sample(input="3+3?", target="6")],
                    solver=[generate()], scorer=exact())
        logs = eval(task, model="mockllm/model", log_dir="./logs")
        assert logs[0].status == "success"
        _LOG_PATH = str(logs[0].location)
    return _LOG_PATH


def run_conv(*args):
    return subprocess.run([sys.executable, "-m", "agent_comparability.inspect_log", *args],
                          capture_output=True, text=True, cwd=ROOT)


def test_real_log_descriptive_registration_admissible(tmp_path):
    """真实日志：登记主张 exit 0 ADMISSIBLE + manifest 逐项正确。"""
    m = tmp_path / "m.json"
    r = run_conv(real_log(), "--claim", "descriptive_registration",
                 "--status", "verified", "--score-map", "C=1.0,I=0.0",
                 "--manifest", str(m))
    assert r.returncode == 0, r.stderr
    cdr = json.loads(r.stdout)
    assert cdr["admissibility"] == "ADMISSIBLE"
    assert cdr["policy_version"] == "cmp/0.3.1"
    man = json.loads(m.read_text(encoding="utf-8"))
    assert man["source_kind"] == "inspect_evallog"
    assert man["source_version"]
    assert len(man["records"]) == 2
    assert all(e["verification_state"] == "artifact_observed" for e in man["records"])
    assert all(e["file_digest"].startswith("sha256:") for e in man["records"])
    # 全部映射决策必须显式入警告：status 断言 / 字母映射 / 任务身份来源 / summary 读
    w = " ".join(man["mapping_warnings"])
    assert "reward_status_asserted_by_operator" in w
    assert "score_map_applied" in w
    assert "task_identity_source" in w
    assert "trajectory_not_inspected" in w
    assert "verification_tier_absent_in_source" in " ".join(man["unsupported_capabilities"])


def test_real_log_score_comparison_correctly_refused(tmp_path):
    """真实日志：同日志不同样本=不同任务 → score_comparison INADMISSIBLE（exit 0）。
    核心验收：系统正确拒绝无依据的比较，而非追求 ADMISSIBLE。"""
    r = run_conv(real_log(), "--claim", "score_comparison",
                 "--status", "verified", "--score-map", "C=1.0,I=0.0")
    assert r.returncode == 0, r.stderr
    cdr = json.loads(r.stdout)
    assert cdr["admissibility"] == "INADMISSIBLE"
    assert "same_task_id" in cdr["violated_conditions"]


def test_real_log_records_honest_fields(tmp_path):
    """记录字段如实：model 原样 mockllm/model、harness=inspect-ai、reward=映射后 0.0。"""
    c = tmp_path / "case.json"
    r = run_conv(real_log(), "--claim", "descriptive_registration",
                 "--status", "verified", "--score-map", "C=1.0,I=0.0",
                 "--save-case", str(c))
    assert r.returncode == 0, r.stderr
    case = json.loads(c.read_text(encoding="utf-8"))
    recs = case["records"]
    assert all(x["model"] == "mockllm/model" for x in recs)
    assert all(x["harness"] == "inspect-ai" for x in recs)
    assert all(x["reward"] == 0.0 for x in recs)  # exact 打分为 I → 显式映射
    assert all("trajectory_available" not in x for x in recs)  # summary 读不声明
    tids = {x["task_id"] for x in recs}
    assert len(tids) == 2  # 逐样本粒度：不同样本=不同任务


def test_missing_status_flag_exit2():
    r = run_conv(real_log(), "--claim", "score_comparison", "--score-map", "C=1.0,I=0.0")
    assert r.returncode == 2
    assert "--status" in r.stderr


def test_letter_score_without_map_exit2():
    r = run_conv(real_log(), "--claim", "score_comparison", "--status", "verified")
    assert r.returncode == 2
    assert "score-map" in r.stderr and "I" in r.stderr


def test_unknown_scorer_exit2():
    r = run_conv(real_log(), "--claim", "descriptive_registration", "--status", "verified",
                 "--score-map", "C=1.0,I=0.0", "--scorer", "nonexistent")
    assert r.returncode == 2
    assert "nonexistent" in r.stderr


def test_nonexistent_log_exit2(tmp_path):
    r = run_conv(str(tmp_path / "ghost.eval"), "--claim", "descriptive_registration",
                 "--status", "verified")
    assert r.returncode == 2
    assert "ghost.eval" in r.stderr


def test_missing_dependency_clear_error(tmp_path, monkeypatch):
    """缺 inspect_ai：明确 exit 2 诊断，绝不裸 traceback（§7 缺失依赖案例）。"""
    import agent_comparability.inspect_log as il
    monkeypatch.setattr(sys, "modules", {**sys.modules, "inspect_ai": None, "inspect_ai.log": None})
    code = ("import sys; sys.modules['inspect_ai']=None; sys.modules['inspect_ai.log']=None;"
            f"from agent_comparability.inspect_log import main;"
            f"sys.exit(main([{str(real_log())!r}, '--claim', 'descriptive_registration',"
            f" '--status', 'verified']))")
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 2, (r.stdout, r.stderr)
    assert "inspect" in r.stderr.lower() and "install" in r.stderr.lower()


def test_pure_mapping_rules():
    """映射规则单元级：数值透传免映射 / 字母无映射拒绝 / 映射生效 / epoch 计 repetition。"""
    from inspect_ai.log import EvalSampleSummary  # noqa: F401  (确认官方类型存在)
    from agent_comparability.inspect_log import records_from_summaries, MappingError

    class S:  # 构造 summary 形状（字段与官方 EvalSampleSummary 一致）
        def __init__(self, id, epoch, value):
            self.id, self.epoch = id, epoch
            class _Sc:
                pass
            sc = _Sc(); sc.value = value; sc.answer = None
            self.scores = {"s": sc}; self.error = None; self.completed = True

    # 数值透传：无需 score-map
    recs = records_from_summaries([S(1, 1, 0.75), S(2, 1, 1.0)], scorer="s", status="verified",
                                  task_label="T", harness="inspect-ai")
    assert [x["reward"] for x in recs] == [0.75, 1.0]
    # 字母无映射 → MappingError
    with pytest.raises(MappingError):
        records_from_summaries([S(1, 1, "I")], scorer="s", status="verified",
                               task_label="T", harness="h")
    # 显式映射生效
    recs2 = records_from_summaries([S(1, 1, "I")], scorer="s", status="verified",
                                   task_label="T", harness="h", score_map={"I": 0.0, "C": 1.0})
    assert recs2[0]["reward"] == 0.0
    # 同 id 双 epoch → repetition_count=2（真实数据，非猜测）
    recs3 = records_from_summaries([S(1, 1, 1.0), S(1, 2, 0.0)], scorer="s", status="verified",
                                   task_label="T", harness="h")
    assert all(x["repetition_count"] == 2 for x in recs3)
    # error 样本被跳过（不编造 reward）
    s_err = S(3, 1, 1.0); s_err.error = "boom"
    recs4 = records_from_summaries([S(1, 1, 1.0), s_err], scorer="s", status="verified",
                                   task_label="T", harness="h")
    assert all("t?3" not in x["task_id"] for x in recs4) and len(recs4) == 1


def test_cli_manifest_verifies_clean(tmp_path):
    from agent_comparability.evidence import verify_manifest
    m = tmp_path / "m.json"
    r = run_conv(real_log(), "--claim", "descriptive_registration", "--status", "verified",
                 "--score-map", "C=1.0,I=0.0", "--manifest", str(m))
    assert r.returncode == 0, r.stderr
    man = json.loads(m.read_text(encoding="utf-8"))
    assert verify_manifest(man) == []
