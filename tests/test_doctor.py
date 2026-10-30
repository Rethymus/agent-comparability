"""doctor（python -m agent_comparability doctor）包环境自检回归。

契约（doctor.py 模块头）：
  exit 0 = 可执行检查全部通过（not_run 项在 checks_not_run 如实列出，不计为通过）
  exit 1 = 任一检查失败
not_run 是诚实降级，绝不冒充 pass（AGENTS.md §1 同律）；负向路径用注入/篡改数据
证明检查器真的能发现漂移，而非恒真。
"""
import copy
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_comparability.doctor import (  # noqa: E402
    _DEMO_CASE,
    _DEMO_CLAIM,
    check_demo_cdr,
    check_frozen_case_files,
    check_frozen_expectations,
    check_policy_version_line,
    check_schema_validation,
    _read_pkg_data,
)


def _run_doctor():
    return subprocess.run([sys.executable, "-m", "agent_comparability", "doctor"],
                          capture_output=True, text=True, cwd=ROOT)


def _report(r):
    return json.loads(r.stdout)


def _schema():
    return json.loads(_read_pkg_data("cdr.schema.json"))


# ---------- 主路径：整体通过 + 报告结构 ----------

def test_doctor_exit0_and_report_structure():
    r = _run_doctor()
    assert r.returncode == 0, r.stdout + r.stderr
    rep = _report(r)
    assert rep["overall"] == "pass"
    assert rep["policy_version"] == "cmp/0.4.0"
    assert isinstance(rep["package_version"], str) and rep["package_version"]
    assert set(rep["checks"]) == {"frozen_case_files", "frozen_expectations",
                                  "policy_version_line", "demo_cdr", "schema_validation"}
    assert rep["checks_not_run"] == []
    assert all(v["status"] == "pass" for v in rep["checks"].values()), rep["checks"]


def test_doctor_frozen_case_counts():
    rep = _report(_run_doctor())
    c = rep["checks"]["frozen_case_files"]
    assert c["counts"] == {"A": 9, "B": 13, "D": 4}, "A/B/D 对数漂移（26=9+13+4）"
    assert c["a_set_records_packaged"] is False, "A 集随包形态须如实报告（只有预期无 records）"


def test_doctor_expectation_sample_full_bd():
    rep = _report(_run_doctor())
    c = rep["checks"]["frozen_expectations"]
    assert c["executed"] == 17 and c["passed"] == 17, "B+D 逐对抽验必须全过"


def test_doctor_policy_version_line_matches_core():
    rep = _report(_run_doctor())
    c = rep["checks"]["policy_version_line"]
    assert c["spec_declares"] == c["core"] == "cmp/0.4.0"


def test_doctor_demo_cdr_schema_required_present():
    rep = _report(_run_doctor())
    c = rep["checks"]["demo_cdr"]
    assert c["status"] == "pass" and c["required_keys_missing"] == []
    assert c["admissibility"] in ("ADMISSIBLE", "INADMISSIBLE", "PARTIAL", "INCONCLUSIVE")


def test_doctor_schema_validation_runs_with_suite_extra():
    _, cdr = check_demo_cdr(_DEMO_CASE, _DEMO_CLAIM, _schema())
    assert check_schema_validation(cdr, _schema())["status"] == "pass"


# ---------- 诚实降级：not_run 绝不冒充 pass ----------

def test_doctor_schema_not_run_reported_honestly():
    """缺 jsonschema（[suite] extra）→ not_run + 原因 + 安装指引，绝不计为 pass。"""

    def _missing():
        raise ImportError("No module named 'jsonschema'")

    _, cdr = check_demo_cdr(_DEMO_CASE, _DEMO_CLAIM, _schema())
    c = check_schema_validation(cdr, _schema(), import_jsonschema=_missing)
    assert c["status"] == "not_run", "依赖缺失必须与 pass 可区分"
    assert "jsonschema" in c["reason"] and "suite" in c["install_hint"]


# ---------- 负向路径：检查器必须能发现真实漂移（非恒真） ----------

def test_doctor_detects_tampered_frozen_expectation():
    boundary = json.loads(_read_pkg_data("boundary-cases.json"))
    tampered = copy.deepcopy(boundary)
    first = tampered["cases"][0]
    claim = next(iter(first["claims"]))
    first["claims"][claim] = "ADMISSIBLE" if first["claims"][claim] != "ADMISSIBLE" else "INADMISSIBLE"
    c = check_frozen_expectations(boundary, tampered)
    assert c["status"] == "fail", "判定与随包预期不一致必须被判 fail"
    assert c["passed"] < c["executed"] and c["mismatches"]


def test_doctor_detects_count_mismatch():
    boundary = json.loads(_read_pkg_data("boundary-cases.json"))
    short = copy.deepcopy(boundary)
    short["cases"] = short["cases"][:-1]  # 少一份案例 → B 对数低于预期
    c = check_frozen_case_files(json.loads(_read_pkg_data("frozen-cases-a.json")),
                                short, json.loads(_read_pkg_data("cases-0.4.json")))
    assert c["status"] == "fail" and c["counts"]["B"] == 12, c


def test_doctor_detects_policy_version_line_drift():
    c = check_policy_version_line("# Spec — cmp/0.3.1 (superseded)\n")
    assert c["status"] == "fail" and c["spec_declares"] == "cmp/0.3.1"
    c2 = check_policy_version_line("# Spec without version line\n")
    assert c2["status"] == "fail" and c2["spec_declares"] is None


def test_doctor_detects_schema_violating_cdr():
    """缺必填字段的 CDR（模拟 schema 演进后旧产物缺字段）→ schema 校验 fail 分支。"""
    schema = _schema()
    broken = {"case_id": "x"}  # 仅一个字段，缺其余全部 required
    sv = check_schema_validation(broken, schema)
    assert sv["status"] == "fail" and sv["errors"], "缺必填字段的 CDR 必须被判 fail"


def test_doctor_demo_cdr_missing_required_key_is_fail():
    """required 清单运行时扩展（注入多出的必填键）→ demo_cdr 检查 fail 而非恒 pass。"""
    stricter = dict(_schema(), required=list(_schema()["required"]) + ["evidence_digest"])
    c, _ = check_demo_cdr(_DEMO_CASE, _DEMO_CLAIM, stricter)
    assert c["status"] == "fail" and c["required_keys_missing"] == ["evidence_digest"]
