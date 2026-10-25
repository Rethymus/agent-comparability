"""永久回归：负向门禁 N1-N4 的可执行断言（原始失败记录见 VALIDATION.md 与 git 历史
ad14fb5/541494d 修复提交）。每条测试在 tmp 副本上注入违规并断言对应门禁退出码非零。"""
import importlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
ROOT = Path(__file__).resolve().parents[1]


def _copy_tree():
    tmp = Path(tempfile.mkdtemp())
    for rel in ["src", "conformance", "spec", "adapters", "tests", "pyproject.toml",
                "README.md", "README.zh-CN.md", "LICENSE", "NOTICE", "CHANGELOG.md",
                "CONTRIBUTING.md", "SECURITY.md", "docs"]:
        s, d = ROOT / rel, tmp / rel
        (shutil.copytree if s.is_dir() else shutil.copy2)(s, d)
    return tmp


def _run(tmp, *args):
    return subprocess.run([sys.executable, *args], cwd=tmp, capture_output=True, text=True)


def test_N1_poison_import_blocked_by_terminal_scan():
    tmp = _copy_tree()
    core = tmp / "src/agent_comparability/core.py"
    core.write_text(core.read_text(encoding="utf-8") + "\nfrom cmp.core import x\n", encoding="utf-8")
    r = _run(tmp, "conformance/terminal_scan.py")
    shutil.rmtree(tmp, ignore_errors=True)
    assert r.returncode != 0, "终扫未阻断违规导入（N1 回归）"


def test_N1b_structured_alternative_ast_scan():
    """结构化检查路径：AST 解析 import 语句，不依赖字符串模式扩张。"""
    import ast
    # 注：本文件自身含注入用字面量（"from cmp…"），故 AST 检查只扫 src/（真实运行面）
    core = (ROOT / "src/agent_comparability/core.py").read_text(encoding="utf-8")
    tree = ast.parse(core)
    banned = {"cmp", "arlib"}
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module.split(".")[0])
    assert not (mods & banned), f"AST 扫描发现违规模块: {mods & banned}"


def test_N2_frozen_expectation_tamper_fails_suite_exit():
    tmp = _copy_tree()
    cases = tmp / "conformance/boundary-cases.json"
    d = json.loads(cases.read_text(encoding="utf-8"))
    b3 = next(x for x in d["cases"] if x["id"] == "B3")
    b3["claims"]["score_comparison"] = "ADMISSIBLE"  # 篡改为让缺陷通过
    cases.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    r = _run(tmp, "conformance/run_suite.py")
    shutil.rmtree(tmp, ignore_errors=True)
    assert r.returncode != 0, "套件对冻结预期篡改仍退出 0（N2 回归）"


def test_N3_N4_doc_gate_blocks_bad_link_and_fake_pip():
    tmp = _copy_tree()
    readme = tmp / "README.md"
    readme.write_text(readme.read_text(encoding="utf-8").replace(
        "[CONTRIBUTING.md](CONTRIBUTING.md)", "[CONTRIBUTING.md](NOPE.md)"), encoding="utf-8")
    assert _run(tmp, "conformance/check_docs.py").returncode != 0
    shutil.rmtree(tmp, ignore_errors=True)
    tmp = _copy_tree()
    zh = tmp / "README.zh-CN.md"
    zh.write_text(zh.read_text(encoding="utf-8").replace(
        "pip install -e .            # 核心，零依赖", "pip install agent-comparability"), encoding="utf-8")
    r = _run(tmp, "conformance/check_docs.py")
    shutil.rmtree(tmp, ignore_errors=True)
    assert r.returncode != 0, "docs 门禁未拦截假 pip 命令（N4 回归）"


def test_assertions_not_skipped_or_weakened():
    """断言完整性：关键测试文件无 skip 标记、无降级为 warning。"""
    for f in (ROOT / "tests").glob("test_*.py"):
        if f.name == "test_gate_regressions.py":
            continue  # 自身包含被检测字面量（自引用排除，同 terminal_scan 先例）
        s = f.read_text(encoding="utf-8")
        assert "pytest.skip" not in s and "@pytest.mark.skip" not in s, f"{f.name} 含 skip"
        assert "pytest.warns" not in s, f"{f.name} 断言降级为 warns"
