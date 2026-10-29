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
    assert cdr["policy_version"] == "cmp/0.4.0"
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


# ---------- 多日志比较入口（#26） ----------

_LOG2 = None


def real_log2(model="mockllm/model", inputs=("alt-Q1?", "alt-Q2?")) -> str:
    """第二份真实日志：默认不同样本集；可换模型/输入构造变体。"""
    global _LOG2
    if _LOG2 is None:
        from inspect_ai import Task, eval
        from inspect_ai.dataset import Sample
        from inspect_ai.scorer import exact
        from inspect_ai.solver import generate
        task = Task(dataset=[Sample(input=inputs[0], target="nope-1"),
                             Sample(input=inputs[1], target="nope-2")],
                    solver=[generate()], scorer=exact())
        logs = eval(task, model=model, log_dir="./logs2")
        assert logs[0].status == "success"
        _LOG2 = str(logs[0].location)
    return _LOG2


def _var_log(model, inputs, tag):
    """按需生成变体真实日志（不同模型/样本），不做缓存。单样本输入即单样本日志。"""
    from inspect_ai import Task, eval
    from inspect_ai.dataset import Sample
    from inspect_ai.scorer import exact
    from inspect_ai.solver import generate
    import tempfile, pathlib
    d = pathlib.Path(tempfile.mkdtemp(prefix=f"var-{tag}-"))
    task = Task(dataset=[Sample(input=i, target="deliberately-wrong") for i in inputs],
                solver=[generate()], scorer=exact())
    logs = eval(task, model=model, log_dir=str(d / "logs"))
    assert logs[0].status == "success"
    return str(logs[0].location)


def test_multilog_same_task_two_runs_admissible(tmp_path):
    """同任务两次真实运行（单样本日志 ×2，同 task-label）→ ADMISSIBLE，记录数=2。"""
    a = _var_log("mockllm/model", ("exp-Q1",), "run1")
    b = _var_log("mockllm/model", ("exp-Q1",), "run2")
    c = tmp_path / "case.json"
    m = tmp_path / "m.json"
    r = run_conv(a, b, "--claim", "score_comparison", "--status", "verified",
                 "--score-map", "C=1.0,I=0.0", "--task-label", "same-run",
                 "--save-case", str(c), "--manifest", str(m))
    assert r.returncode == 0, r.stderr
    cdr = json.loads(r.stdout)
    assert cdr["admissibility"] == "ADMISSIBLE"
    case = json.loads(c.read_text(encoding="utf-8"))
    assert len(case["records"]) == 2  # 1 样本 × 2 日志
    assert {x["task_id"] for x in case["records"]} == {"same-run#1"}
    from agent_comparability.evidence import verify_manifest
    man = json.loads(m.read_text(encoding="utf-8"))
    assert verify_manifest(man) == []
    # 每记录制品指向其来源日志（两份不同日志都必须被引用）
    refs = {e["artifact_ref"] for e in man["records"]}
    assert len(refs) == 2


def test_multilog_diff_model_admissible_under_0_4():
    """两单样本日志不同模型（同 harness）→ 仅模型不同 → ADMISSIBLE（cmp/0.4 单变量对称性，#27 裁决 B）。

    0.3.1 时代此场景判 INADMISSIBLE（§3.3-2 把 same_model 列为硬触发）；0.4.0 依 §4 行 2
    语义修正——模型-only 比较由尺度/零语义条件独立把关。same_model 仍在 violated_conditions
    中如实记录（信息项，不再触发裁决）。
    """
    a = _var_log("mockllm/model", ("exp-Q1",), "m1")
    b = _var_log("mockllm/model2", ("exp-Q1",), "m2")
    r = run_conv(a, b, "--claim", "score_comparison", "--status", "verified",
                 "--score-map", "C=1.0,I=0.0", "--task-label", "cmp-models")
    assert r.returncode == 0, r.stderr
    cdr = json.loads(r.stdout)
    assert cdr["admissibility"] == "ADMISSIBLE"  # cmp/0.4.0（#27 方向 B）
    assert "same_model" in cdr["violated_conditions"]  # 如实记录，不触发裁决
    assert "single_variable_isolation" in cdr["satisfied_conditions"]
    assert cdr["policy_version"] == "cmp/0.4.0"


def test_multilog_disjoint_sample_ids_correctly_refused(tmp_path):
    """样本 id 集不同（1 样本 vs 2 样本日志，同 label）→ 跨任务 → INADMISSIBLE + 警告。"""
    a = _var_log("mockllm/model", ("exp-Q1",), "d1")                 # 仅 id=1
    b = _var_log("mockllm/model", ("exp-Q9", "exp-Q8",), "d2")       # id=1,2
    m = tmp_path / "m.json"
    r = run_conv(a, b, "--claim", "score_comparison", "--status", "verified",
                 "--score-map", "C=1.0,I=0.0", "--task-label", "mix", "--manifest", str(m))
    assert r.returncode == 0, r.stderr
    cdr = json.loads(r.stdout)
    assert cdr["admissibility"] == "INADMISSIBLE"
    assert "same_task_id" in cdr["violated_conditions"]
    man = json.loads(m.read_text(encoding="utf-8"))
    assert any("multi_task_merge" in w for w in man["mapping_warnings"])


