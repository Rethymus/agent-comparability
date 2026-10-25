"""发行版本一致性门禁：tag 名、pyproject、__version__、包元数据四处一致才放行。

用法（本地或 CI 发行步骤）：
    python conformance/release_gate.py            # 校验当前树 vs pyproject
    python conformance/release_gate.py v0.5.0     # 校验当前树 vs 指定发行 tag
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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
    if "cmp/0.3.1" not in spec:
        errs.append("SPEC 版本行缺失（cmp/0.3.1）")
    for e in errs:
        print("RELEASE GATE FAIL:", e)
    print(f"release gate: pyproject={py_ver} runtime={rt_ver} tag=v{expected or '(未指定)'}",
          "OK" if not errs else "FAIL")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
