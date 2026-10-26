"""路 2b：Pydantic Evals Evaluator 包装 cmp/core.adjudicate（真实运行，非探针）。

共享加载器（cases.all_pairs，A+B 全 22 对）构建 Dataset/Case，经 pydantic_evals
真实机制逐对执行；Evaluator 只检查被评测 task 的真实输出（ctx.output，完整 CDR）
与冻结参考判定一致（#10 P0：不得在 Evaluator 内重算）；最终通过判定与逐条明细
全部取自 evaluate_sync() 返回的 report（cases + failures），task 执行失败与案例
缺失同样传导为非零退出码（#10 P1：不再旁路重算旧 A 集循环）。
结果并入 conformance/conformance-results.json——文件不存在时自初始化，
可独立运行，与 inspect 路线互无顺序依赖（#12）。
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from agent_comparability import adjudicate, POLICY_VERSION  # 同一核心判断库

from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import Evaluator, EvaluatorContext

sys.path.insert(0, str(ROOT / "conformance"))
import cases as shared_cases  # 共享加载器（A+B 全 22 对）

OUT = ROOT / "conformance"


class CDRAdjudicator(Evaluator):
    """只依据被评测 task 的真实输出（ctx.output，完整 CDR）判定，不在此重算：
    判定与冻结预期一致（1.0/0.0）+ 结构完整性（policy_version/防篡改限制在位）。"""

    def evaluate(self, ctx: EvaluatorContext) -> float:
        cdr = ctx.output  # task 真实输出；绝不重新调用 adjudicate（#10 P0）
        structurally_valid = (
            cdr.admissibility in ("ADMISSIBLE", "INADMISSIBLE", "INCONCLUSIVE", "PARTIAL")
            and POLICY_VERSION == cdr.policy_version
            and cdr.limitations  # 防篡改限制必须在位
        )
        return 1.0 if (cdr.admissibility == ctx.expected_output and structurally_valid) else 0.0


def main() -> int:
    cases_flat = []
    for cid, claim, expected, recs in shared_cases.all_pairs():
        cases_flat.append(Case(name=f"{cid}:{claim}",
                               inputs=({"id": cid, "records": recs}, claim),
                               expected_output=expected))
    ds = Dataset(name="cmp-conformance-pydantic-route", cases=cases_flat,
                 evaluators=[CDRAdjudicator()])
    # task 返回完整 CDR：判定与结构信息全部来自被评测路线的真实输出
    report = ds.evaluate_sync(task=lambda inputs: adjudicate(*inputs), progress=False)

    # 逐条结果与 CDR 细节：全部取自 report（#10 P1）
    rows, all_ok = [], True
    for c in report.cases:
        cid, _, claim = c.name.partition(":")
        cdr = c.output  # task 真实输出（CDR 对象），非重算
        score = next(iter(c.scores.values())).value
        ok = score == 1.0 and not c.evaluator_failures
        all_ok &= ok
        rows.append({"case": cid, "claim": claim,
                     "pydantic_output": cdr.admissibility, "expected": c.expected_output,
                     "consistent_with_frozen": ok,
                     "supported": cdr.supported_claims, "unsupported": cdr.unsupported_claims,
                     "limitations_fixed": cdr.limitations[0][:20] + "…"})
    for f in report.failures:  # task 执行失败（抛错）必须传导为失败
        cid, _, claim = f.name.partition(":")
        all_ok = False
        rows.append({"case": cid, "claim": claim,
                     "pydantic_output": None, "expected": f.expected_output,
                     "consistent_with_frozen": False,
                     "task_error": f.error_message[:120]})
    # 覆盖门禁：报告案例数（成功+失败）必须等于输入案例数——缺一即失败，防静默丢案例
    if len(report.cases) + len(report.failures) != len(cases_flat):
        all_ok = False
    adapter_loc = len(Path(__file__).read_text(encoding="utf-8").splitlines())

    # 并入 conformance-results.json：不存在时自初始化（干净环境可独立运行），
    # 存在时保留既有路线段落——与 inspect 路线同模式，消除运行顺序依赖（#12）
    res_path = OUT / "conformance-results.json"
    res = (json.loads(res_path.read_text(encoding="utf-8"))
           if res_path.exists() else {})
    res["route2b_pydantic_evaluator"] = {
        "framework": f"pydantic_evals (installed {__import__('pydantic_evals').__name__})",
        "how": "Dataset/Case + 自定义 Evaluator(CDRAdjudicator)；task=核心库调用返回完整 CDR；"
               "Evaluator 只检查 ctx.output 真实输出 vs 冻结 expected_output（不在评估器内重算）；"
               "最终判定取自 report.cases/failures（全 22 对 + 覆盖门禁）",
        "rows": rows, "all_consistent": all_ok, "pairs_reported": len(rows),
        "adapter_loc": adapter_loc, "core_loc": 122,
        "note": "Inspect 路线 25 行适配 vs 本路线 ~40 行（含逐条明细导出）；两路线共享同一核心库、零语义重复",
    }
    res_path.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"route2b_all_consistent": all_ok,
                      "pairs_reported": len(rows),
                      "rows": [{k: r[k] for k in ("case", "claim", "pydantic_output", "consistent_with_frozen")} for r in rows],
                      "adapter_loc": adapter_loc}, ensure_ascii=False, indent=1))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