def test_multilog_whole_logs_pooled_refused():
    """两个多样本日志整体合并（跨题池化）→ INADMISSIBLE——规范拒绝跨题合并比较。"""
    a = _var_log("mockllm/model", ("exp-A1", "exp-A2"), "w1")
    b = _var_log("mockllm/model", ("exp-A1", "exp-A2"), "w2")
    r = run_conv(a, b, "--claim", "score_comparison", "--status", "verified",
                 "--score-map", "C=1.0,I=0.0", "--task-label", "whole")
    assert r.returncode == 0, r.stderr
    cdr = json.loads(r.stdout)
    assert cdr["admissibility"] == "INADMISSIBLE"
    assert "same_task_id" in cdr["violated_conditions"]


def test_multilog_harness_name_count_mismatch_exit2():
    a, b = real_log(), real_log2()
    r = run_conv(a, b, "--claim", "score_comparison", "--status", "verified",
                 "--score-map", "C=1.0,I=0.0", "--task-label", "t",
                 "--harness-name", "h1,h2,h3")
    assert r.returncode == 2
    assert "harness" in r.stderr


def test_multilog_one_unreadable_log_exit2(tmp_path):
    r = run_conv(str(tmp_path / "ghost.eval"), real_log(), "--claim", "score_comparison",
                 "--status", "verified", "--score-map", "C=1.0,I=0.0")
    assert r.returncode == 2
    assert "ghost.eval" in r.stderr


def test_multilog_single_log_still_works():
    """向后兼容：单日志路径行为不变。"""
    r = run_conv(real_log(), "--claim", "descriptive_registration",
                 "--status", "verified", "--score-map", "C=1.0,I=0.0")
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["admissibility"] == "ADMISSIBLE"


# ---------- 真实多-epoch 与 --full-read 验收（#28） ----------

def _epoch_log():
    """真实 epochs=2 日志（实际运行产生；每样本 id 出现于 epoch 1/2）。"""
    from inspect_ai import Task, eval
    from inspect_ai.dataset import Sample
    from inspect_ai.scorer import exact
    from inspect_ai.solver import generate
    import tempfile, pathlib
    d = pathlib.Path(tempfile.mkdtemp(prefix="epoch-"))
    task = Task(dataset=[Sample(input="ep-Q1", target="w1")], solver=[generate()], scorer=exact())
    logs = eval(task, model="mockllm/model", log_dir=str(d / "logs"), epochs=2)
    assert logs[0].status == "success"
    return str(logs[0].location)


def test_real_multiepoch_repetition_count(tmp_path):
    """真实 epochs=2 → 每样本记录 repetition_count=2（真实数据推导，非猜测）。"""
    c = tmp_path / "case.json"
    r = run_conv(_epoch_log(), "--claim", "descriptive_registration",
                 "--status", "verified", "--score-map", "C=1.0,I=0.0",
                 "--task-label", "ep", "--save-case", str(c))
    assert r.returncode == 0, r.stderr
    case = json.loads(c.read_text(encoding="utf-8"))
    assert len(case["records"]) == 2  # 1 样本 × 2 epoch
    assert all(x["repetition_count"] == 2 for x in case["records"])


def test_real_full_read_trajectory_observed(tmp_path):
    """--full-read：实察 messages/events → trajectory_available=true（默认读不声明）。"""
    log = _epoch_log()
    c = tmp_path / "case.json"
    r = run_conv(log, "--claim", "descriptive_registration",
                 "--status", "verified", "--score-map", "C=1.0,I=0.0",
                 "--task-label", "ep", "--full-read", "--save-case", str(c))
    assert r.returncode == 0, r.stderr
    case = json.loads(c.read_text(encoding="utf-8"))
    assert all(x.get("trajectory_available") is True for x in case["records"])
    # 对照：默认 summary 读不声明
    c2 = tmp_path / "case2.json"
    r2 = run_conv(log, "--claim", "descriptive_registration",
                  "--status", "verified", "--score-map", "C=1.0,I=0.0",
                  "--task-label", "ep", "--save-case", str(c2))
    case2 = json.loads(c2.read_text(encoding="utf-8"))
    assert all("trajectory_available" not in x for x in case2["records"])


# ---------- 边界加固：epochs × 多日志合并，与跨日志映射失败定位 ----------

