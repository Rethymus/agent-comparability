# Positioning — 与相关工作的关系 / Relation to prior work

> **English summary below the Chinese section.** 所有文献断言均经 arXiv 官方 API 核实（2026-10-27），仅引用摘要中可验证的内容；本文不做任何未核实的生态判断。

## 中文

### 三条线，一个正交关系

**线 1：基准构建严谨性（benchmark construction rigor）**
[Establishing Best Practices for Building Rigorous Agentic Benchmarks（arXiv:2507.02825，2025-07）](https://arxiv.org/abs/2507.02825) 提出 ARB 清单，指出大量 agentic 基准在任务设置或奖励设计上有缺陷——例如 SWE-bench Verified 测试用例不足、**TAU-bench 把空响应计为成功**。这条线解决的是"**把单个基准做对**"。

**线 2：轨迹缺陷检测（transcript flaw detection）**
[Automated Transcript Analysis for Detecting Flaws in Agentic Benchmarks（arXiv:2607.27518，2026-07）](https://arxiv.org/abs/2607.27518) 用自动化扫描器检测轨迹中的四类有效性问题（ground truth 访问、工具失败、猜测漏洞等）。这条线解决的是"**发现某次运行内部的无效性**"。

**线 3（本项目）：跨记录比较主张的裁决（cross-record claim adjudication）**
Agent Comparability 不构建基准、不检测轨迹缺陷；它回答的是**下一层问题**：给定若干条评测记录（无论各自多么严谨），某个比较主张（"A 比 B 好""分数差异由模型导致"）是否被这些证据支持。两个直接对应关系（引用自上述已核实摘要，非本文新断言）：

- TAU-bench"空响应计成功"类缺陷 → 正是 cmp `reward_status` 语义区分（`verified` 0 分 ≠ `unresolved_zero` 0 分）与 `zero_semantics_uniform` 条件的动机——**混同即降级（PARTIAL）或拒绝**；
- "AI Agents That Matter"（[arXiv:2407.01502，2024-07](https://arxiv.org/abs/2407.01502)）指出社区"对精度增益来源得出过错误结论"→ 正是 `single_variable_isolation`（混淆变量拒绝）与 `causal` 主张一律要求重复证据的存在理由。

### 关系总结

| 维度 | 线 1（ARB 清单） | 线 2（轨迹扫描） | 本项目（cmp） |
|---|---|---|---|
| 作用对象 | 基准的构建 | 单条运行轨迹 | 记录**之间**的比较主张 |
| 时机 | 基准发布前 | 运行后审计 | 任何比较结论发布前 |
| 输出 | 清单/修复建议 | 缺陷标记 | 结构化 CDR（可采纳性裁决 + 支持范围 + 证据清单） |

互补而非竞争：经过线 1/2 加固的记录输入 cmp 会得到更明确的可采纳性；未经加固的记录在 cmp 下通常得到 INCONCLUSIVE/PARTIAL——**宁可保留证据也不包装结论**。

## English

Two ecosystem lines are grounded below (abstracts verified via the official arXiv API on 2026-10-27; no unverified claims):

1. **Benchmark construction rigor** — [Establishing Best Practices for Building Rigorous Agentic Benchmarks (arXiv:2507.02825, 2025-07)](https://arxiv.org/abs/2507.02825): the ARB checklist documents task-setup and reward-design flaws in agentic benchmarks (e.g., SWE-bench Verified's insufficient test cases; TAU-bench counting empty responses as success). This line makes *individual benchmarks* valid.
2. **Transcript flaw detection** — [Automated Transcript Analysis for Detecting Flaws in Agentic Benchmarks (arXiv:2607.27518, 2026-07)](https://arxiv.org/abs/2607.27518): automated scanners for in-transcript validity issues (ground-truth access, tool failure, guessing vulnerabilities). This line finds *invalidity inside individual runs*.

**Agent Comparability occupies the orthogonal layer**: given evaluation records of whatever rigor, it adjudicates whether a *comparison claim* ("A beats B", "the model caused the difference") is supported by that evidence. Two direct correspondences grounded in the verified abstracts: TAU-bench's empty-response-as-success flaw is exactly what cmp's `reward_status` semantics (`verified` zero ≠ `unresolved_zero` zero, mixing → PARTIAL) is designed to expose; and "AI Agents That Matter" ([arXiv:2407.01502, 2024-07](https://arxiv.org/abs/2407.01502)) reporting that the community "has reached mistaken conclusions about the sources of accuracy gains" is the motivating case for `single_variable_isolation` (confounded comparisons refused) and for requiring repetition evidence before any `causal` claim.

Complementary, not competing: records hardened by lines 1–2 yield clearer admissibility under cmp; unhardened records typically yield INCONCLUSIVE/PARTIAL — evidence is preserved rather than packaged into conclusions.
