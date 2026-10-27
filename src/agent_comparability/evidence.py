"""Evidence Manifest（#18）——CDR 外部的来源与证据可信边界。

三态（**证据制品级**，与 SPEC §1 的记录级评分信任四层是不同维度，绝不进入
adjudicate、不改变任何 CDR 字段或判定结果）：

    source_claimed < artifact_observed < independently_verified

升级只能由显式证据触发：
  - artifact_observed ⟺ 制品路径存在且被实际读取且 sha256 已实算记录；
  - independently_verified ⟺ 在 artifact_observed 之上存在显式 verification 条目
    （method/operator/at 三者齐备）；
  - 无制品 → 地板 source_claimed + 警告；有 verification 无制品 → 不一致，不升级。
不存在任何隐式跃迁（防"证据不足被包装成可信结论"）。
"""
import hashlib

from . import POLICY_VERSION

MANIFEST_VERSION = "evidence/0.1"
STATES = ("source_claimed", "artifact_observed", "independently_verified")


def _digest(path):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
    except OSError:
        return None
    return "sha256:" + h.hexdigest()


def build_manifest(case, source_kind, source_version=None, artifacts=None,
                   verifications=None, requested_claim=None,
                   unsupported_capabilities=None):
    """构建 manifest。artifacts: {record_index: 制品路径}；verifications: {record_index:
    {method, operator, at}}。状态只由提供的证据决定——本函数绝不主动升级。"""
    artifacts = artifacts or {}
    verifications = verifications or {}
    warnings = []
    records = []
    for i, r in enumerate(case["records"]):
        state, digest, art_ref, reason = "source_claimed", None, None, None
        if i in artifacts:
            art_ref = artifacts[i]
            digest = _digest(art_ref)
            if digest is None:
                warnings.append(f"records[{i}]:artifact_missing({art_ref} 不可读——保持 source_claimed)")
                reason = f"artifact_unreadable:{art_ref}"
            else:
                state = "artifact_observed"
        else:
            warnings.append(f"records[{i}]:artifact_missing(未提供制品——保持 source_claimed)")
            reason = "no_artifact_provided"
        verification = None
        if i in verifications:
            v = verifications[i]
            valid = isinstance(v, dict) and {"method", "operator", "at"} <= set(v)
            if state != "artifact_observed":
                warnings.append(f"records[{i}]:verification_without_artifact("
                                f"无法独立验证从未观察过的制品——不升级)")
            elif not valid:
                warnings.append(f"records[{i}]:verification_entry_invalid(需 method/operator/at)")
            else:
                state = "independently_verified"
                verification = {"method": v["method"], "operator": v["operator"], "at": v["at"]}
        records.append({
            "record_id": f"records[{i}]",
            "task_identity": {"task_id": r["task_id"], "model": r["model"], "harness": r["harness"]},
            "artifact_ref": art_ref,
            "file_digest": digest,
            "verification_state": state,
            "verification": verification,
            "unverified_reason": reason,
            "provenance_note": (f"state={state}; artifact="
                                f"{'read+sha256' if digest else 'none'}; source={source_kind}"),
        })
    return {
        "manifest_version": MANIFEST_VERSION,
        "policy_version": POLICY_VERSION,  # 引用锚定：标识判定所用规范版本，不参与判定
        "source_kind": source_kind,
        "source_version": source_version,  # None = 不可取得（诚实记录，不猜测）
        "case_id": case["id"],
        "requested_claim": requested_claim,
        "records": records,
        "mapping_warnings": warnings,
        "unsupported_capabilities": unsupported_capabilities or [],
    }


def verify_manifest(manifest):
    """重算校验（供审计与后续转换器复用）：重读 artifact 实算摘要比对记录值。
    返回问题列表；空列表 = 干净。只验证已声明观察过的制品——不产生新状态。"""
    problems = []
    for e in manifest.get("records", []):
        rid, ref, dig = e.get("record_id"), e.get("artifact_ref"), e.get("file_digest")
        if e.get("verification_state") in ("artifact_observed", "independently_verified"):
            if not ref or not dig:
                problems.append(f"{rid}:structural(声明已观察但缺 artifact_ref/file_digest)")
                continue
            now = _digest(ref)
            if now is None:
                problems.append(f"{rid}:artifact_missing_on_reverify({ref})")
            elif now != dig:
                problems.append(f"{rid}:digest_mismatch({ref})")
        if e.get("verification_state") == "independently_verified" and not e.get("verification"):
            problems.append(f"{rid}:structural(verified 态缺 verification 条目)")
    return problems
