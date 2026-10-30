"""包环境自检（doctor）：PyPI 安装侧的只读自诊断入口。

用法：
    python -m agent_comparability doctor

定位：conformance/ 与 adapters/ 不随 wheel 分发（pyproject.toml [tool.setuptools]），
从 PyPI 安装的用户无法运行仓库的五项封闭门禁，也无法自证本地环境是否完整——
随包冻结案例在位、判定行为与随包预期一致、版本线一致。本模块只读检查这些前提，
只写 stdout、不写用户目录的任何文件（副作用纪律同 __main__.py）。

检查清单（全部纯 stdlib；除声明为 not_run 的项外逐项给出 pass/fail）：
  1. frozen_case_files      随包 data/ 三份冻结案例文件在位，且 A/B/D 对数
                            与预期一致（A=9、B=13、D=4，合计 26——预期值与
                            run_suite.py 的 case_sets 及 cases.py 加载器同源）。
  2. frozen_expectations    逐对抽验判定结果 vs 随包冻结预期。A 集随包文件只有
                            预期无 records（历史冻结形态），如实报告不判定；
                            B+D 集随包带 records，全部 17 对逐对核对（超出抽样
                            下限的全量核对）。
  3. policy_version_line    随包 SPEC.md 声明的 policy 版本 == core.POLICY_VERSION
                            （语义线一致）；同时报告包 __version__（软件线，
                            与 SPEC 是不同版本空间，仅报告不互比——三线版本见
                            README §12）。
  4. demo_cdr               用内置合成记录产出一份演示 CDR，并核对必填字段齐备
                            （required 清单运行时读自随包 data/cdr.schema.json）。
                            合成数据同 examples/ 的性质：仅验证管线可产出，
                            预期判定不写死在检查里（判定正确性由检查 2 覆盖）。
  5. schema_validation      有 jsonschema（[suite] extra）→ 对演示 CDR 做结构
                            校验；没有 → 如实输出 not run 与原因及安装指引，
                            绝不静默计为通过（AGENTS.md §1 同律：未运行的检查
                            不得计为通过）。
  6. case_set_digest        随包冻结语料内容寻址摘要（sha256，canonical JSON）。
                            **报告项（status=report）**：只报告摘要、不内嵌期望值
                            ——避免成为第二事实源；期望值在 CI 产物
                            conformance-results.json 顶层 case_set_digest 与发行
                            说明中，用户将本报告值与之比对（打通生产者↔消费者
                            比较域）。定义与 conformance/cases.py 的
                            case_set_digest() 孪生（A 集随包无 records，只锚
                            预期），一致性由 tests/test_gate_regressions.py N9
                            守卫；随包语料与 CI 语料的孪生同一性由
                            conformance/release_gate.py 在仓库/CI 侧守卫。

退出码契约：
    0 = 所有可执行检查通过（not_run 项在报告 checks_not_run 中如实列出；
        report 项是纯报告，不参与 pass/fail 判定）
    1 = 任一检查失败（报告 overall=fail；诊断逐项给出）

本模块不做任何判定语义判断之外的事：绝不修改文件、不发网络请求、不缓存状态。
"""
import hashlib
import json
import re
import sys
from importlib.resources import files as _pkg_files

from . import POLICY_VERSION, adjudicate, __version__

# ---- 冻结对数预期（同步来源：conformance/cases.py 加载器 A9+B13+D4=26；
#      conformance/run_suite.py case_sets 硬编码 A:9/B:13）----
EXPECTED_COUNTS = {"A": 9, "B": 13, "D": 4}

# 演示合成记录（SYNTHETIC/ILLUSTRATIVE，同 examples/demo-case.json 性质）：
# 同任务/同模型/仅 harness 不同、均 verified、reward∈[0,1] 未声明尺度。
_DEMO_CASE = {
    "id": "doctor-demo",
    "records": [
        {"task_id": "demo-task", "harness": "alpha", "model": "demo-model",
         "reward": 0.9, "reward_status": "verified"},
        {"task_id": "demo-task", "harness": "beta", "model": "demo-model",
         "reward": 0.7, "reward_status": "verified"},
    ],
}
_DEMO_CLAIM = "score_comparison"


