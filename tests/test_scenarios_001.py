"""真实对照实验 001 永久回归（#22）——四场景裁决 + 双实现一致。

负向先行本义：本测试先于 experiments/scenarios-001 存在并失败（模块不存在），
实验脚本并入后必须全绿且每次运行都重新执行真实管线（生成真实日志→转换→裁决）。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

EXPECTED = {
    "S1_same_task_same_model_diff_harness": "ADMISSIBLE",
    "S2_diff_model_diff_harness": "INADMISSIBLE",
    "S3_verified_vs_unresolved_zero": "PARTIAL",
    "S4_trajectory_missing": "INCONCLUSIVE",
}


def test_scenarios_run_and_verdicts():
    from experiments.scenarios_001.run import run_all
    results = run_all()
    scenarios = {k for k in results if not k.startswith("_")}
    assert scenarios == set(EXPECTED), f"场景集漂移: {sorted(scenarios)}"
    for sid, exp in EXPECTED.items():
        got = results[sid]["cdr"]["admissibility"]
        assert got == exp, f"{sid}: 期望 {exp} 实得 {got}"
        # 双实现一致：independent_impl（仅依 SPEC）与参考实现同判
        assert results[sid]["independent"] == exp, \
            f"{sid}: independent_impl 判 {results[sid]['independent']} != 预期 {exp}（规范歧义信号！）"


def test_s2_causal_also_refused():
    from experiments.scenarios_001.run import run_all, adjudicate
    results = run_all()
    case = results["S2_diff_model_diff_harness"]["case"]
    cdr = adjudicate(case, "causal")
    assert cdr.admissibility == "INADMISSIBLE"
    assert any("single_variable" in v for v in cdr.violated_conditions)


def test_real_log_artifact_recorded():
    """真实日志工件必须被记录（路径 + sha256），且 manifest 声明 artifact_observed。"""
    from experiments.scenarios_001.run import run_all
    results = run_all()
    log_info = results["_real_log"]
    assert log_info["path"].endswith(".eval")
    assert log_info["sha256"].startswith("sha256:") and len(log_info["sha256"]) == 71
    man = results["S1_same_task_same_model_diff_harness"]["manifest"]
    assert man["source_kind"] == "experiment-001-mixed"
    assert all(e["verification_state"] == "artifact_observed" for e in man["records"])
    # 诚实标注入清单：synthetic 记录与 mock 模型性质都必须显式声明
    w = " ".join(man["mapping_warnings"])
    assert "synthetic" in w and "mock" in w
