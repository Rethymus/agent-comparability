"""共享案例加载器：A 集（冻结）+ B 集（边界）→ 统一 26 对（A9+B13+D4，动态计算） (case_id, claim, expected, records)。

供 conformance/run_suite.py 与 adapters/*.py 共用，保证两个适配器报告覆盖完全相同的案例集。
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "adapters"))
from inspect_adapter import CASES as A_CASES  # A 集（历史冻结定义，不改写）

_B = json.loads((ROOT / "conformance" / "boundary-cases.json").read_text(encoding="utf-8"))
_D = json.loads((ROOT / "conformance" / "cases-0.4.json").read_text(encoding="utf-8"))


def all_pairs():
    """返回 [(case_id, claim, expected, records)]，A 集在前（顺序稳定，供跨运行比对）。"""
    pairs = []
    for c in A_CASES:
        for claim, expected in c["claims"].items():
            pairs.append((c["id"], claim, expected, c["records"]))
    for c in _B["cases"]:
        for claim, expected in c["claims"].items():
            pairs.append((c["id"], claim, expected, c["records"]))
    for c in _D["cases"]:
        for claim, expected in c["claims"].items():
            pairs.append((c["id"], claim, expected, c["records"]))
    return pairs


def canonical_digest(obj):
    """canonical JSON（键排序 + 紧凑分隔符，UTF-8）后取 sha256——通用内容寻址手法。"""
    payload = json.dumps(obj, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def case_set_digest():
    """冻结语料内容寻址锚：A 集只锚预期（随包形态无 records），B/D 锚预期+records。

    与 doctor 报告的随包语料摘要同一定义（conformance/ 不随 wheel 分发，doctor 无法
    import 本模块——定义孪生一致性由 tests/test_gate_regressions.py N9 守卫）。
    run_suite.py 将其写入 conformance-results.json 顶层，供 PyPI 侧
    （python -m agent_comparability doctor）与 CI 产物跨域比对：版本锚点锚不住
    语料内容，记录+预期一致篡改时唯有本摘要暴露差异。
    """
    corpus = {
        "A": [{"case": c["id"], "claim": k, "expected": v}
              for c in A_CASES for k, v in c["claims"].items()],
        "B": [{"case": c["id"], "claim": k, "expected": v, "records": c["records"]}
              for c in _B["cases"] for k, v in c["claims"].items()],
        "D": [{"case": c["id"], "claim": k, "expected": v, "records": c["records"]}
              for c in _D["cases"] for k, v in c["claims"].items()],
    }
    return canonical_digest(corpus)
