# VALIDATION — v0.4.1（验收 SHA 541494d81a60d9af955e678f9760b94632bf9fb8）

全部验证从固定 SHA 的全新克隆执行，非工作区。逐条对应目标第九节 11 项 + 负向门禁。

| # | 验证 | 命令/环境 | 退出码 | 结果 |
|---|---|---|---|---|
| 1 | 固定 SHA | `git rev-parse HEAD` | 0 | 541494d8… |
| 2 | 全新工作区 | `git clone . /tmp/final-verify && git checkout $SHA` | 0 | ✓ |
| 3 | 安装依赖 | venv `pip install -e .[suite] pytest` | 0 | ✓ |
| 4 | README 首案例 | 按 README §7 原样执行 | 0 | `PARTIAL / ['per_status_stratified_rate(verified_zero/unresolved_zero 分列)']` 与文档逐字一致 |
| 5 | 完整 Conformance | `python conformance/run_suite.py` | **0** | 22/22 ×3 + schema failures 0（inspect/pydantic 装入后 metric1 22/22；未装时 null=预期降级） |
| 6 | 独立实现+双框架 | `pytest tests/`（含 200 属性测试）；两个 adapters | 0 | 201 passed；inspect route1 true / pydantic all_consistent true |
| 7 | Wheel/Sdist 资源 | `python -m build` + `twine check` + 内容断言 | 0 | 双 PASSED；wheel/sdist 各含 LICENSE/NOTICE/SPEC/schema/B 集/A 集（零缺失） |
| 8 | 双语文档链接 | `python conformance/check_docs.py` | 0 | 16 节×2 等价、互链在位、无假 pip 命令 |
| 9 | main CI 实际触发 | push 541494d → run 40188394885 | — | **success**（21s，9 步全绿含双门禁）https://github.com/Rethymus/agent-comparability/actions/runs/40188394885 |
| 10 | 默认分支/Tag/版本映射 | `gh repo view` + tag 遍历 | 0 | 默认分支=release（**待所有者批准切 main**）；v0.4.1=541494d8；包 0.4.0（见 OPEN-ISSUES O3）；spec cmp/0.3.1 |
| 11 | 历史安全边界 | main 可达 16 commits blob 级扫描 | 0 | 敏感 0、二进制/NC 0 |

## 负向门禁测试（隔离 clone /tmp/neg4，正式分支零污染）

| 用例 | 注入 | 门禁 | 退出码 | 结论 |
|---|---|---|---|---|
| N1 | 核心尾部追加 `from cmp.core import x` | terminal_scan | **1** | 阻断 ✓ |
| N2 | 篡改 B3 冻结预期为 ADMISSIBLE | run_suite 退出码 | **1** | 阻断 ✓ |
| N3 | README 断链注入 | check_docs | **1** | 阻断 ✓ |
| N4 | 中文 README 假 pip 命令 | check_docs | **1** | 阻断 ✓ |

**N1/N2 首轮未触发并由此发现两个真实门禁缺陷**（终扫模式带空格漏 `from cmp.core`；run_suite 恒 return 0——CI 曾对判定失败恒绿），均已修复并在 v0.4.1 重验阻断。此为负向测试的直接战果：四个门禁现在全部实证有效。
