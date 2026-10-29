"""CDR 消费侧校验器（python -m agent_comparability.validate）三退出码回归。

退出码契约（消费侧，与产出侧 CLI 的 0/2 契约互补，见模块文档）：
  0 = 结构有效且 policy_version 可识别（cmp/0.3.x 或 cmp/0.4.x，旧 CDR 向后兼容）
  1 = 结构有效但 policy_version 无法识别 —— SPEC §5：必须丢弃该 CDR 并重新判定，不得部分信任
  2 = 结构/schema 违规 —— 诊断精确到字段（如 limitations[0]、admissibility）
required 字段清单运行时读包内 data/cdr.schema.json（单一事实来源，非硬编码）。
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from agent_comparability.core import adjudicate

ROOT = Path(__file__).resolve().parents[1]


def run_validate(path):
    return subprocess.run([sys.executable, "-m", "agent_comparability.validate", str(path)],
                          capture_output=True, text=True, cwd=ROOT)


def valid_cdr():
    """真实管线产出（参考实现 adjudicate）——恒等式：产出器的输出必须过自家消费校验器。"""
    case = json.loads((ROOT / "examples" / "demo-case.json").read_text(encoding="utf-8"))
    return adjudicate(case, "score_comparison").to_dict()


def tmp_cdr(tmp_path, *mutations, name="cdr.json", raw=None):
    if raw is not None:
        p = tmp_path / name
        p.write_text(raw, encoding="utf-8")
        return p
    cdr = valid_cdr()
    for m in mutations:
        m(cdr)
    p = tmp_path / name
    p.write_text(json.dumps(cdr, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


# ---------- exit 0：结构有效 + policy_version 可识别 ----------

def test_pipeline_cdr_exit0(tmp_path):
    """参考实现产出的 CDR 必须被自家校验器接受（消费闭环恒等式）。"""
    r = run_validate(tmp_cdr(tmp_path))
    assert r.returncode == 0, r.stderr
    assert "OK" in r.stdout
    assert "cmp/0.4.0" in r.stdout


def test_legacy_cmp031_cdr_exit0(tmp_path):
    """向后兼容：旧 cmp/0.3.1 CDR 的 policy_version 仍可识别（schema pattern 收 0.3.x）。"""
    r = run_validate(tmp_cdr(tmp_path, lambda c: c.update(policy_version="cmp/0.3.1")))
    assert r.returncode == 0, r.stderr
    assert "cmp/0.3.1" in r.stdout


@pytest.mark.parametrize("pv", ["cmp/0.3.2", "cmp/0.4.7"])
def test_patch_versions_recognized_exit0(tmp_path, pv):
    r = run_validate(tmp_cdr(tmp_path, lambda c: c.update(policy_version=pv)))
    assert r.returncode == 0, r.stderr


# ---------- exit 1：结构有效但 policy_version 无法识别 ----------

@pytest.mark.parametrize("pv", ["cmp/9.9", "cmp/0.5.0", "not-a-version"])
def test_unknown_policy_version_exit1(tmp_path, pv):
    """SPEC §5：不认识的 policy_version → 必须丢弃该 CDR 并重新判定，不得部分信任。"""
    r = run_validate(tmp_cdr(tmp_path, lambda c: c.update(policy_version=pv)))
    assert r.returncode == 1
    assert pv in r.stderr
    assert "丢弃" in r.stderr and "重新判定" in r.stderr
    assert "部分信任" in r.stderr          # 明确禁止部分信任
    assert "SPEC" in r.stderr              # 指引注明规范出处
    assert "OK" not in r.stdout            # 绝不以成功口吻放行


def test_structural_violation_dominates_version_check(tmp_path):
    """结构违规优先于版本识别：结构已坏时不得落入 exit 1 的"可丢弃但结构良好"分支。"""
    r = run_validate(tmp_cdr(tmp_path,
                             lambda c: c.update(policy_version="cmp/9.9"),
                             lambda c: c.pop("case_id")))
    assert r.returncode == 2
    assert "case_id" in r.stderr


# ---------- exit 2：结构/schema 违规，诊断精确到字段 ----------

def test_missing_field_exit2(tmp_path):
    r = run_validate(tmp_cdr(tmp_path, lambda c: c.pop("evidence_refs")))
    assert r.returncode == 2
    assert "evidence_refs" in r.stderr


def test_missing_fields_all_reported_exit2(tmp_path):
    """多字段缺失时诊断逐字段列出（收集式，不只报第一个）。"""
    r = run_validate(tmp_cdr(tmp_path,
                             lambda c: c.pop("evidence_refs"),
                             lambda c: c.pop("limitations")))
    assert r.returncode == 2
    assert "evidence_refs" in r.stderr and "limitations" in r.stderr


def test_tampered_limitations_exit2(tmp_path):
    """防篡改声明被剔除（limitations 不含 抗恶意篡改|tamper）→ exit 2，诊断点名 limitations。"""
    r = run_validate(tmp_cdr(tmp_path,
                             lambda c: c.update(limitations=["与本裁决无关的一般性说明"])))
    assert r.returncode == 2
    assert "limitations" in r.stderr
    assert "抗恶意篡改" in r.stderr or "tamper" in r.stderr


def test_tampered_limitations_index_in_diagnostic(tmp_path):
    """诊断精确到数组下标：不匹配项以 limitations[i] 形式点名。"""
    r = run_validate(tmp_cdr(tmp_path,
                             lambda c: c.update(limitations=["说明一", "说明二", "说明三"])))
    assert r.returncode == 2
    for idx in (0, 1, 2):
        assert f"limitations[{idx}]" in r.stderr


def test_empty_limitations_exit2(tmp_path):
    r = run_validate(tmp_cdr(tmp_path, lambda c: c.update(limitations=[])))
    assert r.returncode == 2
    assert "limitations" in r.stderr


def test_bad_admissibility_exit2(tmp_path):
    """admissibility 四值枚举镜像：任何越界值 → exit 2，诊断点名 admissibility。"""
    r = run_validate(tmp_cdr(tmp_path, lambda c: c.update(admissibility="MOSTLY_ADMISSIBLE")))
    assert r.returncode == 2
    assert "admissibility" in r.stderr


def test_wrong_type_exit2(tmp_path):
    r = run_validate(tmp_cdr(tmp_path, lambda c: c.update(case_id=123)))
    assert r.returncode == 2
    assert "case_id" in r.stderr


def test_array_item_type_exit2(tmp_path):
    """数组元素级诊断：精确到 supported_claims[1]。"""
    r = run_validate(tmp_cdr(tmp_path,
                             lambda c: c.update(supported_claims=["ok", 3])))
    assert r.returncode == 2
    assert "supported_claims[1]" in r.stderr


def test_unknown_top_level_field_exit2(tmp_path):
    """schema additionalProperties=false：CDR 顶层未知字段是违规（与 Record 级忽略规则不同层）。"""
    r = run_validate(tmp_cdr(tmp_path, lambda c: c.update(legacy_extra={"x": 1})))
    assert r.returncode == 2
    assert "legacy_extra" in r.stderr


def test_malformed_json_exit2(tmp_path):
    r = run_validate(tmp_cdr(tmp_path, raw='{"case_id": "x",,,}'))
    assert r.returncode == 2
    assert "JSON" in r.stderr or "json" in r.stderr


def test_unreadable_file_exit2(tmp_path):
    r = run_validate(tmp_path / "no-such-cdr.json")
    assert r.returncode == 2


def test_top_level_not_object_exit2(tmp_path):
    r = run_validate(tmp_cdr(tmp_path, raw='["a", "b"]'))
    assert r.returncode == 2


# ---------- 单一事实来源：required 清单确为运行时读 schema ----------

def test_required_list_follows_runtime_schema(tmp_path):
    """注入改动的 schema（required 只留 case_id）：其余字段缺失不再违规——
    证明 required 清单来自运行时读取的 data/cdr.schema.json，不是硬编码。"""
    from agent_comparability import validate as v

    schema = v.load_schema()
    assert "evidence_refs" in schema["required"]      # 前提：当前 schema 确含该字段
    slim = dict(schema, required=["case_id"])
    cdr = valid_cdr()
    cdr.pop("evidence_refs")
    cdr.pop("limitations")
    assert v.structural_errors(cdr, slim) == []
    assert any("evidence_refs" in e for e in v.structural_errors(cdr, schema))


def test_load_schema_reads_packaged_file():
    """load_schema 读的就是包内 data/cdr.schema.json（同文件同内容）。"""
    from agent_comparability import validate as v

    schema = v.load_schema()
    assert schema["required"] == json.loads(
        (Path(__file__).resolve().parents[1] / "src/agent_comparability/data/cdr.schema.json")
        .read_text(encoding="utf-8"))["required"]
