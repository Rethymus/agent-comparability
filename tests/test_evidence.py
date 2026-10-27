"""Evidence Manifest 规则回归（#18）——负向先行：防自动升级是核心不变式。

三态（制品级，与 SPEC §1 记录级四层不同维度，不进入 adjudicate）：
  source_claimed < artifact_observed < independently_verified
升级只能由显式证据触发；任何隐式跃迁都是缺陷。
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_comparability.evidence import build_manifest, verify_manifest  # noqa: E402


def _case(tmp_path):
    case = {"id": "ev-demo", "records": [
        {"task_id": "t1", "harness": "h1", "model": "m1", "reward": 1.0, "reward_status": "verified"},
        {"task_id": "t1", "harness": "h2", "model": "m1", "reward": 0.5, "reward_status": "verified"},
    ]}
    p = tmp_path / "case.json"
    p.write_text(json.dumps(case), encoding="utf-8")
    return case, p


def test_default_floor_is_source_claimed_without_artifact(tmp_path):
    """无制品：全部 source_claimed 地板 + artifact_missing 警告——绝不出 Artifact 态。"""
    case, p = _case(tmp_path)
    m = build_manifest(case, source_kind="offline_json", artifacts={})
    states = {e["record_id"]: e["verification_state"] for e in m["records"]}
    assert set(states.values()) == {"source_claimed"}
    assert any("artifact_missing" in w for w in m["mapping_warnings"])


def test_artifact_observed_requires_actual_read_and_real_digest(tmp_path):
    """制品存在且被读取：artifact_observed + sha256 必须等于实算值。"""
    case, p = _case(tmp_path)
    m = build_manifest(case, source_kind="offline_json",
                       artifacts={0: str(p), 1: str(p)})
    for e in m["records"]:
        assert e["verification_state"] == "artifact_observed"
        expect = hashlib.sha256(p.read_bytes()).hexdigest()
        assert e["file_digest"] == f"sha256:{expect}"
        assert e["provenance_note"]
    assert m["mapping_warnings"] == []


def test_nonexistent_artifact_stays_claimed_with_warning(tmp_path):
    """制品路径不存在：保持 source_claimed + 警告（不得假装观察过）。"""
    case, _ = _case(tmp_path)
    m = build_manifest(case, source_kind="x", artifacts={0: str(tmp_path / "ghost.eval")})
    assert m["records"][0]["verification_state"] == "source_claimed"
    assert any("artifact_missing" in w for w in m["mapping_warnings"])
    assert m["records"][0]["unverified_reason"]


def test_no_auto_upgrade_claimed_to_verified(tmp_path):
    """核心不变式：没有任何独立验证记录时，无论提供什么，绝不出 independently_verified。"""
    case, p = _case(tmp_path)
    m = build_manifest(case, source_kind="x", artifacts={0: str(p), 1: str(p)})
    assert all(e["verification_state"] == "artifact_observed" for e in m["records"])


def test_verified_requires_artifact_plus_explicit_verification(tmp_path):
    case, p = _case(tmp_path)
    m = build_manifest(case, source_kind="x", artifacts={0: str(p), 1: str(p)},
                       verifications={0: {"method": "manual_final_state_check",
                                          "operator": "human-1", "at": "2026-10-27T00:00:00+08:00"}})
    by = {e["record_id"]: e for e in m["records"]}
    assert by["records[0]"]["verification_state"] == "independently_verified"
    assert by["records[0]"]["verification"]["method"] == "manual_final_state_check"
    assert by["records[1]"]["verification_state"] == "artifact_observed"  # 无验证记录 → 不升级


def test_verification_without_artifact_is_inconsistent_not_verified(tmp_path):
    """验证记录但无制品观察 → 不一致：降回 artifact 层之下并记警告（不能验证从未观察的东西）。"""
    case, _ = _case(tmp_path)
    m = build_manifest(case, source_kind="x", artifacts={},
                       verifications={0: {"method": "m", "operator": "o", "at": "t"}})
    assert m["records"][0]["verification_state"] == "source_claimed"
    assert any("verification_without_artifact" in w for w in m["mapping_warnings"])


def test_verify_manifest_recomputes_and_catches_tampering(tmp_path):
    """verify_manifest 重算摘要：制品被篡改 → mismatch（exit 语义供审计复用）。"""
    case, p = _case(tmp_path)
    m = build_manifest(case, source_kind="x", artifacts={0: str(p)})
    assert verify_manifest(m) == []  # 未篡改：无问题
    p.write_text(json.dumps(case) + " ", encoding="utf-8")  # 篡改（字节变化）
    problems = verify_manifest(m)
    assert any("digest_mismatch" in x for x in problems)


def test_manifest_carries_policy_but_does_not_touch_cdr():
    """manifest 携带 policy_version 仅为引用锚定；结构上不含任何 CDR 判定字段。"""
    case = {"id": "c", "records": [
        {"task_id": "t", "harness": "h", "model": "m", "reward": 1.0, "reward_status": "verified"}]}
    m = build_manifest(case, source_kind="x")
    assert m["policy_version"] == "cmp/0.4.0"
    for banned in ("admissibility", "supported_claims", "violated_conditions"):
        assert banned not in m


def test_cli_manifest_flag(tmp_path):
    """CLI --manifest：输入文件即制品、实算摘要、全部 artifact_observed、零 verification。"""
    case, p = _case(tmp_path)
    out = tmp_path / "out.manifest.json"
    r = subprocess.run([sys.executable, "-m", "agent_comparability", str(p),
                        "--claim", "score_comparison", "--manifest", str(out)],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    m = json.loads(out.read_text(encoding="utf-8"))
    assert m["source_kind"] == "offline_json"
    assert m["case_id"] == "ev-demo" and m["requested_claim"] == "score_comparison"
    assert all(e["verification_state"] == "artifact_observed" for e in m["records"])
    expect = hashlib.sha256(p.read_bytes()).hexdigest()
    assert all(e["file_digest"] == f"sha256:{expect}" for e in m["records"])
    # 离线 CLI 绝不冒充独立验证：无顶层 verifications，逐记录 verification 为 None
    assert "verifications" not in m
    assert all(e["verification"] is None for e in m["records"])
    assert m["unsupported_capabilities"] == ["source_side_verification_unavailable"]
