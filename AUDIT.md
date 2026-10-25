# AUDIT — Rethymus/agent-comparability（2026-10-25，基于实际命令输出）

标注：CONFIRMED=实际命令证实；SUSPECTED=有迹象待验；NOT_APPLICABLE=不适用；NOT_VERIFIED=本轮无法核实。

## A. 仓库与分支

| # | 发现 | 状态 | 证据 |
|---|---|---|---|
| A1 | 仓库 Private（isPrivate=true, visibility=PRIVATE） | CONFIRMED | `gh repo view --json` |
| A2 | Default Branch = `release`（承担主干职责，不符合目标协作模型） | CONFIRMED | 同上 `defaultBranchRef.name` |
| A3 | 远程含 `release` 分支与 v0.3.6/v0.3.7 tag；本地另有分叉 `master`（独有 2 commits，含旧 dist 二进制 blob `dist/…0.3.1.tar.gz`）——**历史污染源，禁止合并** | CONFIRMED | `git rev-list release..master --count`=2；`git log --all -- dist/*` |
| A4 | 本地 `master`、`release` 两分支；`main` 不存在 | CONFIRMED | `git branch -vv` |
| A5 | tag v0.3.1–v0.3.7 谱系连续，v0.3.7=`257f1e61`（CI 绿） | CONFIRMED | tag 遍历 + rv-001 |

## B. 文件树与历史包袱

| # | 发现 | 状态 | 证据 |
|---|---|---|---|
| B1 | **`build/lib/…`（7 文件）与 `src/agent_comparability.egg-info/`（5 文件）构建产物被提交** | CONFIRMED | `git ls-tree -r release --name-only` |
| B2 | 报告/计划类文件混入发行面：REMOTE-PUSH-PLAN.md、RELEASE-CHECK-V2.md、REMOTE-VERIFICATION.md、PROVENANCE.json（对外开发者无意义且含过程细节） | CONFIRMED | 同上 |
| B3 | QUICKSTART.md 与 README 内容重复（漂移风险） | CONFIRMED | 两文件对比 |
| B4 | README.md 含"rf-002/版本对齐"等过程叙述 + 定位冻结块，但缺 16 节结构、缺中文版、Quickstart `pip install -e .` 指向本地（未发 PyPI 时正确）但无 from-source 安装完整说明 | CONFIRMED | 文件读取 |

## C. 治理与社区

| # | 发现 | 状态 | 证据 |
|---|---|---|---|
| C1 | 缺：README.zh-CN.md、CHANGELOG.md、PR 模板、Issue 模板、支持版本政策、Dependabot 配置 | CONFIRMED | `ls` 输出 |
| C2 | CONTRIBUTING.md / SECURITY.md 存在但内容指向研究仓路径习惯（如 boundary-cases.json 相对路径已对，但无双语/模板链接） | CONFIRMED | 文件读取 |
| C3 | GitHub About description 正确；Topics 未设置；License 识别未验证（API licenseInfo 字段空返回） | CONFIRMED / NOT_VERIFIED | `gh repo view` |

## D. 代码/规范/测试一致性

| # | 发现 | 状态 | 证据 |
|---|---|---|---|
| D1 | 三指标 22/22×3 + schema 22/22 在 v0.3.7 快照与 CI 双绿 | CONFIRMED | 本地快照 clone 运行 + run 40169899908 |
| D2 | README 首案例输出"ADMISSIBLE"与实际一致 | CONFIRMED | 干净 venv 实跑（第二十轮） |
| D3 | tests/ 仅 1 冒烟测试；conformance 套件承担主要回归——属性/变异测试缺位（本轮补少量高价值项） | CONFIRMED | `ls tests/` |
| D4 | B5 勘误与 A/B 集一致性此前已程序化四方交叉验证 | CONFIRMED | 第二十轮门禁1 记录 |
| D5 | CI：v0.3.7 workflow 有效且绿；但 trigger 为 `[push, pull_request]`（含 tag push 噪声）；YAML/包内容/文档链接校验缺位 | CONFIRMED | ci.yml 读取 |

## E. 打包

| # | 发现 | 状态 | 证据 |
|---|---|---|---|
| E1 | src layout + import 一致；wheel/sdist 含 data 资产（v0.3.6 修复）；`importlib.resources` 可读 | CONFIRMED | 第二十轮双 venv 实测 |
| E2 | **pyproject version=0.3.6 而 tag 已 v0.3.7**（v0.3.7 修复只改 workflow，未 bump 包版本）——包版本与 tag 脱节 | CONFIRMED | pyproject.toml 读取 vs tag |
| E3 | README 未写错误 pip 命令（`pip install -e .` 本地安装正确；无 `pip install agent-comparability` 字样） | CONFIRMED | README 读取 |

## F. 安全/许可

| # | 发现 | 状态 | 证据 |
|---|---|---|---|
| F1 | release 可达历史（至 v0.3.7 + rv-001）敏感扫描 0、二进制 0 | CONFIRMED | 第二十二轮 blob 级遍历 |
| F2 | Apache-2.0 LICENSE 全文 + NOTICE（非捆绑声明）；无 NC 数据入发行面 | CONFIRMED | 历轮审计 |
| F3 | CI permissions contents:read + actions 固定 SHA；Node20 弃用警告（上游演进，非缺陷） | CONFIRMED | run 40169899908 日志 |
| F4 | 分支保护/Rulesets 未配置 | NOT_VERIFIED（私有仓库计划能力未知） | — |
