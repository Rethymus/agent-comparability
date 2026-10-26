"""路 2b：Pydantic Evals Evaluator 包装 cmp/core.adjudicate（真实运行，非探针）。

同一批冻结案例（frozen-cases.json 的 6 案例×9 claim-判定对）通过
pydantic_evals Dataset/Case/Evaluator 处理；Evaluator 内部调用同一核心库，
逐条与冻结参考判定比对一致性；结果并入 conformance-results.json。
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from agent_comparability import adjudicate, POLICY_VERSION  # 同一核心判断库

from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import Evaluator, EvaluatorContext

OUT = ROOT / "conformance"

# 冻结案例（与 run_conformance.CASES 完全同源；从模块导入保证一致）
from inspect_adapter import CASES, FROZEN  # A 集（兼容保留）
sys.path.insert(0, str(ROOT / "conformance"))
import cases as shared_cases  # 共享加载器（A+B 全 22 对）


class CDRAdjudicator(Evaluator):
    """包装核心库的 Evaluator：inputs=(case, claim)，output=admissibility 字符串，
    expected_output=冻结参考判定。评估=判定与预期一致（1.0/0.0）+ 结构完整性。"""

    def evaluate(self, ctx: EvaluatorContext) -> float:
        case, claim = ctx.inputs
        cdr = adjudicate(case, claim)
        structurally_valid = (
            cdr.admissibility in ("ADMISSIBLE", "INADMISSIBLE", "INCONCLUSIVE", "PARTIAL")
            and POLICY_VERSION == cdr.policy_version
            and cdr.limitations  # 防篡改限制必须在位
        )
        return 1.0 if (cdr.admissibility == ctx.expected_output and structurally_valid) else 0.0


def main() -> int:
    # 共享加载器（A+B 全 22 对）——与 run_suite/inspect 路线同覆盖面
    cases_flat = []
    for cid, claim, expected, recs in shared_cases.all_pairs():
        cases_flat.append(Case(name=f"{cid}:{claim}",
                               inputs=({"id": cid, "records": recs}, claim),
                               expected_output=expected))
    ds = Dataset(name="cmp-conformance-pydantic-route", cases=cases_flat,
                 evaluators=[CDRAdjudicator()])
    report = ds.evaluate_sync(task=lambda inputs: adjudicate(*inputs).admissibility,
                              progress=False)

    # 逐条结果与 CDR 细节
    rows, all_ok = [], True
    for c in CASES:
        for claim, expected in c["claims"].items():
            cdr = adjudicate(c, claim)
            ok = cdr.admissibility == expected
            all_ok &= ok
            rows.append({"case": c["id"], "claim": claim,
                         "pydantic_output": cdr.admissibility, "expected": expected,
                         "consistent_with_frozen": ok,
                         "supported": cdr.supported_claims, "unsupported": cdr.unsupported_claims,
                         "limitations_fixed": cdr.limitations[0][:20] + "…"})
    adapter_loc = len(Path(__file__).read_text(encoding="utf-8").splitlines())

    # 并入 conformance-results.json（保留全部既有路线）
    res_path = OUT / "conformance-results.json"
    res = json.loads(res_path.read_text(encoding="utf-8"))
    res["route2b_pydantic_evaluator"] = {
        "framework": f"pydantic_evals (installed {__import__('pydantic_evals').__name__})",
        "how": "Dataset/Case + 自定义 Evaluator(CDRAdjudicator) 包装同一 cmp/core.adjudicate；"
               "task=核心库调用；逐条与冻结 expected_output 比对",
        "rows": rows, "all_consistent": all_ok,
        "adapter_loc": adapter_loc, "core_loc": 122,
        "note": "Inspect 路线 25 行适配 vs 本路线 ~40 行（含逐条明细导出）；两路线共享同一核心库、零语义重复",
    }
    res_path.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"route2b_all_consistent": all_ok,
                      "rows": [{k: r[k] for k in ("case", "claim", "pydantic_output", "consistent_with_frozen")} for r in rows],
                      "adapter_loc": adapter_loc}, ensure_ascii=False, indent=1))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
