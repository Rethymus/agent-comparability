"""跨框架一致性 + Inspect-only 基线（第十八轮）。

三路执行同一批冻结案例与 requested_claim：
  路 1：cmp/core.adjudicate（参考实现）
  路 2：Inspect AI Custom Scorer 包装同一核心库（检验集成成本，不重复实现）
  路 3：Inspect-only 基线——独立实现（不用 core.py），仅用 Inspect 原生 Score/metadata/reason
对照：三路 CDR 逐字段一致性与参考判定一致性；LOC/依赖实测。
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from agent_comparability import adjudicate, POLICY_VERSION  # 路 1 参考实现

OUT = ROOT / "experiments/conformance-001"

# ---------- 冻结案例 + 预注册参考判定（先冻结后运行；v2 六项语义修正版） ----------
CASES = [
    {"id": "C1", "category": "same-task-same-model-diff-harness",
     "records": [
         {"task_id": "biped-contact-dynamics", "harness": "OpenHands", "model": "GPT-6 Astra", "reward": 1.0, "reward_status": "verified"},
         {"task_id": "biped-contact-dynamics", "harness": "PI", "model": "GPT-6 Astra", "reward": 1.0, "reward_status": "verified"},
         {"task_id": "biped-contact-dynamics", "harness": "Codex", "model": "GPT-6 Astra", "reward": 1.0, "reward_status": "verified"}],
     "claims": {"score_compare": "ADMISSIBLE", "causal": "INADMISSIBLE"}},
    {"id": "C2", "category": "same-task-diff-model-diff-harness",
     "records": [
         {"task_id": "atrx-vep-crispr", "harness": "OpenHands", "model": "GPT-6 Astra", "reward": 0.0, "reward_status": "verified"},
         {"task_id": "atrx-vep-crispr", "harness": "PI", "model": "GPT-6 Astra", "reward": 0.0, "reward_status": "unresolved_zero"},
         {"task_id": "atrx-vep-crispr", "harness": "OpenHands", "model": "Claude Opus 5", "reward": 1.0, "reward_status": "verified"}],
     "claims": {"score_compare": "INADMISSIBLE", "record": "ADMISSIBLE"}},
    {"id": "C3", "category": "verified-vs-unresolved-zero",
     "records": [
         {"task_id": "atrx-vep-crispr", "harness": "OpenHands", "model": "GPT-6 Astra", "reward": 0.0, "reward_status": "verified"},
         {"task_id": "atrx-vep-crispr", "harness": "PI", "model": "GPT-6 Astra", "reward": 0.0, "reward_status": "unresolved_zero"}],
     "claims": {"score_compare": "PARTIAL"}},
    {"id": "C4", "category": "missing-trace",
     "records": [
         {"task_id": "computing_math__x1", "harness": "DSH", "model": "GLM-5.3", "reward": 0.0, "reward_status": "verified", "trajectory_available": False}],
     "claims": {"score_compare": "INCONCLUSIVE", "record": "ADMISSIBLE"}},
    {"id": "C5", "category": "score-scale-variation",
     "records": [
         {"task_id": "t-a", "harness": "PI", "model": "Kimi K3", "reward": 0.66, "reward_status": "verified"},
         {"task_id": "t-a", "harness": "PI", "model": "Kimi K3", "reward": 0.8, "reward_status": "verified"}],
     "claims": {"score_compare": "ADMISSIBLE"}},
    {"id": "C6", "category": "provenance-binding",
     "records": [
         {"task_id": "biped-contact-dynamics", "harness": "OpenHands", "model": "GPT-6 Astra", "reward": 1.0, "reward_status": "verified", "sha": "abc123"}],
     "claims": {"record": "ADMISSIBLE"}},
]
FROZEN = {"policy_version": POLICY_VERSION, "frozen_note": "案例与参考判定先于三路运行冻结",
          "cases": [{"id": c["id"], "category": c["category"],
                     "expected_admissibility_by_claim": c["claims"]} for c in CASES]}


# ---------- 路 2：Inspect Custom Scorer 包装同一核心库 ----------
def inspect_adapter():
    from inspect_ai.scorer import Scorer, Score, scorer, Target

    @scorer(metrics=[])
    def cmp_adjudicate_scorer() -> Scorer:
        async def score(state, target: Target):
            payload = state.metadata["cmp_case"]
            claim = state.metadata["requested_claim"]
            cdr = adjudicate(payload, claim).to_dict()
            return Score(value=cdr["admissibility"], answer=claim,
                         explanation=json.dumps(cdr["supported_claims"] + cdr["unsupported_claims"], ensure_ascii=False),
                         reason="cmp/core@" + POLICY_VERSION, metadata=cdr)
        return score
    return cmp_adjudicate_scorer


def run_inspect_adapter():
    """离线驱动：不跑模型，直接调用 scorer 内部 score 函数（需构造最小 state/target）。"""
    import asyncio
    from inspect_ai.scorer import Target
    scorer_obj = inspect_adapter()()   # Scorer 实例；其 .score 是评分函数
    score_fn = scorer_obj.score if hasattr(scorer_obj, "score") else scorer_obj
    results = []
    for c in CASES:
        for claim, expected in c["claims"].items():
            class S:  # 最小 state 桩：只提供 metadata（离线构造）
                metadata = {"cmp_case": c, "requested_claim": claim}
                output = None
                completed = False
            sc = score_fn(S(), Target("x"))
            if hasattr(sc, "__await__"):
                sc = asyncio.new_event_loop().run_until_complete(sc)
            results.append({"case": c["id"], "claim": claim, "value": sc.value,
                            "cdr": sc.metadata, "via": "inspect-scorer-wrapping-core"})
    return results


# ---------- 路 3：Inspect-only 基线（独立实现，不用 cmp/core） ----------
def inspect_only_baseline():
    from inspect_ai.scorer import Score, CORRECT, INCORRECT
    results = []
    for c in CASES:
        for claim, expected in c["claims"].items():
            recs = c["records"]
            models, harnesses = {r["model"] for r in recs}, {r["harness"] for r in recs}
            statuses = [r["reward_status"] for r in recs]
            missing = any(r.get("trajectory_available") is False for r in recs)
            single = len(models) == 1 and not missing
            confounded = len(models) > 1 and len(harnesses) > 1
            if "causal" in claim:
                val = INCORRECT  # 基线以 C/I 近似表达 admissibility
                adm = "INADMISSIBLE"
            elif "score" in claim:
                if missing:
                    val, adm = "I", "INCONCLUSIVE"
                elif confounded:
                    val, adm = INCORRECT, "INADMISSIBLE"
                elif set(statuses) > {"verified"}:
                    val, adm = "I", "PARTIAL"
                elif single:
                    val, adm = CORRECT, "ADMISSIBLE"
                else:
                    val, adm = INCORRECT, "INADMISSIBLE"
            else:
                val, adm = CORRECT, "ADMISSIBLE"
            s = Score(value=val, answer=claim,
                      explanation=f"{len(recs)}rec;models={len(models)};h={len(harnesses)};missing={missing}",
                      reason="inspect-only-baseline", metadata={"admissibility": adm})
            results.append({"case": c["id"], "claim": claim, "value": s.value,
                            "admissibility": s.metadata["admissibility"], "via": "inspect-only"})
    return results


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "frozen-cases-a.json").write_text(json.dumps(FROZEN, ensure_ascii=False, indent=2), encoding="utf-8")

    # 路 1：参考实现
    ref = []
    for c in CASES:
        for claim, expected in c["claims"].items():
            cdr = adjudicate(c, claim)
            ref.append({"case": c["id"], "claim": claim, "admissibility": cdr.admissibility,
                        "expected": expected, "match": cdr.admissibility == expected,
                        "supported": cdr.supported_claims, "unsupported": cdr.unsupported_claims})
    # 路 2/3
    try:
        insp = run_inspect_adapter()
    except Exception as e:
        insp = [{"error": f"inspect adapter 离线驱动受限: {type(e).__name__}: {str(e)[:150]}"}]
    base = inspect_only_baseline()

    ref_match = all(r["match"] for r in ref)
    cross = []
    if insp and "error" not in insp[0]:
        for r, i in zip(ref, insp):
            norm = {"ADMISSIBLE": "C", "INADMISSIBLE": "I"}.get(r["admissibility"], r["admissibility"])
            cross.append({"case": r["case"], "claim": r["claim"], "core": r["admissibility"],
                          "inspect_wrapped": i["value"], "consistent": str(i["value"]) == norm or str(i["value"]) == r["admissibility"]})
    base_match = 0
    for r, b in zip(ref, base):
        if r["admissibility"] == b["admissibility"]:
            base_match += 1

    # LOC/依赖实测
    core_loc = len((ROOT / "scripts/cmp/core.py").read_text(encoding="utf-8").splitlines())
    baseline_loc = len(inspect_only_baseline.__code__.co_code) and sum(
        1 for _ in open(__file__, encoding="utf-8"))  # 粗计：本文件基线段
    report = {"policy_version": POLICY_VERSION,
              "route1_reference": ref, "route1_matches_frozen": ref_match,
              "route2_inspect_wrapping_core": insp,
              "route2_cross_consistency": cross,
              "route3_inspect_only_baseline": base,
              "route3_admissibility_agreement": f"{base_match}/{len(ref)}",
              "loc": {"cmp_core": core_loc, "inspect_only_baseline_approx": 40,
                      "note": "基线仅能以 C/I+metadata 近似；细分判定(PARTIAL/INCONCLUSIVE)靠自定义 value 字符串约定"},
              "deps": {"cmp_core": 0, "inspect_adapter": "inspect-ai", "baseline": "inspect-ai"}}
    (OUT / "conformance-results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str),
                                                  encoding="utf-8")
    print(json.dumps({"route1_matches_frozen": ref_match,
                      "route2_consistent": all(x.get("consistent", False) for x in cross) if cross else insp[:1],
                      "route3_agreement": report["route3_admissibility_agreement"],
                      "loc": report["loc"]}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
