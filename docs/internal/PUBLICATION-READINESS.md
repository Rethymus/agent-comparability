# PUBLICATION-READINESS（2026-10-25，公开前最终治理检查记录）

## 1. GitHub 权限与规则

**Rulesets 能力：确认可用**（非 404 推断——实证链：`rulesets` GET 返回 `[]`；POST 探针（enforcement=disabled、仅匹配 `__probe_only__` 幽灵分支）**创建成功 id=25847405** 后立即删除，终态 0 条）。Branch Protection 端点 404 = "未配置保护"而非"无能力"。账户 plan 字段 API 未暴露（`gh api user` plan 空），但 Rulesets 实测可用即结论成立。

**最小保护方案（已备好，待所有者授权执行）**：
- main：Ruleset `enforcement=active`，rules = deletion + non_fast_forward；require PR + status check `ci/conformance`
- 发行 tag：Ruleset target=branch, include `refs/tags/v*`，rules = deletion + non_fast_forward（+ update 视 API 支持）
- 不升级付费计划；不启用绕过豁免

## 2. 发行身份

- **v0.5.0 = commit `fb2e06f0019e15e9a5528ffa54e98295b63aebe3`**（远程 tag 对象 `0c20405a…` 解引用后与此逐字节一致）
- tag 内 pyproject=0.5.0、`__version__`=0.5.0（release_gate 语义四方一致）；该 commit 的 check-runs = success
- main HEAD（06c2079+）≠ tag SHA 属正常演进，未移动任何 tag

## 3. 公开前安全检查

| 范围 | 方法 | 结果 |
|---|---|---|
| 全部远程引用 | `git ls-remote` | main + release 两分支；v0.3.6/v0.3.7/v0.4.1/v0.5.0 四 tag |
| main 可达 Git 对象（22 commits，每个 blob） | 密钥/私钥/token 模式（含 gho_/ghp_）| **敏感 0**；二进制/NC 数据 blob 0 |
| Actions 运行日志 | API 全量 13 run = 11 success + 2 failure | 2 失败 = v0.3.6 workflow 语法错误（0s、无 job 日志、无敏感内容）——**保留不删** |
| 毒分支验证 run | 分支已删，run 不在默认列表 | 属门禁验证动作，无敏感内容 |
| Artifacts | 逐 run artifacts 计数 | **全部 0**（无残留构建产物） |
| 历史发行资产 | git 历史扫描 | dist 二进制仅存在于**未推送的本地 master**，远程不可达 |

**剩余不确定性（如实记录）**：① Rulesets 部分规则类型（tag update/immutable）在该账户的实际支持矩阵未逐一探测（只探测了创建能力）；② Actions 日志内容审核为关键词级+元数据级，非逐行人工通读 13 份日志（失败 2 份已确认无 job 输出）；③ GitHub 转公开将公开全部日志（官方文档），建议所有者点开 2 个失败 run 链接过目后再切换。

## 4. 遗留项（按指令未动）

- 远程 `release` 分支：保留（此前已证为 main 完全祖先、无独有提交）
- Topics：建议值 `llm-agents` / `evaluation` / `specification` / `conformance-testing`——待授权写入
- 无新研究报告；后续 Issue/PR 维护

## 5. 结论

**不存在阻断公开的技术问题**（PUBLISH-READY）。公开动作清单（均需所有者逐项批准）：
① Branch Protection Rulesets 落地（方案在案）→ ② Topics → ③ 失败 run 人工过目 → ④ 仓库转 public → ⑤ （可选）GitHub Release v0.5.0 → ⑥ （可选）PyPI（Trusted Publishing）。
