"""最小冒烟：安装即可验证。"""
from agent_comparability import adjudicate, POLICY_VERSION

def test_admissible_side_by_side():
    cdr = adjudicate({"id": "t", "records": [
        {"task_id": "x", "harness": "a", "model": "m", "reward": 1.0, "reward_status": "verified"},
        {"task_id": "x", "harness": "b", "model": "m", "reward": 0.5, "reward_status": "verified"}]},
        "score_comparison")
    assert cdr.admissibility == "ADMISSIBLE"
    assert cdr.policy_version == POLICY_VERSION
    assert any("抗恶意篡改" in l for l in cdr.limitations)
