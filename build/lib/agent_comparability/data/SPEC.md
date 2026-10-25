# Agent Evaluation Comparability Specification — cmp/0.3.1 (Release Candidate)

规范状态：候选规范（非行业标准、无第三方认证）。本文是判定语义的单一事实来源；参考实现（`scripts/cmp/core.py`）与一切第三方实现均以本文为准，冲突时以本文裁决。可脱离任何源码阅读。

---

## 0. 范围与目的

给定一组**评测运行记录**（Record）与一个**请求结论**（Requested Claim），本规范定义：该组记录在当前证据条件下**允许得出什么结论、不允许得出什么结论**。它不评分、不运行 Agent、不替代任何评测框架——它只裁决**可比性**。

**Record**（最小字段）：`task_id`、`model`、`harness`、`reward`（数值）、`reward_status`（`verified` / `unresolved_zero` / 其他）、可选 `trajectory_available`（bool）、可选 `score_scale`（`{range, unit, verifier}`）、可选 `repetition_count`（int ≥1）。

---

## 1. 证据信任层级（独立于比较判定）

每条 Record 的评分只能落在以下一层，层级**互斥且必须显式**，不得混用：

| 层 | 名称 | 含义 | 禁止 |
|---|---|---|---|
| L-claim | agent-claimed | Agent 自我声明 | 作为评分依据 |
| L-src | source-verifier-attested | 来源基准验证器给出 | 冒充本方独立验证 |
| L-ours | independently-verified | 本方对终态/答案亲自复验 | — |
| L-none | no-sufficient-evidence | trace 缺失/截断/引用不一致 | 计入任何成功率 |

**摘要（哈希）一致 = binding_verified，仅证明"未经同步修改"，不构成抗恶意篡改**（单写信任域）。该限制必须出现在每个 CDR 的 `limitations` 中。

---

## 2. Requested Claim 类型

| 类型 | 语义 |
|---|---|
| `causal` | 断言某变量（模型/Harness）**导致**了分数差异 |
| `score_comparison` | 请求对连续分数做（并排或汇总）比较 |
| `descriptive_registration` | 仅登记条件与分数，不作比较结论 |
| 其他 | **未支持类型** |

未支持类型 → `INCONCLUSIVE`，`unknown_conditions` 记录 `unrecognized_claim_type`。**实现不得猜测**相近类型。

---

## 3. Admissibility 分类与判定优先级

### 3.1 分类

| 分类 | 含义 |
|---|---|
| `ADMISSIBLE` | 所请求结论类型在当前条件下可得出 |
| `INADMISSIBLE` | 条件冲突，该结论类型**不可**得出（较弱结论可能仍可） |
| `PARTIAL` | 结论可得出但必须按拆分形式呈现（不得合并） |
| `INCONCLUSIVE` | 证据不足以判定（保留数据，不删来源评分） |

### 3.2 前置条件检查（按此顺序求值并记入 CDR）

1. `same_task_id` —— 全部 Record 同任务
2. `same_model` —— 全部同模型
3. `single_variable_isolation` —— **不得同时变化两个及以上比较变量**（模型与 Harness 同时不同即违反）
4. `trace_available` —— 无 `trajectory_available=false`
5. `zero_semantics_uniform` —— `verified` 的 0 分与 `unresolved_zero` 的 0 分**语义不同**，混组即违反
6. `score_scale_consistent` —— 全部 Record 声明同一 `{range, unit, verifier}`。**隐式默认规则（0.3.1 勘误补充）**：当组内全部 `reward ∈ [0,1]` 且未声明 `score_scale` 时，视为声明默认尺度 `{range:"0..1", unit:"fraction", verifier:"source"}`；任一值越界（如 0..100 百分制）或显式声明互不一致即违反。缺省与显式混用亦违反。
7. `causal_evidence_available` —— `repetition_count ≥ 1` 的重复实验存在于每个比较单元

### 3.3 判定表（规范核心）

**`causal`**：无条件 `INADMISSIBLE`，除非 3.2-7 满足（重复实验存在）；满足时仍须在 `supported_claims` 中**降级表述**为描述性结论。禁止单次运行支持因果。

**`score_comparison`**（按优先级，先命中先裁决）：
1. 违反 `trace_available` → `INCONCLUSIVE`（来源评分转录保留于 `unknown_conditions`，禁止删除）
2. 违反 `single_variable_isolation` **或** `same_task_id` 或 `same_model` → `INADMISSIBLE`
3. 违反 `score_scale_consistent` → `INADMISSIBLE`
4. 违反 `zero_semantics_uniform` → `PARTIAL`（支持按 verified/unresolved 分列的率；禁止合并 fail 率）
5. 其余 → `ADMISSIBLE`（同尺度连续分数并排）

**`descriptive_registration`**：无条件 `ADMISSIBLE`（登记一切条件与连续分数原值）。

优先级说明：证据缺失（INCONCLUSIVE）先于条件冲突（INADMISSIBLE）裁决，因为前者连"冲突"都无从判定；冲突先于语义拆分（PARTIAL），因为混变量组连拆分比较也不支持。

---

## 4. 变量变化对比较的影响

| 变化 | score_comparison | descriptive_registration |
|---|---|---|
| 仅 Harness 不同（同任务同模型） | ADMISSIBLE（并排） | ADMISSIBLE |
| 仅模型不同（同任务同 Harness） | ADMISSIBLE（并排） | ADMISSIBLE |
| 模型与 Harness 同时不同 | INADMISSIBLE | ADMISSIBLE |
| 任务不同 | INADMISSIBLE | ADMISSIBLE |
| 评分尺度/验证器不同 | INADMISSIBLE | ADMISSIBLE（附尺度差异说明） |
| reward_status 语义混同 | PARTIAL（分列） | ADMISSIBLE |

---

## 5. 未知字段、未支持 Claim 与版本规则

- **未知字段**：Record 中规范未定义的字段**必须忽略**（不得报错、不得猜测），并在 `unknown_conditions` 记 `ignored_fields:[...]`。
- **未支持 Claim**：见 §2 —— INCONCLUSIVE + `unrecognized_claim_type`，禁止近似匹配。
- **Policy 版本**：CDR 必须携带 `policy_version`。消费方遇到 `policy_version` 不认识时**必须丢弃该 CDR 并重新判定**，不得部分信任。本规范为 `cmp/0.3.1`（0.3 的澄清版：仅补隐式默认尺度规则，判定表未变）。
- **规范不兼容变更**：升 minor（0.3→0.4）可新增判定分支；改判定表必须升 major 并迁移案例。

---

## 6. CDR（Comparison Decision Record）最小字段

`case_id`、`requested_claim`、`comparison_scope`、`admissibility`、`satisfied_conditions[]`、`violated_conditions[]`、`unknown_conditions[]`、`supported_claims[]`、`unsupported_claims[]`、`evidence_refs[]`、`policy_version`、`limitations[]`（必须含 §1 防篡改声明）。机器可验证 Schema：`release/cdr.schema.json`。

---

## 7. Conformance 分层（三个独立指标，禁止合并）

1. **集成一致性**（integration）：同一参考实现经不同框架（Inspect/Pydantic）调用，输出逐字段一致。
2. **规范一致性**（spec conformance）：独立实现（仅依本文、未读参考源码）对冻结案例的判定与冻结预期一致。
3. **策略正确性**（policy correctness）：参考实现对冻结案例的判定与冻结预期一致。

三者的失败含义不同：1=适配缺陷；2=规范有歧义或实现误读；3=参考实现缺陷。任何"9/9"只属于其所属层。