def _read_pkg_data(name):
    """读随包 data/ 文件文本（单一入口，validate.load_schema 同模式）。"""
    return (_pkg_files("agent_comparability") / "data" / name).read_text(encoding="utf-8")


def check_frozen_case_files(frozen_a, boundary, cases_04):
    """检查 1：随包冻结案例在位且 A/B/D 对数与预期一致。"""
    counts = {
        "A": sum(len(c["expected_admissibility_by_claim"]) for c in frozen_a["cases"]),
        "B": sum(len(c["claims"]) for c in boundary["cases"]),
        "D": sum(len(c["claims"]) for c in cases_04["cases"]),
    }
    problems = [f"{k} 集 {counts[k]} 对 != 预期 {EXPECTED_COUNTS[k]} 对"
                for k in counts if counts[k] != EXPECTED_COUNTS[k]]
    check = {
        "status": "pass" if not problems else "fail",
        "counts": counts,
        "expected": dict(EXPECTED_COUNTS),
        "a_set_records_packaged": "records" in (frozen_a["cases"][0] if frozen_a["cases"] else {}),
    }
    if problems:
        check["problems"] = problems
    return check


def check_frozen_expectations(boundary, cases_04):
    """检查 2：逐对判定 vs 随包冻结预期（B+D 全量；A 集随包无 records，如实不判）。"""
    executed = passed = 0
    mismatches = []
    for set_name, blob in (("B", boundary), ("D", cases_04)):
        for c in blob["cases"]:
            for claim, expected in c["claims"].items():
                got = adjudicate({"id": c["id"], "records": c["records"]}, claim).admissibility
                executed += 1
                if got == expected:
                    passed += 1
                else:
                    mismatches.append({"set": set_name, "case": c["id"], "claim": claim,
                                       "got": got, "expected": expected})
    check = {"status": "pass" if not mismatches else "fail",
             "executed": executed, "passed": passed}
    if mismatches:
        check["mismatches"] = mismatches[:5]
    return check


def check_policy_version_line(spec_text):
    """检查 3：随包 SPEC 声明的 policy 版本 == core.POLICY_VERSION。"""
    m = re.search(r"cmp/\d+\.\d+(?:\.\d+)?", spec_text.splitlines()[0] if spec_text else "")
    declared = m.group(0) if m else None
    ok = declared is not None and declared == POLICY_VERSION
    return {"status": "pass" if ok else "fail",
            "spec_declares": declared, "core": POLICY_VERSION}


