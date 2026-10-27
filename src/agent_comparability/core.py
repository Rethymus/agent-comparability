"""比较判定核心库 cmp/core（cmp/0.4.0 规范参考实现）。

相对 0.3.1 的判定表分支修正（#27 裁决方向 B，SPEC §5 允许 minor 新增分支）：
  ⑤score_comparison 的 INADMISSIBLE 触发移除 same_model——单变量对称性
    （§4 行 2：仅模型不同 → ADMISSIBLE 并排）；模型-only 变化由
    score_scale_consistent / zero_semantics_uniform 独立把关（D2 冻结对证明）。
相对 0.2 的规范符合性修复（依据 SPEC 0.3.1；B 集冻结预期先于本修改存在）：
  ①同任务性检查入 score 判定优先级 2（B3 暴露 0.2 缺失）
  ②评分尺度一致性检查（含 0.3.1 隐式默认规则）（B4/B5 暴露 0.2 缺失）
  ③claim 路由补 registration/descriptive 关键词（B2-B5 暴露误判）
  ④policy_version 升 cmp/0.3.1（消费方按 SPEC §5 重判旧 CDR）
判定优先级（SPEC §3.3）：INCONCLUSIVE(缺trace) > INADMISSIBLE(任务/混淆/尺度) > PARTIAL(零语义) > ADMISSIBLE。
"""

from dataclasses import dataclass, field, asdict

POLICY_VERSION = "cmp/0.4.0"
TAMPER_LIMITATION = "摘要一致仅证明未同步修改，不构成抗恶意篡改（单写信任域）"
DEFAULT_SCALE = {"range": "0..1", "unit": "fraction", "verifier": "source"}
KNOWN_FIELDS = {"task_id", "harness", "model", "reward", "reward_status",
                "trajectory_available", "score_scale", "repetition_count"}


@dataclass
class CDR:
    case_id: str
    requested_claim: str
    comparison_scope: str
    admissibility: str = "PENDING"
    satisfied_conditions: list = field(default_factory=list)
    violated_conditions: list = field(default_factory=list)
    unknown_conditions: list = field(default_factory=list)
    supported_claims: list = field(default_factory=list)
    unsupported_claims: list = field(default_factory=list)
    evidence_refs: list = field(default_factory=list)
    policy_version: str = POLICY_VERSION
    limitations: list = field(default_factory=lambda: [TAMPER_LIMITATION])

    def to_dict(self):
        return asdict(self)


def _effective_scale(r):
    """SPEC 0.3.1 隐式默认：值∈[0,1] 且未声明 → 默认尺度；否则必须显式。"""
    if "score_scale" in r:
        return tuple(sorted(r["score_scale"].items()))
    if isinstance(r.get("reward"), (int, float)) and 0.0 <= r["reward"] <= 1.0:
        return tuple(sorted(DEFAULT_SCALE.items()))
    return None  # 越界且未声明 → 不一致


def adjudicate(case: dict, requested_claim: str) -> CDR:
    recs = case["records"]
    models = {r["model"] for r in recs}
    harnesses = {r["harness"] for r in recs}
    tasks = {r["task_id"] for r in recs}
    statuses = [r["reward_status"] for r in recs]
    any_missing = any(r.get("trajectory_available") is False for r in recs)
    multi = len(recs) > 1
    ignored = sorted({k for r in recs for k in r if k not in KNOWN_FIELDS})

    cdr = CDR(case_id=case["id"], requested_claim=requested_claim,
              comparison_scope=f"{len(recs)} records; models={sorted(models)}; harnesses={sorted(harnesses)}")

    (cdr.satisfied_conditions if len(tasks) == 1 else cdr.violated_conditions).append("same_task_id")
    (cdr.satisfied_conditions if len(models) == 1 else cdr.violated_conditions).append("same_model")
    confounded = len(models) > 1 and len(harnesses) > 1
    (cdr.violated_conditions if confounded else cdr.satisfied_conditions).append("single_variable_isolation")
    if any_missing:
        cdr.violated_conditions.append("trace_available")
    if "unresolved_zero" in statuses and "verified" in statuses:
        cdr.violated_conditions.append("zero_semantics_uniform(verified_zero != unresolved_zero)")
    scales = [_effective_scale(r) for r in recs]
    if (multi and (None in scales or len(set(scales)) > 1)) or None in scales:
        # 值越界且未声明尺度（单记录同样不构成可比较尺度）——SPEC 0.3.1 隐式默认规则
        cdr.violated_conditions.append("score_scale_consistent")
    else:
        base = scales[0] if scales else tuple(sorted(DEFAULT_SCALE.items()))
        cdr.satisfied_conditions.append("continuous_score_preserved(" + repr(dict(base)) + ")")
    if ignored:
        cdr.unknown_conditions.append(f"ignored_fields:{ignored}")
    if any_missing:
        cdr.unknown_conditions.append("source_reward_retained_but_unverifiable_by_us")

    claim = requested_claim.replace("_", " ")
    single_var = (not confounded and not any_missing)

    if any(k in claim for k in ("causal", "导致", "归因")):
        cdr.admissibility = "INADMISSIBLE"
        cdr.unsupported_claims.append("causal_attribution(单次运行无重复)")
        if single_var:
            cdr.supported_claims.append("descriptive_side_by_side(降级表述)")
    elif any(k in claim for k in ("score", "分数", "成功率")) and not any(
            k in claim for k in ("record", "登记", "registration", "descriptive")):
        if any_missing:
            cdr.admissibility = "INCONCLUSIVE"
            cdr.supported_claims.append("score_transcription(source_verifier_attested)")
            cdr.unsupported_claims.append("success_rate(含证据缺失记录)")
        elif len(tasks) > 1 or confounded or "score_scale_consistent" in cdr.violated_conditions:
            # 0.4：same_model 移出硬触发（#27 单变量对称性）；尺度/零语义条件独立把关
            cdr.admissibility = "INADMISSIBLE"
            cdr.unsupported_claims.append("score_comparison(任务/混淆/尺度条件冲突)")
        elif any(v.startswith("zero_semantics_uniform") for v in cdr.violated_conditions):
            cdr.admissibility = "PARTIAL"
            cdr.supported_claims.append("per_status_stratified_rate(verified_zero/unresolved_zero 分列)")
            cdr.unsupported_claims.append("pooled_fail_rate(0 分语义混同)")
        else:
            cdr.admissibility = "ADMISSIBLE"
            cdr.supported_claims.append("continuous_score_side_by_side(同尺度)")
    elif any(k in claim for k in ("record", "登记", "registration", "descriptive", "describe")):
        cdr.admissibility = "ADMISSIBLE"
        cdr.supported_claims.append("descriptive_registration(全部条件+连续分数)")
    else:
        cdr.admissibility = "INCONCLUSIVE"
        cdr.unknown_conditions.append("unrecognized_claim_type")

    cdr.evidence_refs = [f"rec:{r['task_id']}/{r['model']}/{r['harness']}" for r in recs]
    return cdr
