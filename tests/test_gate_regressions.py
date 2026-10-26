"""永久回归：负向门禁 N1-N6 的可执行断言（原始失败记录见 VALIDATION.md 与 git 历史
ad14fb5/541494d 修复提交；N5/N6 源自 #10）。每条测试在 tmp 副本上注入违规并断言对应门禁退出码非零。"""
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
        "pip install -e .                        # 最小核心，零依赖", "pip install agent-comparability"), encoding="utf-8")
    r = _run(tmp, "conformance/check_docs.py")
    shutil.rmtree(tmp, ignore_errors=True)
    assert r.returncode != 0, "docs 门禁未拦截假 pip 命令（N4 回归）"


def test_N5_evaluators_check_real_task_output():
    """#10 P0 回归：Pydantic Evaluator 必须检查被评测 task 的真实输出（ctx.output），
    不得在评估器内重算判定。注入错误输出的 task，断言逐对 0 分（路线级失败）。"""
    pytest.importorskip("pydantic_evals")
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT / "conformance"))
    sys.path.insert(0, str(ROOT / "adapters"))
    from dataclasses import replace

    from pydantic_evals import Case, Dataset
    from agent_comparability import adjudicate
    from cases import all_pairs
    from pydantic_adapter import CDRAdjudicator
    from run_suite import CDRParity

    pairs = [p for p in all_pairs() if p[2] != "INADMISSIBLE"][:3]
    cases = [Case(name=f"{cid}:{claim}", inputs=({"id": cid, "records": recs}, claim),
                  expected_output=expected)
             for cid, claim, expected, recs in pairs]

    # run_suite 路线：task 返回错误常量 → 全部 0 分（结构合法但输出错误）
    rep = Dataset(name="n5a", cases=cases, evaluators=[CDRParity()]).evaluate_sync(
        task=lambda inputs: "INADMISSIBLE", progress=False)
    scores = [next(iter(c.scores.values())).value for c in rep.cases]
    assert scores and all(s == 0.0 for s in scores), "错误 task 输出未被 CDRParity 阻断（N5 回归）"

    # 适配器路线：真实 CDR 结构、注入错误可采纳性 → 0 分；原始 CDR → 1 分（阳性对照）
    cid, claim, expected, recs = pairs[0]
    inputs = ({"id": cid, "records": recs}, claim)
    ds = Dataset(name="n5b", cases=[Case(name="x", inputs=inputs, expected_output=expected)],
                 evaluators=[CDRAdjudicator()])
    bad = ds.evaluate_sync(task=lambda i: replace(adjudicate(*i), admissibility="INADMISSIBLE"),
                           progress=False)
    good = ds.evaluate_sync(task=lambda i: adjudicate(*i), progress=False)
    assert next(iter(bad.cases[0].scores.values())).value == 0.0, \
        "错误 task 输出未被 CDRAdjudicator 阻断（N5 回归）"
    assert next(iter(good.cases[0].scores.values())).value == 1.0, \
        "正确 task 输出被误判为失败（N5 阳性对照）"


def test_N6_adapter_verdict_from_report_all_pairs():
    """#10 P1 回归：适配器最终判定必须来自 report（全 22 对）而非旁路循环。
    tmp 副本注入返回错误可采纳性的 task，断言退出码非零、仍报告 22 对且判定不一致。"""
    pytest.importorskip("pydantic_evals")
    tmp = _copy_tree()
    pa = tmp / "adapters/pydantic_adapter.py"
    s = pa.read_text(encoding="utf-8")
    anchor = "task=lambda inputs: adjudicate(*inputs), progress=False)"
    assert anchor in s, "锚点漂移：适配器 task 定义已变更，需同步更新 N6 注入方式"
    s = s.replace(anchor,
                  "task=lambda inputs: replace(adjudicate(*inputs), admissibility='INADMISSIBLE'), progress=False)")
    s = s.replace("import json\n", "import json\nfrom dataclasses import replace\n", 1)
    pa.write_text(s, encoding="utf-8")
    _run(tmp, "adapters/inspect_adapter.py")  # 先生成 conformance-results.json（与 CI 同序）
    r = _run(tmp, "adapters/pydantic_adapter.py")
    shutil.rmtree(tmp, ignore_errors=True)
    assert r.returncode != 0, "错误 task 输出未传导为适配器非零退出码（N6 回归）"
    assert '"route2b_all_consistent": false' in r.stdout
    assert '"pairs_reported": 22' in r.stdout


def test_assertions_not_skipped_or_weakened():
    """断言完整性：关键测试文件无 skip 标记、无降级为 warning。"""
    for f in (ROOT / "tests").glob("test_*.py"):
        if f.name == "test_gate_regressions.py":
            continue  # 自身包含被检测字面量（自引用排除，同 terminal_scan 先例）
        s = f.read_text(encoding="utf-8")
        assert "pytest.skip" not in s and "@pytest.mark.skip" not in s, f"{f.name} 含 skip"
        assert "pytest.warns" not in s, f"{f.name} 断言降级为 warns"
