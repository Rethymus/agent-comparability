"""发行版本一致性门禁：tag 名、pyproject、__version__、包元数据四处一致才放行。

用法（本地或 CI 发行步骤）：
    python conformance/release_gate.py            # 校验当前树 vs pyproject
    python conformance/release_gate.py v0.5.0     # 校验当前树 vs 指定发行 tag

另含孪生同一性门：仓库副本与随包副本（src/agent_comparability/data/）逐字节一致
才放行——两侧静默漂移时，doctor 报告的随包语料摘要与 CI 产物 case_set_digest 将
不可比（生产者↔消费者比较域断裂）。唯一例外 frozen-cases-a.json：仓库副本由
adapters/inspect_adapter.py 以当前 POLICY_VERSION 运行时重写（投影），policy_version
元数据已知分歧、属历史冻结留痕——本门只锁其**预期内容**（id → 各 claim 预期）一致，
这正是 case_set_digest 跨域可比的前提（摘要只覆盖案例内容，不覆盖该元数据）。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 逐字节一致的孪生（规范/Schema/冻结语料 B/D——当前全部一致，实证见 sha256sum）：
_TWIN_FILES = [
    ("spec/SPEC.md", "src/agent_comparability/data/SPEC.md"),
    ("spec/cdr.schema.json", "src/agent_comparability/data/cdr.schema.json"),
    ("conformance/boundary-cases.json", "src/agent_comparability/data/boundary-cases.json"),
    ("conformance/cases-0.4.json", "src/agent_comparability/data/cases-0.4.json"),
]
_FROZEN_A_REPO = "conformance/frozen-cases-a.json"
_FROZEN_A_PKG = "src/agent_comparability/data/frozen-cases-a.json"


def _a_expectations(rel):
    """A 集预期内容视图：{case_id: {claim: expected}}（不含 policy_version 元数据）。"""
    blob = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    return {c["id"]: c["expected_admissibility_by_claim"] for c in blob["cases"]}


def main() -> int:
    expected = sys.argv[1].lstrip("v") if len(sys.argv) > 1 else None
    py = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'^version = "([^"]+)"', py, re.M)
    py_ver = m.group(1)
    init = (ROOT / "src/agent_comparability/__init__.py").read_text(encoding="utf-8")
    m2 = re.search(r'__version__ = "([^"]+)"', init)
    rt_ver = m2.group(1)
    errs = []
    if py_ver != rt_ver:
        errs.append(f"pyproject {py_ver} != __version__ {rt_ver}")
    if expected and py_ver != expected:
        errs.append(f"pyproject {py_ver} != 发行 tag v{expected}")
    spec = (ROOT / "spec/SPEC.md").read_text(encoding="utf-8")
    if "cmp/0.4.0" not in spec:
        errs.append("SPEC 版本行缺失（cmp/0.4.0）")
    twin_errs = []
    for repo_rel, pkg_rel in _TWIN_FILES:
        if (ROOT / repo_rel).read_bytes() != (ROOT / pkg_rel).read_bytes():
            twin_errs.append(f"孪生漂移: {repo_rel} != {pkg_rel}（随包副本须与仓库副本逐字节一致）")
    if _a_expectations(_FROZEN_A_REPO) != _a_expectations(_FROZEN_A_PKG):
        twin_errs.append(f"frozen-cases-a 预期内容漂移: {_FROZEN_A_REPO} vs {_FROZEN_A_PKG}"
                         "（A 集预期须一致——case_set_digest 跨域可比前提；"
                         "policy_version 元数据差异属已知留痕，不在本门范围）")
    errs.extend(twin_errs)
    for e in errs:
        print("RELEASE GATE FAIL:", e)
    twins = "byte-identical" if not twin_errs else "FAIL"  # 结构化判定：孪生错误单独收集，不靠文案匹配
    print(f"release gate: pyproject={py_ver} runtime={rt_ver} tag=v{expected or '(未指定)'} "
          f"twins={twins}", "OK" if not errs else "FAIL")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
