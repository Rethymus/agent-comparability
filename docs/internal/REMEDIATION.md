# REMEDIATION — 整改前后、根因与取舍（对应 AUDIT.md 编号）

| 审计项 | 处置 | 状态 | 根因 / 取舍 |
|---|---|---|---|
| A2 默认分支=release | main 已建自已验证 release HEAD（无覆盖：main 此前不存在），CI/文档已切 main 触发；**GitHub 默认分支切换待所有者批准** | PARTIAL（本地 FIXED，远程 BLOCKED-on-owner） | 远程默认分支变更属授权边界 |
| A3 分叉 master（含 dist 二进制） | 未合并、未删除，保持隔离；发布历史确认在 release/main 线 | FIXED（保持隔离即处置） | 历史污染源，合并被禁止 |
| B1 build/egg-info 入库 | `git rm --cached` + .gitignore | FIXED | 构建产物曾被 `git add -A` 捕获——根因是无 .gitignore 条目 |
| B2 过程报告混入发行面 | 移入 docs/internal/（不删除） | FIXED | 保留研究可追溯性 vs 首页清晰，取归档 |
| B3/B4 QUICKSTART 重复/README 过程叙述 | 并入 README 16 节双语版；QUICKSTART 删除 | FIXED | 单一文档源防漂移 |
| C1 治理文件缺失 | CHANGELOG/PR 模板/Issue 模板×2/支持政策/Dependabot 全部新增 | FIXED | 按需最小集，未过度建设 |
| C3 Topics/License 识别 | Topics 未设（远程元数据变更待默认分支一并批准）；licenseInfo 待 GitHub 重扫 LICENSE | PARTIAL | 见 OPEN-ISSUES |
| D3 测试薄弱 | 200 个属性测试（4 不变式×50 种子）加入；**并抓到真实缺陷 E-新**：reward>1 无声明尺度时 `dict(None)` 崩溃——修复为尺度违规 | FIXED+VERIFIED | 高价值不变式优先，未灌数量 |
| D5 CI 触发/校验缺位 | trigger 改 main+PR；新增 docs 门禁、包内容门禁、pytest 步骤 | FIXED | — |
| **新发现：终扫模式缺陷** | `from cmp.core`（无空格）逃逸 `from cmp ` 模式 → 放宽为 `from cmp`/`import cmp` | FIXED（负向 N1 验证阻断） | 模式过窄；根因是首版抄了带空格写法 |
| **新发现：run_suite 恒 exit 0** | 退出码按三指标+schema 传导 | FIXED（负向 N2 验证阻断） | **严重**：CI 曾对判定失败恒绿——"虚假一致性"类缺陷的实例 |
| E2 包版本 0.3.6 vs tag v0.3.7 | 统一升 0.4.0→0.4.1（tag 序列）；__version__ 同步 | FIXED | 见 OPEN-ISSUES O3（0.4.1 tag 内包版本 0.4.0 的微小余差，诚实保留） |
| F4 分支保护/Rulesets | 未配置（需所有者批准+计划能力核实） | DEFERRED | — |

## 分支迁移记录

- `main` 新建自 release HEAD（经全历史扫描），非 rename（保留 release 原样直至远程切换获批，可回退）
- 本地 tracking：main→origin/main；CI trigger=main+PR；贡献文档已按 main/PR 模型编写
- 未发生：force push、tag -f（tag 序列全部新建）、--mirror、master 合并、历史改写
- **需所有者批准的远程动作**：① `gh repo edit --default-branch main`；② 可选：master 分支删除建议（含 dist 二进制，确认无用后删）；③ Topics 设置
