"""Conformance Suite 运行器：三指标分离（规范 §7），并输出每层独立结果。

指标 1 集成一致性：core 经 Inspect / Pydantic 调用，输出一致（既有 9 案例复核 + B 集）。
  Pydantic 路线的 Evaluator 只检查被评测 task 的真实输出（ctx.output）与冻结预期，
  绝不在评估器内重算判定（#10 P0：重算式评估无法证明 task 输出正确）。
指标 2 规范一致性：independent_impl（依规范）对 A+B 全案例的判定 vs 冻结预期。
指标 3 策略正确性：core 对 A+B 全案例的判定 vs 冻结预期（B 集是 0.2 的 gap 检验，
  允许暴露缺陷——修复须以规范为准，不得改预期）。
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "adapters"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

RELEASE = ROOT / "release"
OUT = ROOT / "conformance-results.json"

from cases import all_pairs  # 共享案例加载器（A+B 全 22 对）——单一事实来源（#8/#10）

from agent_comparability import core
import independent_impl as indep  # 独立实现（规范一致性受检对象）

try:  # 模块级定义以便负向回归测试直接导入（tests/test_gate_regressions.py N5）
    from pydantic_evals.evaluators import Evaluator, EvaluatorContext

    class CDRParity(Evaluator):
        """只检查被评测 task 的真实输出（ctx.output）与冻结预期一致（#10 P0：不得在此重算判定）。"""

        def evaluate(self, ctx: EvaluatorContext) -> float:
            return 1.0 if ctx.output == ctx.expected_output else 0.0
except ImportError:  # 未安装 .[pydantic]：main() 按路线未执行（FAIL）处理
    CDRParity = None


