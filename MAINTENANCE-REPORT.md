# 维护报告 — Post-Hardening Stabilization（2026-10-25）

## 1. 当前 main Commit 与 CI 结果

- main = `fb2e06f`（Merge fix/v050-version-consistency）；tag **v0.5.0** = 同一提交（`release_gate.py 0.5.0` 实测 OK）
- CI：run **40189960184 success**（22s，10 步含新增 release 版本一致性门禁 + N1–N4 回归测试）
- 毒分支验证：tmp/gate-proof（注入 `from arlib import`）CI **failure**——失败检查确认可阻断，临时分支已清理

## 2. 已修复的真实问题

| 问题 | 处置 |
|---|---|
| v0.4.1 tag 内包版本为 0.4.0（历史发行候选缺陷，已记录） | **v0.5.0 发行**：tag==pyproject==`__version__`==包元数据全对齐；`conformance/release_gate.py` 入 CI，任何不一致即红 |
| 负向门禁仅为一次性验证 | N1–N4 转为**永久回归测试**（tests/test_gate_regressions.py，5 测试含断言完整性自检）；原始失败记录保留于 VALIDATION.md 与修复 commit ad14fb5/541494d |
| 终扫依赖字符串匹配 | 新增 **AST 结构化检查**（N1b：解析真实 import 语句扫 src/），未扩张字符串规则；自引用排除已文档化 |

## 3. 尚需所有者授权的操作

1. **Branch Protection / Rulesets**（当前 main 无保护，API 404 证实）。最小规则提案：
   - main：Block force push + Block deletion；Require PR，Required check = `ci/conformance`（建议另勾 Require approvals=1）；**不启用** Include administrators 之外的特殊豁免
   - 发行 tag（v*）：Code scramming→建议用 Rulesets 的 tag-create/read-only 规则（若套餐支持；free 私有仓 Rulesets 可用性需所有者账户页确认）
   - 影响：维护者此后须经 PR+CI 合并（正是防"无记录绕过"）；实施仅一条 API/页面操作
2. Topics 设置（建议：`llm-agents`/`evaluation`/`specification`/`conformance-testing`）与 About 微调——远程元数据写入需授权
3. 远程 `release` 分支处置：已确认 **release 是 main 的完全祖先（0 独有提交）、无未合并 PR、无工作流/文档引用**——建议**删除**（历史全部保留于 main 与 tags），等你一句话；本地 master（含 dist 二进制的 2 提交）建议直接丢弃本地引用，同样待确认

## 4. 下一次发行的版本一致性状态

**READY**：v0.5.0 已实现四处一致并被 CI 门禁强制；后续任何发行若不一致将在 CI 红灯（release_gate 步骤）。规范版本 cmp/0.3.1 独立维护不变。

## 5. 能否安全申请公开发布的结论

**技术上 READY，发布动作待授权**：
- PRIVATE 确认；远程仅 main+release 两分支、5 个 tag（v0.3.6/7、v0.4.1、v0.5.0 + 各 tag 对象），谱系干净
- main 可达 21 commits blob 级扫描：敏感 0、二进制/NC 数据 0
- 历史 Actions 12 次 run = 10 success + 2 failure（两次失败均已披露：v0.3.6 workflow 语法错误 + 本次毒分支验证——日志无敏感内容，但按 GitHub 官方提示**转公开将公开日志**，建议你批阅 2 个失败 run 链接后再公开）
- 双语 README 在 main 最终提交校验 OK；About 描述准确；Topics 空（建议发布前设置）
- 未发布 GitHub Release / PyPI；无凭据；Apache-2.0+NOTICE 完整

**建议发布顺序**：授权 Branch Protection → Topics → 删除远程 release（可选）→ 批阅 2 个失败 run → 变更可见性 public → （可选）GitHub Release v0.5.0 → PyPI（Trusted Publishing）。
