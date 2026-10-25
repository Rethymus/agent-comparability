"""独立最小实现：仅依 release/SPEC.md（cmp/0.3 规范）编写，未参考 scripts/cmp/core.py 源码。

作者注（隔离声明）：本实现按规范 §3.2 条件顺序与 §3.3 判定表从零翻译；
§5 未知字段/未支持 claim 规则、B5 的保守尺度规则均来自规范文本。
"""

POLICY_VERSION = "cmp/0.3.1"
TAMPER = "摘要一致仅证明未同步修改，不构成抗恶意篡改（单写信任域）"


def adjudicate(records, requested_claim):
    known_fields = {"task_id", "harness", "model", "reward", "reward_status",
                    "trajectory_available", "score_scale", "repetition_count"}
    ignored = sorted({k for r in records for k in r if k not in known_fields})

    tasks = {r["task_id"] for r in records}
    models = {r["model"] for r in records}
    harnesses = {r["harness"] for r in records}
    missing_trace = any(r.get("trajectory_available") is False for r in records)
    statuses = {r["reward_status"] for r in records}
    # 规范 0.3.1 隐式默认：值∈[0,1] 未声明 → 默认尺度
    DEFAULT = ("range", "0..1"),  # 占位，实际用元组排序比较
    eff = []
    for r in records:
        if "score_scale" in r:
            eff.append(tuple(sorted(r["score_scale"].items())))
        elif isinstance(r.get("reward"), (int, float)) and 0.0 <= r["reward"] <= 1.0:
            eff.append(tuple(sorted({"range": "0..1", "unit": "fraction", "verifier": "source"}.items())))
        else:
            eff.append(None)
    scale_consistent = (len(set(eff)) == 1 and None not in eff) if len(records) > 1 else True
    has_explicit_scale = [e is not None for e in eff]
    reps = all(r.get("repetition_count", 0) >= 1 for r in records)

    satisfied, violated, unknown = [], [], []
    if ignored:
        unknown.append(f"ignored_fields:{ignored}")
    (satisfied if len(tasks) == 1 else violated).append("same_task_id")
    (satisfied if len(models) == 1 else violated).append("same_model")
    confounded = len(models) > 1 and len(harnesses) > 1
    if confounded:
        violated.append("single_variable_isolation")
    else:
        satisfied.append("single_variable_isolation")
    if missing_trace:
        violated.append("trace_available")
    if "unresolved_zero" in statuses and "verified" in statuses:
        violated.append("zero_semantics_uniform")
    multi = len(records) > 1
    if multi and not scale_consistent:
        violated.append("score_scale_consistent")

    claim = requested_claim.replace("_", " ")
    if any(k in claim for k in ("causal", "归因", "导致")):
        adm = "INADMISSIBLE"  # 规范 §3.3：重复存在也仍禁止单纯因果表述（降级为描述）
        supported, unsupported = [], ["causal_attribution"]
    elif any(k in claim for k in ("score", "分数", "成功率")) and not any(
            k in claim for k in ("record", "登记", "registration", "descriptive")):
        if missing_trace:
            adm = "INCONCLUSIVE"   # 优先级 1
            unknown.append("source_reward_retained_but_unverifiable_by_us")
            supported, unsupported = ["score_transcription(source_verifier_attested)"], ["success_rate"]
        elif len(tasks) > 1 or len(models) > 1 or confounded or "score_scale_consistent" in violated:
            adm = "INADMISSIBLE"  # 优先级 2
            supported, unsupported = [], ["score_comparison"]
        elif multi and "score_scale_consistent" in violated:
            adm = "INADMISSIBLE"  # 优先级 3
            supported, unsupported = [], ["score_comparison(scale_mismatch)"]
        elif "zero_semantics_uniform" in violated:
            adm = "PARTIAL"       # 优先级 4
            supported, unsupported = ["per_status_stratified_rate"], ["pooled_fail_rate"]
        else:
            adm = "ADMISSIBLE"
            supported, unsupported = ["continuous_score_side_by_side"], []
    elif any(k in claim for k in ("record", "登记", "registration", "descriptive", "describe")):
        adm = "ADMISSIBLE"
        supported, unsupported = ["descriptive_registration"], []
    else:
        adm = "INCONCLUSIVE"
        unknown.append("unrecognized_claim_type")
        supported, unsupported = [], []

    return {"admissibility": adm, "supported": supported, "unsupported": unsupported,
            "satisfied": satisfied, "violated": violated, "unknown": unknown,
            "policy_version": POLICY_VERSION, "limitations": [TAMPER]}
