# 远程验收记录（rv-001，2026-10-25）

## 授权范围与执行
所有者授权：创建 Private 仓库 + 推送经审查分支与 tag + 首次计划内 CI。以下为实际执行记录，无范围外动作。

| 步骤 | 命令 | 结果 |
|---|---|---|
| 1. 创建仓库 | `gh repo create agent-comparability --private` | https://github.com/Rethymus/agent-comparability（API 确认 visibility=PRIVATE, isPrivate=true） |
| 2. 推送分支 | `git push origin release`（仅显式引用，无 --tags/--mirror） | ✓ 29476cf..257f1e6 |
| 3. 首次 tag 推送 | `git push origin v0.3.6` | ✓；远程 tag 对象解引用 commit = fa4f50bd7b28…（与本地快照一致） |
| 4. CI 首跑（v0.3.6） | push 触发 | **failure（0s）**——workflow 文件 YAML 语法错误（run: 内 python heredoc） |
| 修复 | heredoc → conformance/terminal_scan.py 共享门禁（自排除）；workflow 重写（固定 SHA、permissions、build/twine 步骤）；本地 YAML/scan/suite 三重验证 | commit 257f1e6 |
| 5. 新 tag | `git tag v0.3.7` + 推送（v0.3.6 未移动，保留为废弃候选） | ✓ 远程 commit = 257f1e618d88…（与本地一致） |
| 6. CI 复跑 | run 40169899908（v0.3.7）+ 40169898573（release） | **success**（conformance job 18s，7 步全绿：checkout/安装/终扫门禁/三指标套件/冒烟/build+twine） |

## CI 运行链接（私有，仅所有者可见）
- v0.3.7 tag run: https://github.com/Rethymus/agent-comparability/actions/runs/40169899908 （success）
- release branch run: https://github.com/Rethymus/agent-comparability/actions/runs/40169898573 （success）
- v0.3.6 首跑（失败，保留）: https://github.com/Rethymus/agent-comparability/actions/runs/40169769178

## 发行候选身份
- **当前候选：v0.3.7 = commit 257f1e618d88a94de5190885d4a94a93a6be3ae4**（远程=本地一致，CI success）
- 规范版本：cmp/0.3.1（不变）；v0.3.6 因 workflow 语法缺陷废弃（tag 未移动）
- 遗留警告（非阻断，记录在案）：CI 提示 actions 固定 SHA 目标 Node.js 20 已弃用（被强制跑在 24）；ubuntu-latest 即将迁移 26——属上游动作版本演进，后续维护时升级 pin

## 未做（授权边界外）
仓库公开化 / GitHub Release / PyPI / 购买服务 / 模型额度 / 移动任何旧 tag。
未来转公开前须单独审查远程 Actions 历史（GitHub 官方：转公开将公开日志）。
