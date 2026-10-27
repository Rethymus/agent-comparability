"""真实对照实验 001（#22）：四类比较场景，经真实管线（#20 转换器 + #16 CLI + 核心）裁决。

数据来源与诚实标注（不可移除）：
  - Inspect 日志为实验内实际运行 inspect_ai.eval 产生（mockllm/model，零 API 调用）。
    真实 EvalLog 工件，但模型输出为 mock 性质——不代表任何真实 Agent 基准表现。
  - 场景 1/2/4 中 harness=manual-json 的对照记录为 synthetic（人工编写，非任何
    harness 实测），其 model 字段取值仅为构造 SPEC §4 场景条件。
  - 场景 3 的 verified/unresolved_zero 差异来自操作者 --status 断言（实验设计的一部分）。

预期独立依据：SPEC §3.3/§4 冻结判定表；并由 independent_impl（仅依规范的独立实现）
交叉验证——两实现不一致即规范歧义信号，须另开 Issue，不得改预期。
"""
import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "conformance"))

from agent_comparability import adjudicate  # noqa: E402
from agent_comparability import evidence  # noqa: E402
from agent_comparability.inspect_log import main as conv_main  # noqa: E402

MOCK_MODEL = "mockllm/model"
_CACHE = None


def _sha256(path):
    return "sha256:" + hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _produce_real_log(tmp: Path) -> str:
    """实际运行 inspect eval 产生真实日志（双样本、目标皆不匹配 → 全部 I → 0.0）。"""
    from inspect_ai import Task, eval
    from inspect_ai.dataset import Sample
    from inspect_ai.scorer import exact
    from inspect_ai.solver import generate
    task = Task(dataset=[Sample(input="exp-Q1", target="deliberately-wrong-1"),
                         Sample(input="exp-Q2", target="deliberately-wrong-2")],
                solver=[generate()], scorer=exact())
    logs = eval(task, model=MOCK_MODEL, log_dir=str(tmp / "logs"))
    assert logs[0].status == "success"
    return str(logs[0].location)


def _convert(log_path, tmp, label, status, tag):
    """经 #20 转换器真实管线产出 case JSON，取样本 1 的记录。"""
    case_path = tmp / f"case-{tag}.json"
    rc = conv_main([log_path, "--claim", "descriptive_registration",
                    "--status", status, "--score-map", "C=1.0,I=0.0",
                    "--task-label", label, "-o", str(tmp / f"cdr-{tag}.json"),
                    "--save-case", str(case_path)])
    assert rc == 0, f"converter failed for {tag}"
    case = json.loads(case_path.read_text(encoding="utf-8"))
    recs = sorted(case["records"], key=lambda r: r["task_id"])
    return recs[0], case


def _authored(tmp, name, task_id, model, reward, status, harness="manual-json", **extra):
    """synthetic 对照记录（诚实来源：manual-json 人工编写），写入真实文件以供摘要实算。"""
    rec = {"task_id": task_id, "harness": harness, "model": model,
           "reward": reward, "reward_status": status}
    rec.update(extra)
    path = tmp / f"authored-{name}.json"
    path.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    return rec, str(path)


def _independent(recs, claim):
    import independent_impl as indep
    return indep.adjudicate(recs, claim)["admissibility"]


def run_all():
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    tmp = Path(tempfile.mkdtemp(prefix="exp001-"))

    log_path = _produce_real_log(tmp)
    log_digest = _sha256(log_path)

    # ---- S1：同任务同模型不同 Harness（真实 inspect 记录 + synthetic manual-json 记录）
    insp1, _ = _convert(log_path, tmp, "exp001", "verified", "s1-insp")
    man1, man1_path = _authored(tmp, "s1", insp1["task_id"], MOCK_MODEL, 1.0, "verified")
    s1_case = {"id": "S1", "records": [insp1, man1]}

    # ---- S2：同任务不同模型不同 Harness（混淆 → 必须正确拒绝）
    insp2, _ = _convert(log_path, tmp, "exp002", "verified", "s2-insp")
    man2, man2_path = _authored(tmp, "s2", insp2["task_id"], "manual-model-b", 1.0, "verified")
    s2_case = {"id": "S2", "records": [insp2, man2]}

    # ---- S3：验证失败与未决零分混合（同一真实日志两种操作者 status 断言，同样本合并）
    v1, _ = _convert(log_path, tmp, "exp003", "verified", "s3-v")
    u1, _ = _convert(log_path, tmp, "exp003", "unresolved_zero", "s3-u")
    s3_case = {"id": "S3", "records": [v1, u1]}

    # ---- S4：证据/轨迹缺失（synthetic 记录 trajectory_available=false，经 #16 CLI 裁决）
    man4, man4_path = _authored(tmp, "s4", "exp004#1", MOCK_MODEL, 0.0, "verified",
                                trajectory_available=False)
    s4_case = {"id": "S4", "records": [man4]}
    s4_in = tmp / "s4-input.json"
    s4_in.write_text(json.dumps(s4_case), encoding="utf-8")
    s4_out = tmp / "s4-cdr.json"
    from agent_comparability.__main__ import main as cli_main
    rc = cli_main([str(s4_in), "--claim", "score_comparison", "-o", str(s4_out)])
    assert rc == 0
    s4_cdr = json.loads(s4_out.read_text(encoding="utf-8"))
    s4_in_str = str(s4_in)

    def verdict(case, claim="score_comparison"):
        cdr = adjudicate(case, claim)
        return cdr, cdr.to_dict()

    results = {}
    for sid, case in (("S1_same_task_same_model_diff_harness", s1_case),
                      ("S2_diff_model_diff_harness", s2_case),
                      ("S3_verified_vs_unresolved_zero", s3_case)):
        cdr, cdrd = verdict(case)
        results[sid] = {"case": case, "cdr": cdrd,
                        "independent": _independent(case["records"], "score_comparison")}
    cdr4 = s4_cdr
    results["S4_trajectory_missing"] = {
        "case": s4_case, "cdr": cdr4,
        "independent": _independent(s4_case["records"], "score_comparison")}

    # S1 的证据清单：两条记录分别锚定真实日志与 synthetic 记录文件（摘要实算）
    s1_man = evidence.build_manifest(
        s1_case, source_kind="experiment-001-mixed",
        artifacts={0: log_path, 1: man1_path},
        requested_claim="score_comparison",
        unsupported_capabilities=["source_side_verification_unavailable",
                                  "verification_tier_absent_in_source",
                                  "manual_records_are_synthetic"])
    s1_man["mapping_warnings"].extend([
        f"record[0]=真实 inspect 日志转换（{log_path}，{log_digest}；mock 模型性质，非真实基准表现）",
        "record[1]=synthetic manual-json 记录（人工编写，非 harness 实测；model 字段取值仅为构造 SPEC §4 场景）",
    ])
    results["S1_same_task_same_model_diff_harness"]["manifest"] = s1_man
    results["_real_log"] = {"path": log_path, "sha256": log_digest}
    results["_artifacts"] = {"s1_manual": man1_path, "s2_manual": man2_path,
                             "s4_input": s4_in_str}
    _CACHE = results
    return results