def _canonical_digest(obj):
    """canonical JSON（键排序 + 紧凑分隔符，UTF-8）后取 sha256。

    定义孪生：conformance/cases.py 的 canonical_digest（conformance/ 不随 wheel
    分发，无法 import——两份定义的一致性由 tests/test_gate_regressions.py N9 守卫，
    先例同 EXPECTED_COUNTS 的同步来源注释）。
    """
    payload = json.dumps(obj, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def check_case_set_digest(frozen_a, boundary, cases_04):
    """检查 6：随包冻结语料内容寻址摘要——**报告项，不判 pass/fail**。

    只报告 sha256、不内嵌期望值（避免第二事实源）：期望值在 CI 产物
    conformance-results.json 顶层 case_set_digest 与发行说明中，用户将本报告值
    与之比对；随包语料一旦与 CI 语料分歧（孪生漂移或历史版本包），摘要即不同。
    A 集随包只有预期无 records（历史冻结形态），只锚预期；B/D 锚预期+records
    ——与 cases.py 的 case_set_digest() 同一定义。
    """
    corpus = {
        "A": [{"case": c["id"], "claim": k, "expected": v}
              for c in frozen_a["cases"]
              for k, v in c["expected_admissibility_by_claim"].items()],
        "B": [{"case": c["id"], "claim": k, "expected": v, "records": c["records"]}
              for c in boundary["cases"] for k, v in c["claims"].items()],
        "D": [{"case": c["id"], "claim": k, "expected": v, "records": c["records"]}
              for c in cases_04["cases"] for k, v in c["claims"].items()],
    }
    return {"status": "report",
            "algorithm": "sha256(canonical-json:sort_keys+compact,utf-8)",
            "case_set_digest": _canonical_digest(corpus),
            "per_set": {k: _canonical_digest(v) for k, v in corpus.items()},
            "scope": {k: len(v) for k, v in corpus.items()},
            "compare_hint": "与 CI 产物 conformance-results.json 顶层 case_set_digest / 发行说明比对"}


def check_demo_cdr(case, claim, schema):
    """检查 4：演示 CDR 可产出且必填字段齐备（required 运行时读自随包 schema）。"""
    cdr = adjudicate(case, claim).to_dict()
    missing = [k for k in schema.get("required", []) if k not in cdr]
    check = {"status": "pass" if not missing else "fail",
             "admissibility": cdr["admissibility"],
             "required_keys_missing": missing}
    return check, cdr


def check_schema_validation(cdr_doc, schema, import_jsonschema=None):
    """检查 5：jsonschema 结构校验；缺 [suite] extra 时如实 not_run（不静默计过）。"""
    if import_jsonschema is None:
        def import_jsonschema():
            import jsonschema
            return jsonschema
    try:
        jsonschema = import_jsonschema()
    except ImportError:
        return {"status": "not_run",
                "reason": "未安装 jsonschema（可选 [suite] extra）",
                "install_hint": 'pip install "agent-comparability[suite]"'}
    validator = jsonschema.Draft202012Validator(schema)
    errs = sorted(validator.iter_errors(cdr_doc), key=lambda e: list(e.path))
    if errs:
        return {"status": "fail",
                "errors": [e.message[:120] for e in errs[:3]]}
    return {"status": "pass", "validator": "Draft202012"}


def run_checks():
    """装配全部检查并返回报告 dict（不打印、不退出——便于测试直接断言）。"""
    frozen_a = json.loads(_read_pkg_data("frozen-cases-a.json"))
    boundary = json.loads(_read_pkg_data("boundary-cases.json"))
    cases_04 = json.loads(_read_pkg_data("cases-0.4.json"))
    schema = json.loads(_read_pkg_data("cdr.schema.json"))
    spec_text = _read_pkg_data("SPEC.md")

    c1 = check_frozen_case_files(frozen_a, boundary, cases_04)
    c2 = check_frozen_expectations(boundary, cases_04)
    c3 = check_policy_version_line(spec_text)
    c4, cdr = check_demo_cdr(_DEMO_CASE, _DEMO_CLAIM, schema)
    c5 = check_schema_validation(cdr, schema)
    c6 = check_case_set_digest(frozen_a, boundary, cases_04)

    checks = {"frozen_case_files": c1, "frozen_expectations": c2,
              "policy_version_line": c3, "demo_cdr": c4, "schema_validation": c5,
              "case_set_digest": c6}
    any_fail = any(v["status"] == "fail" for v in checks.values())
    return {
        "overall": "fail" if any_fail else "pass",
        "package_version": __version__,
        "policy_version": POLICY_VERSION,
        "checks": checks,
        "checks_not_run": [k for k, v in checks.items() if v["status"] == "not_run"],
    }


def main(argv=None) -> int:
    report = run_checks()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["overall"] == "fail":
        print("doctor: FAIL —— 存在失败检查，本地环境与随包冻结产物不一致", file=sys.stderr)
        return 1
    if report["checks_not_run"]:
        print(f"doctor: PASS（{len(report['checks_not_run'])} 项未运行已如实列出）", file=sys.stderr)
    else:
        print("doctor: PASS", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