def _var_log_targets(model, pairs, tag, ids=None):
    """按需生成变体真实日志：自定义 (input, target) 对以控制 exact 的 C/I 取值；
    ids 可选，用于让失败样本在转换器诊断中可定位（同 _var_log，不做缓存）。"""
    from inspect_ai import Task, eval
    from inspect_ai.dataset import Sample
    from inspect_ai.scorer import exact
    from inspect_ai.solver import generate
    import tempfile, pathlib
    d = pathlib.Path(tempfile.mkdtemp(prefix=f"var-{tag}-"))
    samples = [Sample(input=i, target=t) if sid is None else Sample(input=i, target=t, id=sid)
               for (i, t), sid in zip(pairs, ids or [None] * len(pairs))]
    task = Task(dataset=samples, solver=[generate()], scorer=exact())
    logs = eval(task, model=model, log_dir=str(d / "logs"))
    assert logs[0].status == "success"
    return str(logs[0].location)


def test_multilog_epochs_log_plus_single_run_merge(tmp_path):
    """多日志 × epochs 组合：epochs=2 日志 + 单样本日志（同 task-label）合并裁决与 repetition_count。

    防回归：(1) 同任务同模型同 harness 的跨日志合并仍是合法 score_comparison（ADMISSIBLE）；
    (2) repetition_count 只按来源日志内统计——epochs=2 日志的记录带 2，单样本日志的记录
    不得编造，更不得跨日志按 task_id 重算（错误重算会得出 3）；(3) 逐记录制品指向保持
    来源忠实（manifest 与 case 记录按序对齐）。
    """
    c = tmp_path / "case.json"
    m = tmp_path / "m.json"
    r = run_conv(_epoch_log(), _var_log("mockllm/model", ("solo-Q1",), "solo"),
                 "--claim", "score_comparison", "--status", "verified",
                 "--score-map", "C=1.0,I=0.0", "--task-label", "merge-ep",
                 "--save-case", str(c), "--manifest", str(m))
    assert r.returncode == 0, r.stderr
    cdr = json.loads(r.stdout)
    assert cdr["admissibility"] == "ADMISSIBLE"       # 同任务+同模型+harness 合并=合法比较
    assert cdr["policy_version"] == "cmp/0.4.0"
    case = json.loads(c.read_text(encoding="utf-8"))
    assert len(case["records"]) == 3                  # 1 样本×2 epoch + 1 样本×1
    assert {x["task_id"] for x in case["records"]} == {"merge-ep#1"}  # task-label 断言生效
    assert [x.get("repetition_count") for x in case["records"]] == [2, 2, None]
    # ↑ 前两条来自 epochs=2 日志（源日志内计 2）；第三条来自单样本日志，不得跨日志重算为 3
    from agent_comparability.evidence import verify_manifest
    man = json.loads(m.read_text(encoding="utf-8"))
    assert verify_manifest(man) == []
    refs = [e["artifact_ref"] for e in man["records"]]
    assert refs[0] == refs[1] != refs[2]              # epoch 对同源日志，第三条来自另一日志
    assert any("multilog_merge" in w for w in man["mapping_warnings"])


def test_multilog_second_log_unmapped_letter_exit2(tmp_path):
    """第二份日志出现未映射字母分数 → exit 2，诊断可定位到该日志的失败样本。

    防回归：多日志循环吞掉或笼统化逐样本映射错误——MappingError 必须带样本级定位，
    操作者才能定位是哪份日志的哪个样本。诊断三要素（PR #36 评审缺口修复后）：
    来源日志路径（路径级定位）+ 失败样本 id（此处为第二份日志独有的显式 id）+
    未映射取值与补救开关。
    """
    from inspect_ai.model._providers.mockllm import MockLLM
    a = _var_log_targets("mockllm/model", [("q1?", "deliberately-wrong")], "umap-a")
    # 日志 A：exact 对 mockllm 错答 → I（在映射表内）
    b = _var_log_targets("mockllm/model", [("q2?", MockLLM.default_output)],
                         "umap-b", ids=["second-log-only"])
    # 日志 B：target=mockllm 默认输出 → exact 得 C（映射表故意只含 I，缺 C）
    sanity = run_conv(a, "--claim", "score_comparison", "--status", "verified",
                      "--score-map", "I=0.0", "--task-label", "umap")
    assert sanity.returncode == 0, sanity.stderr      # 对照：日志 A 单独可过——失败确属日志 B 内容
    r = run_conv(a, b, "--claim", "score_comparison", "--status", "verified",
                 "--score-map", "I=0.0", "--task-label", "umap")
    assert r.returncode == 2                          # 未映射字母 → 程序级失败（exit 2）
    assert b in r.stderr                              # 定位到来源日志路径（多日志哪份出错）
    assert "second-log-only" in r.stderr              # 定位到第二份日志中的失败样本
    assert "'C'" in r.stderr and "score-map" in r.stderr  # 指明未映射取值与补救开关
