"""高价值属性测试：随机合法记录组上，不变式必须成立（非为数量造例）。"""
import random
import pytest
from agent_comparability import adjudicate

STATUSES = ["verified", "unresolved_zero", "other"]
def rec(t, h, m, r, s, **kw):
    d = {"task_id": t, "harness": h, "model": m, "reward": r, "reward_status": s}
    d.update(kw); return d

@pytest.mark.parametrize("seed", range(50))
def test_causal_never_admissible_single_run(seed):
    rng = random.Random(seed)
    recs = [rec("t", rng.choice("abc"), rng.choice("xy"), rng.random(),
                rng.choice(STATUSES)) for _ in range(rng.randint(1, 3))]
    cdr = adjudicate({"id": "p", "records": recs}, "causal")
    assert cdr.admissibility == "INADMISSIBLE"          # 无重复实验 → 因果一律拒绝

@pytest.mark.parametrize("seed", range(50))
def test_missing_trace_never_counts_and_keeps_score(seed):
    rng = random.Random(seed)
    recs = [rec("t", rng.choice("abc"), rng.choice("xy"), rng.random(),
                rng.choice(STATUSES), trajectory_available=False)]
    cdr = adjudicate({"id": "p", "records": recs}, "score_comparison")
    assert cdr.admissibility == "INCONCLUSIVE"          # 优先级 1
    assert any("retained" in u for u in cdr.unknown_conditions)  # 评分保留不删

@pytest.mark.parametrize("seed", range(50))
def test_registration_always_admissible_and_tamper_limitation_present(seed):
    rng = random.Random(seed)
    recs = [rec(rng.choice("ab"), rng.choice("abc"), rng.choice("xy"), rng.random()*1.2,
                rng.choice(STATUSES)) for _ in range(rng.randint(1, 4))]
    cdr = adjudicate({"id": "p", "records": recs}, "descriptive_registration")
    assert cdr.admissibility == "ADMISSIBLE"
    assert any("抗恶意篡改" in l for l in cdr.limitations)

@pytest.mark.parametrize("seed", range(50))
def test_higher_priority_verdict_never_erases_registered_violations(seed):
    rng = random.Random(seed)
    recs = [rec("a", "h1", "m1", 1.0, "verified"),
            rec("b", "h2", "m2", 0.0, "unresolved_zero", trajectory_available=False)]
    cdr = adjudicate({"id": "p", "records": recs}, "score_comparison")
    assert cdr.admissibility == "INCONCLUSIVE"
    viol = {v.split("(")[0] for v in cdr.violated_conditions}
    assert {"same_task_id", "same_model", "single_variable_isolation",
            "zero_semantics_uniform", "trace_available"} <= viol
