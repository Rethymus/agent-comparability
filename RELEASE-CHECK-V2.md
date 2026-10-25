# 发布前最终快照核验（rf-002，应第二十轮验收）

## 一、v0.3.1 Tag 核查（评审指定命令实际执行）

```
HEAD            = 9b657a3 (当时) → 现 fa4f50b
v0.3.1^{commit} = 1116139
v0.3.1:LICENSE  = EXISTS ✓   v0.3.1:NOTICE = EXISTS ✓
git status      = clean
```
**结论**：v0.3.1 未指向 LICENSE 缺失提交，但指向**套件不可运行**的快照（缺路径自包含修复，`arlib`/`cmp.core` 导入失败）。按纪律**未移动任何 tag**；v0.3.1 保留为废弃候选。

## 二、tag 谱系（每次废弃均有据）

| tag | 废弃原因（快照验证实证） |
|---|---|
| v0.3.1 | LICENSE 在但套件导入研究仓依赖 → 不可运行 |
| v0.3.2 | pyproject 版本对齐了，但替换无断言 → 静默未生效，快照仍含 cmp.core |
| v0.3.3 | 套件通过但 adapters 仍含研究路径（LOC 统计行） |
| v0.3.4 | 适配器修复改用容错替换，run_suite 注释级残留触发终扫断言 |
| v0.3.5 | **评审预言成真**：包可导入但 wheel/sdist 缺 SPEC/schema/案例 6 项核心资产；pyproject 版本脱节 |
| **v0.3.6** | **当前候选**：资产入包数据、版本对齐、全链验证 |

## 三、v0.3.6 验证链（全部从 tag 快照或安装包执行，非工作区）

- 快照 clone + checkout v0.3.6：三指标 22/22×3 + schema failures 0；inspect route1 true；pydantic all_consistent true
- `python -m build` sdist+wheel → `twine check` 双 PASSED
- 包内容核查：wheel 13 files / sdist 25 files，LICENSE/NOTICE/SPEC/schema/B 集/A 集冻结 **零缺失**
- 双 venv：sdist 装机判定 OK（4 数据资产可读）；wheel 装机判定 OK + `importlib.resources` 实读 SPEC 4213 字节/B 集 8 案例/schema
- 终扫（自包含硬门禁）green；NOTICE 已按 Apache 非捆绑指引修正（无可选依赖入 NOTICE）
- CI 工作流就位（checkout→安装→终扫门禁→三指标套件→冒烟），全新 ubuntu 环境

## 四、四状态

1. **技术验收：PASS**（tag 谱系核验 + 快照级全链验证）
2. **许可与发行安全：PASS**（Apache-2.0 全文/NOTICE 修正/双包资产核查/NC 零携带；GitHub 名称 0 精确占用；PyPI 现刻可用，发布日重验）
3. **规范稳定性：STABLE cmp/0.3.1**（六个发行候选期间规范零变更——22 对冻结案例即锚）
4. **公开发布授权：PENDING_OWNER**——采用评审建议的限定授权话术，等你一句话：

> 授权创建 GitHub 私有仓库 agent-comparability，推送 v0.3.6；暂不公开、暂不发 PyPI，后续公开再批准。

## 五、停止无限验收

本轮已把"声明完成"替换为可执行门禁（终扫断言/快照验证/包内容核查/CI 全新环境）。v0.3.1–v0.3.5 五次废弃即该机制有效性的证据。后续按开源维护节奏（PR/CI/issue），不再产出研究报告。
