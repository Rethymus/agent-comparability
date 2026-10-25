# 远程推送计划（待所有者授权后一次执行）

## 授权范围（按第二十一轮评审第五节，逐条执行、不做范围外动作）

```bash
# 1. 创建 Private 仓库（不公开）
gh repo create agent-comparability --private --source . --push=false
# 2. 只推显式引用（绝不 --tags / --mirror / 强推）
git remote add origin https://github.com/Rethymus/agent-comparability.git
git push origin release        # 经全历史扫描的分支（9 commits）
git push origin v0.3.6         # 显式单个 tag（fa4f50bd7b28…）
# 3. 核对远程 SHA == 本地快照
gh api repos/Rethymus/agent-comparability/git/ref/tags/v0.3.6
# 4. CI 自动触发（push 事件）；轮询首跑结论
gh run list --limit 1
# 5. 保存 run URL + 结论 + 发行候选身份到 REMOTE-VERIFICATION.md
```

## 范围外（明示不做）
公开仓库 / GitHub Release / PyPI / 购买服务 / 模型额度 / 移动旧 tag / 推送 master
（master 带旧 dist 二进制，已排除）。

## 推送前已完成的核验
- release 分支 9 commits 可达历史全扫：敏感命中 0，二进制/数据 blob 0
- v0.3.6 = fa4f50bd…（祖先于 release HEAD b747bb6，tag 快照即验证过的发行版）
- 定位冻结 + CI 最小权限 + actions 固定 SHA（b747bb6）
- gh 已认证（Rethymus）——本计划文件落盘即停，未创建任何远程

## 失败处置
CI 失败 → 修复 → 新 tag v0.3.7 → 重新走快照验证；不移动 v0.3.6。
