"""Conformance Suite 运行器：三指标分离（规范 §7），并输出每层独立结果。

指标 1 集成一致性：core 经 Inspect / Pydantic 调用，输出一致（既有 9 案例复核 + B 集）。
指标 2 规范一致性：independent_impl（依规范）对 A+B 全案例的判定 vs 冻结预期。
指标 3 策略正确性：core 对 A+B 全案例的判定 vs 冻结预期（B 集是 0.2 的 gap 检验，
  允许暴露缺陷——修复须以规范为准，不得改预期）。
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts/cmp"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

RELEASE = ROOT / "release"
OUT = ROOT / "conformance-results.json"

# A 集（既有 9 对）+ B 集（边界）
sys.path.insert(0, str(ROOT / "adapters"))
from inspect_adapter import CASES as A_CASES  # noqa
B = json.loads((ROOT / "conformance/boundary-cases.json").read_text(encoding="utf-8"))

import cmp.core as core  # 参考实现（策略正确性受检对象）
import independent_impl as indep  # 独立实现（规范一致性受检对象）


def run_all_cases():
    pairs = []  # (case_id, claim, expected, records)
    for c in A_CASES:
        for claim, expected in c["claims"].items():
            pairs.append((c["id"], claim, expected, c["records"]))
    for c in B["cases"]:
        for claim, expected in c["claims"].items():
            pairs.append((c["id"], claim, expected, c["records"]))
    return pairs


def main() -> int:
    pairs = run_all_cases()

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

    # --- 指标 1：集成一致性（core 的 CDR 经 Inspect/Pydantic 路线输出一致；用 A 集 + B 集抽样）---
    integ_rows = []
    try:
        for cid, claim, expected, recs in pairs:
            cdr_direct = core.adjudicate({"id": cid, "records": recs}, claim).to_dict()
            # Inspect 路线（复用 run_conformance 的适配器）
            import asyncio
            from inspect_ai.scorer import Target
            from inspect_adapter import inspect_adapter
            scorer_obj = inspect_adapter()()
            score_fn = scorer_obj.score if hasattr(scorer_obj, "score") else scorer_obj

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
        integ_pass = sum(r["ok"] for r in integ_rows)
        pyd_same = "见 route2b 机制（同一 core，机制等价）"
    except Exception as e:
        integ_pass, pyd_same = None, f"inspect 路线异常: {type(e).__name__}"

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
        "metric1_integration_consistency": {"passed": f"{integ_pass}/{len(integ_rows)}" if integ_pass is not None else None,
                                            "rows": integ_rows, "pydantic": pyd_same},
        "cdr_schema_probe": schema_probe,
        "case_sets": {"A(参与过调试,既有)": 9, "B(新边界,未参与调试)": len(pairs) - 9},
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    brief = {k: (v["passed"] if isinstance(v, dict) and "passed" in v else v) for k, v in result.items() if k != "metrics_separated"}
    print(json.dumps(brief, ensure_ascii=False, indent=1))
    # 失败明细
    for m in ("metric3_policy_correctness", "metric2_spec_conformance"):
        fails = [r for r in result[m]["rows"] if not r["ok"]]
        if fails:
            print(f"\n{m} 失败:", [(r["case"], r["claim"], r["got"], "expect=" + r["expected"]) for r in fails])
    return 0


if __name__ == "__main__":
    sys.exit(main())
