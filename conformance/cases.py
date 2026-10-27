"""共享案例加载器：A 集（冻结）+ B 集（边界）→ 统一 22 对 (case_id, claim, expected, records)。

供 conformance/run_suite.py 与 adapters/*.py 共用，保证两个适配器报告覆盖完全相同的案例集。
"""
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
