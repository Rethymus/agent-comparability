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
**Ruleset-2（发行 tag 防改，保留新 tag 创建路径）**：
```json
{"name":"protect-release-tags","target":"branch","enforcement":"active",
 "conditions":{"ref_name":{"include":["refs/tags/v*"],"exclude":[]}},
 "rules":[{"type":"deletion"},{"type":"non_fast_forward"},
          {"type":"update"}]}
```
语义：include 只匹配已创建的 v* tag push 事件；创建新 tag（新建引用）不落入 update/deletion 规则——**新版本路径保持畅通**（依据 GitHub Rulesets 语义：这些规则作用于既有引用的更新/删除）。

**冲突/bypass/发布流程核查**：两 ruleset 条件集不相交（heads/tags）无冲突；均**不设 bypass**（维护者也无静默绕过通道；单人可合并性由 0-approval 参数而非 bypass 实现——不产生绕过通道）；启用后维护者发版流程 = 正常 push 新 tag（创建不受阻）→ CI 跑 tag → 全绿即发行；如需改错 tag 只能新建补丁版本（先例：v0.3.6→v0.3.7）。

**启用后四项验证计划（授权 A 后执行，全部使用临时引用、验证完即删，不动正式引用）**：
1. **失败 PR 无法合并**：从 main 拉 `verify/fail-pr` 分支，注入毒 import（先例 tmp/gate-proof），开 PR → CI 红 → 断言 merge API 返回 403（required status checks 未满足）。
2. **正常 PR 可合并**：`verify/pass-pr` 分支做无害文档改动，开 PR → CI 绿（conformance check success）→ 0-approval 下作者 merge 成功 → 断言 main 前进。
3. **已有 Tag 受保护**：对既有 tag（用 v0.3.6 做测试对象前先请示，或先打一个 `v9.9.9-verify` 牺牲tag）尝试 `git push --force` 与删除 → 断言两者均被拒（HTTP 403/规则拦截）→ 牺牲tag 若创建成功则保留为受保护状态（不删，避免"删除成功"污染验证语义；如所有者允许删除则删）。
4. **新版本 Tag 可创建**：push 一个新 tag `v0.0.0-verify-newtag` → 断言创建成功（规则只拦 update/delete）→ 请示后删除该验证 tag。
   *预算：全部为 GitHub-hosted 免费额度内 CI 分钟（每 run ~30s），无付费资源。*

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
| A | 写入上述两个 Rulesets（active） | 配置在案第二节，一条 API each |
| B | Topics 写入（建议 llm-agents/evaluation/specification/conformance-testing）+ About 核对 | 值已备 |
| C | 仓库转 Public | 安全审计全绿；建议先 A+B、并自行过目 2 个失败 run 链接 |
| D | GitHub Release（v0.5.0） | 依赖 C（或私有 Release 亦可，需明示） |
| E | PyPI（Trusted Publishing） | 包已 build+twine 校验；名称曾核实可用（发布日需重验） |

## 五、PUBLICATION_GATE 判定

**PASS_WITH_PENDING_AUTHORIZATIONS** —— 无任何阻断公开的技术或安全问题（全引用 blob 级审计 0 敏感/0 二进制、Artifacts 0、失败 run 无日志实体、元数据准确）；四项远程配置变更（A–D）与 PyPI（E）按第 4 节分离等待所有者逐项授权。本文档之后项目转入正常 Issue/PR 维护。
