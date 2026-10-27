# OPEN-ISSUES — 未解决 / 未核实 / 范围外（2026-10-27 刷新）

> 本文件随维护节奏刷新；历史版本见 git 历史（本文件原位于仓库根目录，v0.4.1 时代的
> 原表保存在历史提交中）。O9 披露条目为永久留痕，不随状态变化删除。

| # | 项 | 状态（刷新后） | 说明 |
|---|---|---|---|
| O1 | GitHub 默认分支切换 | **FIXED** | default = main，已核实 |
| O2 | 远程 master 分支处置 | **RESOLVED（MOOT）** | 远端从未长期存在 master；当前远端仅 main。本地 master 保留为发布前旧谱系（被 v0.3.x tag 锚定），不删 |
| O3 | v0.4.1 tag 内 pyproject 版本为 0.4.0 | **DOCUMENTED RESIDUAL** | 历史 tag 不可移动，微差已记录于 CHANGELOG；后续版本线已对齐（v0.5.0/v0.5.1/v0.5.2 均一致） |
| O4 | GitHub Topics / License 自动识别 | **FIXED** | topics×5 + Apache-2.0 识别均已生效 |
| O5 | 分支保护 / Rulesets | **FIXED** | protect-main（PR+必需检查）与 protect-release-tags 生效中 |
| O6 | Linux 实机验证 | **COVERED（CI）** | ubuntu-latest 每次推送验证；支持范围声明以 CI 环境为准 |
| O7 | Node20 弃用警告 / actions pin 演进 | **TRACKED** | dependabot（github-actions ecosystem）在位，被动跟进 |
| O8 | PyPI 发布 / 仓库公开 | **DONE** | 0.5.2 已上线（Trusted Publishing），仓库公开，README PyPI 主入口 + 徽章 |
| O9 | **披露：v0.4.0 远程 tag 删除事件** | **DISCLOSED-DEVIATION（永久留痕）** | 详情见历史版本（v0.4.1 时代表）；此后所有远程引用变更均先取明示授权，该纪律持续有效 |

## 当前真实待决项（2026-10-27）

| 项 | 状态 | 门控 |
|---|---|---|
| 0.5.3 版本化 | **DONE（2026-10-27）** | 已发行（CLI/manifest/converter/experiment/urls/多日志/歧义报告/定位文档全部随行） |
| 规范歧义 #27（§3.3-2 vs §4 行 2） | **方向 B 已实现（PR #33，cmp/0.4.0 随 v0.5.4 发行）；Issue 保持开放待所有者明确确认** | 可回滚（git revert）；若改选 A 按备忘录 2 小时方案执行 |
| 第二真实来源（pydantic-evals 真实报告转换） | 暂停 | 触发条件：真实数据或用户需求 |
| 真实第三方 harness 数据试点 | 暂停 | 触发条件：合法许可数据 |
| 外部展示（HN/Reddit/X 等） | 未启动 | **属所有者动作**（草稿可代拟） |

**结论分级**：无 BLOCKED 项；一项待所有者裁决（#27）；其余暂停项均有明确触发条件。