def main() -> int:
    pairs = all_pairs()

    # --- 指标 3：策略正确性（core vs 冻结预期）---
    core_rows = []
    for cid, claim, expected, recs in pairs:
        cdr = core.adjudicate({"id": cid, "records": recs}, claim)
        core_rows.append({"case": cid, "claim": claim, "got": cdr.admissibility,
                          "expected": expected, "ok": cdr.admissibility == expected})
    core_pass = sum(r["ok"] for r in core_rows)

    # --- 指标 2：规范一致性（independent vs 冻结预期）---
    indep_rows = []
    for cid, claim, expected, recs in pairs:
        out = indep.adjudicate(recs, claim)
        indep_rows.append({"case": cid, "claim": claim, "got": out["admissibility"],
                           "expected": expected, "ok": out["admissibility"] == expected})
    indep_pass = sum(r["ok"] for r in indep_rows)

    # --- 指标 1：集成一致性（core 的 CDR 经 Inspect / Pydantic 两条路线分别全量核对）---
    # 两条路线共用同一 22 对案例（cases.py 加载器）；分别报告执行数/通过数/失败原因。
    integ_rows, pyd_rows = [], []
    inspect_executed = pydantic_executed = False
    inspect_err = pyd_err = None
    try:
        import asyncio
        from inspect_ai.scorer import Target
        from inspect_adapter import inspect_adapter
        scorer_obj = inspect_adapter()()
        score_fn = scorer_obj.score if hasattr(scorer_obj, "score") else scorer_obj
        for cid, claim, expected, recs in pairs:
            cdr_direct = core.adjudicate({"id": cid, "records": recs}, claim).to_dict()

            class S:
                metadata = {"cmp_case": {"id": cid, "records": recs}, "requested_claim": claim}
                output = None
                completed = False
            sc = score_fn(S(), Target("x"))
            if hasattr(sc, "__await__"):
                sc = asyncio.new_event_loop().run_until_complete(sc)
            integ_rows.append({"case": cid, "claim": claim,
                               "direct": cdr_direct["admissibility"], "inspect": sc.value,
                               "ok": sc.value == cdr_direct["admissibility"]})
        inspect_executed = True
    except Exception as e:
        inspect_err = f"{type(e).__name__}: {e}"
    try:
        # Pydantic 路线：真实 Dataset/Case/Evaluator 机制逐对执行（与 adapters/pydantic_adapter 同机制）。
        # Evaluator 只检查 task 真实输出（ctx.output）vs 冻结预期——绝不在评估器内重算（#10 P0）。
        if CDRParity is None:
            raise RuntimeError("pydantic_evals 未安装（需 .[pydantic]）")
        from pydantic_evals import Case, Dataset

        ds = Dataset(name="metric1-pydantic",
                     cases=[Case(name=f"{cid}:{claim}", inputs=({"id": cid, "records": recs}, claim),
                                 expected_output=expected)
                            for cid, claim, expected, recs in pairs],
                     evaluators=[CDRParity()])
        rep = ds.evaluate_sync(task=lambda inputs: core.adjudicate(*inputs).admissibility,
                               progress=False)
        for c in rep.cases:
            score = next(iter(c.scores.values())).value
            cid, _, claim = c.name.partition(":")
            pyd_rows.append({"case": cid, "claim": claim, "ok": score == 1.0})
        for f in rep.failures:  # task 执行失败（抛错）同样是失败，不得静默丢失
            cid, _, claim = f.name.partition(":")
            pyd_rows.append({"case": cid, "claim": claim, "ok": False,
                             "error": f.error_message[:80]})
        pydantic_executed = True
    except Exception as e:
        pyd_err = f"{type(e).__name__}: {e}"

    integ_pass = sum(r["ok"] for r in integ_rows) if inspect_executed else None
    pyd_pass = sum(r["ok"] for r in pyd_rows) if pydantic_executed else None
    integration = {
        "inspect": {"executed": inspect_executed, "passed": f"{integ_pass}/{len(pairs)}" if inspect_executed else None,
                    "rows": integ_rows, "error": inspect_err},
        "pydantic": {"executed": pydantic_executed, "passed": f"{pyd_pass}/{len(pairs)}" if pydantic_executed else None,
                     "rows": pyd_rows, "error": pyd_err},
    }

    # --- CDR schema 真实校验（全部 22 个判定输出都必须过 cdr-0.3.1 schema）---
    from jsonschema import Draft202012Validator
    schema = json.loads((ROOT / "spec/cdr.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    schema_fail = []
    for cid, claim, _, recs in pairs:
        d = core.adjudicate({"id": cid, "records": recs}, claim).to_dict()
        errs = sorted(validator.iter_errors(d), key=lambda e: list(e.path))
        if errs:
            schema_fail.append({"case": cid, "claim": claim, "errors": [e.message[:80] for e in errs[:2]]})
    schema_probe = {"validated": len(pairs), "failures": len(schema_fail), "detail": schema_fail[:3]}

    result = {
        "metrics_separated": True,
        "metric3_policy_correctness": {"passed": f"{core_pass}/{len(pairs)}", "rows": core_rows},
        "metric2_spec_conformance": {"passed": f"{indep_pass}/{len(pairs)}", "rows": indep_rows},
        "metric1_integration_consistency": integration,
        "cdr_schema_probe": schema_probe,
        "case_sets": {"A(参与过调试,既有)": 9, "B(新边界,未参与调试)": 13,
                       "D(0.4对称性,#27)": len(pairs) - 22},
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    brief = {k: (v["passed"] if isinstance(v, dict) and "passed" in v else v) for k, v in result.items()
             if k not in ("metrics_separated", "metric1_integration_consistency")}
    brief["metric1_integration_consistency"] = {
        "inspect": integration["inspect"]["passed"], "pydantic": integration["pydantic"]["passed"]}
    print(json.dumps(brief, ensure_ascii=False, indent=1))
    # 失败明细 + 退出码传导（负向门禁 N2 发现：此前恒 return 0，CI 无法察觉判定失败）
    any_fail = core_pass != len(pairs) or indep_pass != len(pairs)
    for m in ("metric3_policy_correctness", "metric2_spec_conformance"):
        fails = [r for r in result[m]["rows"] if not r["ok"]]
        if fails:
            print(f"\n{m} 失败:", [(r["case"], r["claim"], r["got"], "expect=" + r["expected"]) for r in fails])
    if not integration["inspect"]["executed"] or not integration["pydantic"]["executed"]:
        # 任一适配器未执行（依赖缺失/异常）不得静默计为通过——与 N2 同类风险
        print("\nmetric1 集成路线未全部执行（需安装 .[inspect] 与 .[pydantic]）——按 FAIL 处理")
        any_fail = True
    if integ_pass is not None and integ_pass != len(pairs):
        any_fail = True
    if pyd_pass is not None and pyd_pass != len(pairs):
        any_fail = True
    if schema_fail:
        any_fail = True
    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main())
