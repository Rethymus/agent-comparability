# OPEN-ISSUES — 未解决 / 未核实 / 范围外

| # | 项 | 状态 | 说明 |
|---|---|---|---|
| O1 | GitHub 默认分支切换（release→main） | **BLOCKED-ON-OWNER** | 远程默认分支变更需所有者批准；命令已备好：`gh repo edit Rethymus/agent-comparability --default-branch main`。main 已推送且 CI 绿（run 40188394885），切换零技术风险 |
| O2 | 远程 master 分支处置 | DEFERRED | 含旧 dist 二进制的 2 独有提交；建议所有者确认无用后由其删除（我不删远程分支） |
| O3 | v0.4.1 tag 内 pyproject 版本为 0.4.0 | PARTIAL（已知余差） | tag 命名序列与包版本出现 1 位微差；不影响安装/一致性行为；下一版本对齐（0.5.0/`v0.5.0`）。诚实记录而非移动 tag |
| O4 | GitHub Topics / License 自动识别 | NOT_VERIFIED | 远程元数据变更与 GitHub 重扫待默认分支切换后一并处理 |
| O5 | 分支保护 / Rulesets | DEFERRED | 私有仓库计划能力未核实；建议公开前配置 main 保护（require PR+CI） |
| O6 | Linux 实机验证 | NOT_VERIFIED（间接证据） | CI 在 ubuntu-latest 绿（run 40188394885 即 Linux）即覆盖；本地仅 Windows。声明支持范围以 CI 环境为准 |
| O7 | Node20 弃用警告（actions pin 目标） | DEFERRED | 上游演进；Dependabot 已配置 github-actions ecosystem，月度更新路径在 |
| O8 | PyPI 发布 / 仓库公开 | 范围外 | 未授权；README 已按"从克隆安装"编写无假命令 |

**结论分级**：O1 是唯一 BLOCKED 项（一句话授权即解）；O3 为已记录余差；其余 DEFERRED/NOT_VERIFIED 均不阻断当前 v0.4.1 作为可维护开源候选。
