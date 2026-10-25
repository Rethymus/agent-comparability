[English](README.md) | [简体中文](README.zh-CN.md)

# Agent Comparability — 实验性规范与一致性测试套件

**什么时候可以比较 AI Agent 的评测结果——它们又能支持什么结论？**

## 1. 项目概览

Agent Comparability 是一套与框架无关的**规范**（`spec/SPEC.md`）、冻结的**一致性测试套件**和极薄的**参考实现**，它裁决的是 Agent 评测记录的*可比性*——从不为分数本身评分。

## 2. 问题与动机

Agent 排名会随 Harness 反转；分数混同语义（*已验证的失败*与*未解出的零分*都显示 `0.0`）；轨迹缺失会悄然抬高成功率；两个变量同时变化却有人宣称因果关系。在比较结果之前，你需要机器可校验地知道**证据支持什么**。

## 3. 它做什么

- 针对一组评测记录裁决**请求结论**（如 `score_compare`、`causal`、`descriptive_registration`）
- 返回**比较决策记录（CDR）**：可采纳性（`ADMISSIBLE / INADMISSIBLE / PARTIAL / INCONCLUSIVE`）、满足/违反/未知条件、**允许的结论与禁止的结论**、证据引用、规范版本
- 强制证据信任分层（Agent 自报 / 来源验证器 / 独立复验）、评分尺度一致性（范围/单位/验证器）、零分语义拆分、未知字段与未知结论规则
- 内置冻结一致性套件，按三个分离指标运行

## 4. 它不做什么

- **不**运行 Agent、基准或模型；无网络、无凭据
- **不**为任何东西评分、**不**认证任何 Agent 的可靠性——套件通过是*规范*一致性，不是可靠性评级
- 不把三个指标合并成一个数字（见第 10 节）

## 5. 主要特性

- `adjudicate(records, requested_claim) -> CDR`——纯 Python、零依赖
- 优先级排序的判定表（证据缺失 > 条件混淆 > 语义分裂 > 可采纳）
- 机器可校验的 CDR JSON Schema（`spec/cdr.schema.json`）
- 冻结的 A/B 一致性案例集；B5 公开勘误先例受保护
- 可选的 Inspect AI 与 Pydantic Evals 适配器复用同一核心

## 6. 安装

从克隆安装（尚未发布 PyPI）：

```bash
git clone <本仓库> agent-comparability && cd agent-comparability
pip install -e .            # 核心，零依赖
pip install -e .[suite]     # + 一致性套件（pyyaml、jsonschema）
```

要求 Python ≥ 3.10。无需 Docker、无需模型密钥。

## 7. 快速开始

```python
from agent_comparability import adjudicate

cdr = adjudicate({"id": "demo", "records": [
    {"task_id": "t1", "harness": "h1", "model": "m1",
     "reward": 1.0, "reward_status": "verified"},
    {"task_id": "t1", "harness": "h2", "model": "m1",
     "reward": 0.0, "reward_status": "unresolved_zero"}]},
    "score_compare")
```

## 8. 输入/输出示例（真实输出）

上面的调用返回：

```
cdr.admissibility      -> PARTIAL
cdr.supported_claims   -> ['per_status_stratified_rate(verified_zero/unresolved_zero 分列)']
```

换成一个条件混淆的组：

```python
cdr = adjudicate({"id": "x", "records": [
    {"task_id": "a", "harness": "h1", "model": "m1", "reward": 1.0, "reward_status": "verified"},
    {"task_id": "b", "harness": "h2", "model": "m2", "reward": 0.0, "reward_status": "verified"}]},
    "score_compare")
```

```
cdr.admissibility       -> INADMISSIBLE
cdr.violated_conditions -> ['same_task_id', 'same_model', 'single_variable_isolation']
```

`cdr.to_dict()` 输出完整 CDR（经 schema 校验）。

## 9. 架构

```
spec/SPEC.md                     ← 单一事实来源（可独立阅读）
spec/cdr.schema.json             ← 机器可校验的 CDR
src/agent_comparability/core.py  ← 极薄参考实现
src/agent_comparability/data/    ← SPEC + schema + 冻结案例（随包分发）
conformance/                     ← run_suite.py（三指标）+ independent_impl.py + 案例
adapters/                        ← 可选 inspect-ai / pydantic-evals 封装
tests/                           ← 冒烟 + 属性测试
```

## 10. 一致性套件

`python conformance/run_suite.py` 输出三个**分离**的指标，**绝不合并**：

1. **策略正确性**——参考实现 vs 冻结预期
2. **规范一致性**——仅依规范文本编写的独立实现
3. **集成一致性**——同一核心经 Inspect/Pydantic 适配器调用

每个指标的失败对应不同缺陷类别（实现 bug / 规范歧义或误读 / 适配器 bug）。

## 11. Inspect AI / Pydantic Evals 集成

```bash
pip install -e .[inspect] && python adapters/inspect_adapter.py
pip install -e .[pydantic] && python adapters/pydantic_adapter.py
```

两者封装*同一个*核心（语义零重复）。Inspect scorer 使用 `metrics=[]`——可采纳性**不**被聚合为准确率。

## 12. 规范与版本

三条独立版本线：软件 tag（如 `v0.4.0`）、规范 `cmp/0.3.1`（在 SPEC 内）、`agent_comparability.__version__`。判定表变更须规范升 major（SPEC §5）。完整 tag 谱系见 CHANGELOG（v0.3.1–v0.3.6 为保留不动的废弃候选）。

## 13. 局限

- 实验性规范；自测一致性，**无外部认证**
- 单写信任域：摘要一致仅证明未分叉，不证明抗篡改（SPEC §1）
- 判定内部不含重复次数/成本建模（由调用方处理）
- 中英文文档保持信息等价；翻译漂移由 CI 链接检查跟踪

## 14. 参与贡献

见 [CONTRIBUTING.md](CONTRIBUTING.md)。关键规则：**绝不为了让测试通过而修改冻结预期**；勘误遵循 B5 公开先例。PR 必须分别通过三个一致性指标。

## 15. 安全

见 [SECURITY.md](SECURITY.md)。优先使用私有漏洞报告渠道。

## 16. 许可与致谢

Apache-2.0（见 [LICENSE](LICENSE)、[NOTICE](NOTICE)）。可选集成 inspect-ai / pydantic-evals 为 MIT 且**不随包分发**。一致性案例数据为本项目原创；不分发任何 CC BY-NC 数据。研究脉络：本仓库从私有研究仓库蒸馏而来；内部过程记录在 `docs/internal/`。
