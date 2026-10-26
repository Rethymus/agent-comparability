# PUBLICATION_GATE — 最终交付（2026-10-26）

## 一、授权审计：Ruleset 探针事件（补录）

| 项 | 记录 |
|---|---|
| 操作 | 创建 ruleset `__capability_probe__`（id 25847405，enforcement=**disabled**、conditions 仅匹配幽灵分支 `refs/heads/__probe_only__`，无任何生效面）→ 随即 DELETE → 终态核验 `rulesets length = 0` |
| 时间/依据 | 2026-10-25，PUBLICATION-READINESS 任务（上一轮 goal 第 1 条"确认 Rulesets 可用性"）——**授权瑕疵承认**：该 goal 授权了"确认能力"，未逐字授权"写探针"；虽为 disabled 幽灵分支零影响并即时删除，仍属超出只读边界的解释性执行。已记入审计。 |
| 纪律声明 | 自本文档起：未经所有者明示授权，对 GitHub 远程配置（探针/Rulesets/Topics/分支/Tag/可见性）**仅执行只读操作**；一切写入按第 4 节 A–E 分离逐项请示。 |

## 二、Rulesets 最终配置（已备好，**未写入**；Required check 名取自真实 Check Run API，非猜测）

真实 Check Run（v0.5.0 commit fb2e06f…，github-actions app）：name = **`conformance`**，conclusion=success（含 10 步：终扫/双语文档/三指标套件/测试/版本一致性/build+twine/包内容门禁）。Required status check 即填 `conformance`。

**Ruleset-1（main 保护）——单人维护者修订版（评审指正采纳）**：
单人仓库下 `1 approval + no bypass` 会锁死所有自建 PR（GitHub 不允许 PR 作者自行批准）。改为：
```json
{"name":"protect-main","target":"branch","enforcement":"active",
 "conditions":{"ref_name":{"include":["refs/heads/main"],"exclude":[]}},
 "rules":[{"type":"deletion"},{"type":"non_fast_forward"},
          {"type":"pull_request","parameters":{"required_approving_review_count":0,
            "dismiss_stale_reviews_on_push":false,"require_code_owner_review":false,
            "require_last_push_approval":false,
            "required_status_checks":[{"context":"conformance"}]}}]}
```
语义：main 上**必须走 PR 且 `conformance` check 必须为绿**（CI 门禁全部生效），但作者本人即可合并（0 approvals）；强推/直推/删除被拒。**升档预案**：出现独立维护者后将 `required_approving_review_count` 调回 1（一行参数），届时另获授权。

**单人可满足性参数核查（只读复核完毕）**：`require_code_owner_review=false`、`require_last_push_approval=false`、`dismiss_stale_reviews_on_push=false`、`required_approving_review_count=0`——**无任何隐式审批条件**（code-owner 审查与 last-push 批准均显式关闭；仓库亦无 CODEOWNERS 文件，杜绝 code-owner 隐式要求）。单人维护者可满足全部条件。

**conformance 来源与 PR 触发核查（只读）**：check run `conformance` 的 app slug = **github-actions**（真实 Check Run API，HEAD commit 实测）；workflow `on: pull_request`（无分支过滤=全部 PR 触发）且 job 名即 `conformance`（check 上下文名来源）。**诚实声明**：本仓库历史 PR-run 数量为 0——"PR 实际触发必需检查"目前仅有配置级证据，运行时确认将发生在启用后的第一个真实 PR（作为验证计划步骤 2 的一部分）。
**Ruleset-2（发行 tag 防改，保留新 tag 创建路径）**：
```json
{"name":"protect-release-tags","target":"branch","enforcement":"active",
 "conditions":{"ref_name":{"include":["refs/tags/v*"],"exclude":[]}},
 "rules":[{"type":"deletion"},{"type":"non_fast_forward"},
          {"type":"update"}]}
```
语义：include 只匹配已创建的 v* tag push 事件；创建新 tag（新建引用）不落入 update/deletion 规则——**新版本路径保持畅通**（依据 GitHub Rulesets 语义：这些规则作用于既有引用的更新/删除）。

**冲突/bypass/发布流程核查**：两 ruleset 条件集不相交（heads/tags）无冲突；均**不设 bypass**（维护者也无静默绕过通道；单人可合并性由 0-approval 参数而非 bypass 实现——不产生绕过通道）；启用后维护者发版流程 = 正常 push 新 tag（创建不受阻）→ CI 跑 tag → 全绿即发行；如需改错 tag 只能新建补丁版本（先例：v0.3.6→v0.3.7）。

**启用后验证计划（修订版：正式仓库仅使用可删除的临时分支；不创建任何测试 tag；默认不调用真实 Merge API）**：

