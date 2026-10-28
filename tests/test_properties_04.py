"""cmp/0.4.0 单变量对称性属性测试——D 冻结对（D1/D2）的随机构造泛化。

与 tests/test_properties.py 同风格：随机构造合法记录组，断言 0.4 语义不变式
（非为数量造例）。语义锚点：SPEC §3.3 判定优先级、§4 行 1-5、
conformance/cases-0.4.json（D 集，#27 方向 B，先于实现冻结）。
覆盖维度是 0.3 时代 test_properties.py 未含的对称性与优先级组合。
"""
import random

import pytest

from agent_comparability import adjudicate

STATUSES = ["verified", "unresolved_zero", "other"]


def rec(t, h, m, r, s, **kw):
    d = {"task_id": t, "harness": h, "model": m, "reward": r, "reward_status": s}
    d.update(kw)
    return d


@pytest.mark.parametrize("seed", range(50))
def test_model_only_variation_stays_admissible_with_same_model_info(seed):
    """SPEC §4 行 2：仅模型不同（同任务同 harness、值∈[0,1]、状态不混同）→ 恒 ADMISSIBLE。

    防回归：(a) 0.3.1 语义回潮——same_model 被重新列为 score_comparison 的
    INADMISSIBLE 硬触发（D1 冻结预期的随机化泛化）；(b) same_model 信息项被静默
    抹去（裁决必须如实记录 violated_conditions）；(c) 单变量判定误伤
    （模型-only 必须判 satisfied single_variable_isolation）。
    """
    rng = random.Random(seed)
    n = rng.randint(2, 5)
    k = rng.randint(2, min(n, 4))  # ≥2 个不同模型、≤模型池大小，且全部在组内出现
    models = rng.sample(["model-a", "model-b", "model-c", "model-d"], k)
    status = rng.choice(STATUSES)  # 状态不混同：全组单一 reward_status
    recs = [rec("t", "h1", models[i % k], rng.random(), status) for i in range(n)]
    cdr = adjudicate({"id": "p04-model-only", "records": recs}, "score_comparison")
    assert cdr.admissibility == "ADMISSIBLE"          # 防 same_model 回潮为硬触发（D1）
    assert "same_model" in cdr.violated_conditions    # 信息项必须如实记录，不得静默丢失
    assert "single_variable_isolation" in cdr.satisfied_conditions  # 模型-only=单变量
    assert any(c.startswith("continuous_score_preserved")
               for c in cdr.satisfied_conditions)     # 值∈[0,1] 走隐式默认尺度
    assert cdr.policy_version == "cmp/0.4.0"          # 防版本漂移静默改判


@pytest.mark.parametrize("seed", range(50))
def test_model_and_harness_confound_always_inadmissible(seed):
    """SPEC §4 行 3：模型与 harness 同时不同（同任务）→ 恒 INADMISSIBLE。

    防回归：0.4 对称性只把 same_model 移出硬触发——混淆检测
    （single_variable_isolation）必须仍硬触发；防“对称性放松”被误推广为
    “多变量同变也放行”。混同零语义组同样恒拒（§3.3 优先级 2 先于 4）。
    """
    rng = random.Random(seed)
    n = rng.randint(2, 5)
    combos = [("h1", "m1"), ("h2", "m2"), ("h1", "m2"), ("h2", "m1")]
    recs = [rec("t", "h1", "m1", rng.random(), rng.choice(STATUSES)),
            rec("t", "h2", "m2", rng.random(), rng.choice(STATUSES))]  # 保底双变量
    recs += [rec("t", *rng.choice(combos), rng.random(), rng.choice(STATUSES))
             for _ in range(n - 2)]
    cdr = adjudicate({"id": "p04-confound", "records": recs}, "score_comparison")
    assert cdr.admissibility == "INADMISSIBLE"        # 混淆恒拒（§4 行 3，对称性不覆盖多变量）
    assert "single_variable_isolation" in cdr.violated_conditions  # 防混淆检测被移除
    assert "same_model" in cdr.violated_conditions    # 与 harness 同变=混淆，非单变量


