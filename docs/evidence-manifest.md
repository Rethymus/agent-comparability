# Evidence Manifest — 来源与证据可信边界 / Evidence provenance & trust boundary

> **English summary below the Chinese section.** 本文档描述 `evidence/0.1` 清单（`agent_comparability.evidence`）。

## 中文

### 定位

Evidence Manifest 是 **CDR 外部**的轻量记录，回答"这份输入的证据从哪来、可信到什么程度"。它与 cmp 规范（当前 `cmp/0.4.0`）的关系：

- SPEC §1 的四层（L-claim / L-src / L-ours / L-none）是**记录级评分信任**，参与判定语义；
- Manifest 三态是**证据制品级**（evidence artifact level），是另一个维度，**不进入 `adjudicate()`、不改变任何 CDR 字段或判定结果**；`spec/SPEC.md` 与 `cdr.schema.json` 零改动。

### 三态与防自动升级

```
source_claimed  <  artifact_observed  <  independently_verified
```

| 态 | 触发条件（唯一途径） | 禁止 |
|---|---|---|
| `source_claimed` | 默认地板 | — |
| `artifact_observed` | 制品路径存在**且被实际读取**且 sha256 实算入清单 | 路径存在但未读取即标记 |
| `independently_verified` | 在 artifact_observed 之上存在显式 `verification`（method/operator/at） | 任何隐式升级；"验证记录但无制品"→ 不一致，不升级 |

规则实现于 `build_manifest()`（只依据提供的证据推导状态）与 `verify_manifest()`（重读制品重算摘要，供审计复用）。

### 字段

- 顶层：`manifest_version`（evidence/0.1）、`policy_version`（引用锚定）、`source_kind`、`source_version`（不可取得时为 `null`，诚实记录）、`case_id`、`requested_claim`、`mapping_warnings[]`、`unsupported_capabilities[]`
- 每记录：`record_id`（`records[i]` 指针）、`task_identity`（task_id/model/harness）、`artifact_ref`、`file_digest`（`sha256:…`，读后实算）、`verification_state`、`verification`（或 `null`）、`unverified_reason`（非更高态时的原因）、`provenance_note`

### CLI 用法

```bash
python -m agent_comparability input.json --claim score_comparison --manifest out.manifest.json
```

离线 JSON 的诚实默认：输入文件即证据制品；全部记录 `artifact_observed`；`unsupported_capabilities=["source_side_verification_unavailable"]`；**不含任何独立验证声明**。

## English

The Evidence Manifest (`evidence/0.1`) is a lightweight record **outside** the CDR documenting where input evidence came from and how far it can be trusted. The three artifact-level states (`source_claimed` < `artifact_observed` < `independently_verified`) are a **different dimension** from SPEC §1's record-level score-trust tiers (L-claim/L-src/L-ours/L-none): they never enter `adjudicate()` and never alter CDR outcomes. Upgrades are only ever triggered by explicit evidence — an artifact is only "observed" after the file is actually read and its sha256 computed; `independently_verified` additionally requires an explicit verification entry (method/operator/at). No implicit transitions exist: a missing artifact pins the floor state with a warning, and a verification without an observed artifact is flagged inconsistent rather than upgrading. CLI: `python -m agent_comparability input.json --claim X --manifest out.manifest.json` — the honest offline default marks all records `artifact_observed` (input file as artifact) with no independent-verification claims. `verify_manifest()` recomputes digests for audit reuse.