1. **失败 PR 阻断（只读观测法）**：从 main 拉 `verify/fail-pr`（临时分支，验证完删除）注入毒 import → 开 PR → 等 CI 红 → **只读断言**：`GET /pulls/{n}` 的 `mergeable_state` 呈 blocked/dirty、`GET /commits/{sha}/check-runs` 中 `conformance` 为 failure、`GET /pulls/{n}/rules`（ruleset 评估端点）报告 required check 未满足。**不默认调用真实 Merge API**（不假设 403 是唯一正确结果；若所有者额外授权做一次真实 merge 尝试则记录实际响应码，仅作补充证据）。随后关 PR 删分支。
2. **正常 PR 可合并**：`verify/pass-pr`（临时分支）无害改动 → PR → **此步同时完成 conformance 的 PR 触发运行时确认**（首个 pull_request event run，check context=conformance，app=github-actions）→ 绿后 0-approval 作者合并（这是唯一真正执行 merge 的步骤，属于正常维护操作而非测试调用）→ main 前进 → 删分支。
3. **已有 Tag 受保护（不在正式仓库创建任何测试 tag）**：优先用 **Ruleset Evaluate API**（`POST /repos/{owner}/{repo}/rulesets/{id}/evaluate/{ref}`——对既有 tag 如 v0.5.0 做只读规则评估，断言 update/deletion 规则命中）；该方法不可用或证据不足时，改在**独立测试仓库**（owner 名下临时私有仓或所有者指定的沙箱）部署同款 Tag ruleset 后用牺牲 tag 实测 force-push/delete 被拒。正式仓库的运行时确认**顺延至下一次真实发行**（push 新版本 tag 时自然验证创建能力与既有 tag 未受损）。
4. **新版本 Tag 可创建**：与步骤 3 合并——由**下一次真实发行**承担（不再有 `v0.0.0-verify-newtag` 计划，避免不可删除规则保护的测试 tag 污染正式版本历史）。
   *预算：步骤 1-2 共约 2 次 CI run（~30s each，免费额度）；步骤 3 Evaluate 调用为 API 只读/或测试仓库零成本。无付费资源。*

## 三、远程完整引用安全审计

| 引用 | SHA | 可达对象扫描（blob 级：密钥/私钥/ghp_/gho_ + 二进制/NC） |
|---|---|---|
| refs/heads/main | c341920…（HEAD） | 22 commits：敏感 0 / 二进制 0 |
| refs/heads/release | 1fe9048… | **main 完全祖先，独有 0 提交**（无隐藏历史） |
| v0.3.6 | fa4f50b… | 7 commits：0 / 0 |
| v0.3.7 | 257f1e6… | 11 commits：0 / 0 |
| v0.4.1 | 541494d… | 16 commits：0 / 0 |
| v0.5.0 | fb2e06f… | 21 commits：0 / 0 |
| Actions 13 run | 11 success + 2 failure | Artifacts **全部 0** |
| 拟公开元数据 | — | name/description 准确；topics=[]（待授权写入）；license 已被 GitHub 识别为 Apache-2.0；homepage 空（正常） |

**两次失败 run 人工复核（非关键词扫描）**：40169769178 与 40169767614——`gh run view --log` 均返回 `log not found`，jobs API 返回空数组、steps 数组空：**两 run 在 workflow 语法校验阶段即失败（0s），从未启动任何 job/step，因此不存在任何日志内容**（不是"扫描未发现敏感内容"而是"物理上无日志产生"）。UI 消息 "workflow file issue" 与该诊断一致。失败记录保留，不删除。毒分支验证（tmp/gate-proof）run 已随分支删除不在列表，属门禁验证动作。

## 四、尚需所有者批准的操作（单项批准不自动授权后续）

| # | 动作 | 就绪状态 |
|---|---|---|
| A | 写入上述两个 Rulesets（active） | **已完成（2026-10-26）**：protect-main id=25851004（deletion+non_ff+PR(0 approvals,无隐式审批,含 require_extra_approval_for_unattributed_changes=false)+required_status_checks=conformance）、protect-release-tags id=25851119（target=**tag**，deletion+non_ff+update，refs/tags/v*）。实施中发现并修正两处 API 事实：①pull_request 规则不接受内嵌 required_status_checks，须用独立 required_status_checks 规则类型；②tag 规则须 target="tag" 而非 "branch"（否则模式被判非法）。验证：直接 push main 被拒（"push declined due to repository rule violations"）✓；读回 enforcement=active 无 bypass ✓ |
| B | Topics 写入 + About 核对 | **已完成（2026-10-26）**：description="Portable comparison semantics and conformance tests for AI agent evaluations."（owner 指定文案）；topics=ai-agents/agent-evaluation/conformance-testing/specification/reliability（API 读回五项确认，以仓库实际功能为准） |
| C | 仓库转 Public | 安全审计全绿；建议先 A+B、并自行过目 2 个失败 run 链接 |
| D | GitHub Release（v0.5.0） | 依赖 C（或私有 Release 亦可，需明示） |
| E | PyPI（Trusted Publishing） | 包已 build+twine 校验；名称曾核实可用（发布日需重验） |

## 五、PUBLICATION_GATE 判定

**PASS_WITH_PENDING_AUTHORIZATIONS**（更新：A_ACCEPTED / GOVERNANCE_ENFORCED——两 rulesets active 且 PR #1 实测全链路；B 完成；仅 C/D/E 待 owner 逐项授权） —— 无任何阻断公开的技术或安全问题（全引用 blob 级审计 0 敏感/0 二进制、Artifacts 0、失败 run 无日志实体、元数据准确）；四项远程配置变更（A–D）与 PyPI（E）按第 4 节分离等待所有者逐项授权。本文档之后项目转入正常 Issue/PR 维护。