@pytest.mark.parametrize("seed", range(50))
def test_causal_claim_rejected_under_any_0_4_construction(seed):
    """D1 冻结对因果半边：单次运行记录组的因果主张恒 INADMISSIBLE。

    防回归：0.4 对称性重构为因果开洞——单变量、缺轨迹、越界值等任何 0.4 构造
    都不得使因果主张获准（SPEC §3.3：禁止单次运行支持因果）。同时钉住分支顺序
    契约：因果分支先于缺轨迹 INCONCLUSIVE 裁决。
    """
    rng = random.Random(seed)
    recs = [rec(rng.choice(["t1", "t2"]), rng.choice(["h1", "h2"]),
                rng.choice(["m1", "m2"]), rng.random() * 1.5 - 0.25,
                rng.choice(STATUSES)) for _ in range(rng.randint(1, 4))]
    if rng.random() < 0.5:  # 随机混入缺轨迹记录（因果仍须拒，而非降级 INCONCLUSIVE）
        recs[rng.randrange(len(recs))]["trajectory_available"] = False
    cdr = adjudicate({"id": "p04-causal", "records": recs}, "causal")
    assert cdr.admissibility == "INADMISSIBLE"        # 因果恒拒：任何单次运行构造均不豁免
    assert any("causal_attribution" in u
               for u in cdr.unsupported_claims)       # 拒绝理由必须可审计


@pytest.mark.parametrize("seed", range(50))
def test_missing_trace_priority_dominates_all_hard_triggers(seed):
    """§3.3 score_comparison 优先级 1：缺轨迹 INCONCLUSIVE 压过全部条件冲突。

    防回归：优先级倒置——任务/混淆/尺度冲突（INADMISSIBLE）或零语义（PARTIAL）
    抢先于证据缺失裁决；同时防“转录保留”被删（unknown_conditions 的 retained 项）。
    构造保证任务、模型、harness 全部同时变化且全体缺轨迹（全硬触发在场）。
    """
    rng = random.Random(seed)
    recs = [rec("t1", "h1", "m1", rng.random() * 2.0, rng.choice(STATUSES),
                trajectory_available=False),
            rec("t2", "h2", "m2", rng.random() * 2.0, rng.choice(STATUSES),
                trajectory_available=False)]
    recs += [rec(rng.choice(["t1", "t2"]), rng.choice(["h1", "h2"]),
                 rng.choice(["m1", "m2"]), rng.random() * 2.0,
                 rng.choice(STATUSES), trajectory_available=False)
             for _ in range(rng.randint(0, 2))]
    cdr = adjudicate({"id": "p04-trace-priority", "records": recs}, "score_comparison")
    assert cdr.admissibility == "INCONCLUSIVE"        # 缺轨迹恒第一优先（全硬触发在场）
    assert "trace_available" in cdr.violated_conditions
    viol = {v.split("(")[0] for v in cdr.violated_conditions}  # 登记不得被优先级抹除
    assert {"same_task_id", "same_model", "single_variable_isolation"} <= viol
    assert any("retained" in u for u in cdr.unknown_conditions)  # 评分保留不删


@pytest.mark.parametrize("seed", range(50))
def test_scale_gate_not_relaxed_by_model_only_symmetry(seed):
    """D2 冻结点的随机化泛化：模型-only + 任一记录越界未声明尺度 → 恒 INADMISSIBLE。

    防回归：0.4 把 same_model 移出硬触发时放松 score_scale_consistent——尺度把关
    必须对模型-only 组仍独立硬触发（D2 冻结预期）；状态不混同以隔离冲突源。
    """
    rng = random.Random(seed)
    n = rng.randint(2, 4)
    status = rng.choice(STATUSES)  # 状态不混同：尺度是唯一冲突源
    recs = [rec("t", "h1", "model-a", rng.random() * 2.0, status),
            rec("t", "h1", "model-b", 1.0 + rng.random(), status)]  # 必有越界记录
    recs += [rec("t", "h1", rng.choice(["model-a", "model-b"]),
                 rng.random() * 2.0, status) for _ in range(n - 2)]
    cdr = adjudicate({"id": "p04-scale", "records": recs}, "score_comparison")
    assert cdr.admissibility == "INADMISSIBLE"        # 尺度把关未被对称性放松（D2）
    assert "score_scale_consistent" in cdr.violated_conditions
    assert "same_model" in cdr.violated_conditions    # 模型-only 语义仍如实在场
