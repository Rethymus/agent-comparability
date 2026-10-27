# 真实对照实验 001（#22）— 结果记录 / Experiment Record

运行方式（可复现）：`python -m pytest tests/test_scenarios_001.py -v`（内部实际运行
`experiments.scenarios_001.run.run_all()`：生成真实 Inspect 日志 → #20 转换器 → #16 CLI →
核心裁决 → independent_impl 交叉验证）。

**数据来源与使用许可（全局，适用于全部四场景）**：
- 真实 Inspect EvalLog：实验内实际运行 `inspect_ai.eval`（`mockllm/model`，零 API 调用）产生；
  是真实日志工件，但**模型输出为 mock 性质，不代表任何真实 Agent 基准表现**。
  本轮实例：`logs/2026-10-27T10-55-23-…task_FHomRKQn3kKNtZLCHQDSZA.eval`，
  sha256 `d841ed7e…b6a866`（每次运行重新生成，摘要随内容变化——以运行输出为准）。
- `harness=manual-json` 的对照记录：**synthetic**（人工编写），不冒充任何 harness 实测；
  其 `model` 字段取值仅为构造 SPEC §4 场景条件。
- 全部输入由本仓库工具链（Apache-2.0）本地产生，无第三方数据许可问题。

**预期独立依据（全局）**：SPEC §3.3 判定表与 §4 变量表（冻结规范文本）；
并由 `conformance/independent_impl.py`（仅依规范、未读参考源码的独立实现）交叉验证。

---

## S1 同任务同模型不同 Harness → **ADMISSIBLE**（两实现一致）

1. 数据来源及许可：见全局（真实日志转换记录 + synthetic manual-json 记录）。
2. 原始记录定位：真实日志样本 1（经 #20 转换，`--task-label exp001 --status verified
   --score-map C=1.0,I=0.0`）；synthetic 记录文件 `authored-s1.json`。
3. 字段映射：`task_id=exp001#1`（转换器逐样本粒度，人工记录显式对齐）；
   `harness=inspect-ai / manual-json`（各自真实来源）；`model=mockllm/model`（原样透传）；
   `reward=0.0 / 1.0`（exact 打分 I→显式映射 / 人工赋值）；`reward_status=verified`（操作者断言）。
4. 实际请求的比较主张：`score_comparison`。
5. 预期结果的独立依据：SPEC §4 行 1（仅 Harness 不同 → ADMISSIBLE 并排）。
6. 实际 CDR：`ADMISSIBLE`；satisfied=`same_task_id, same_model, single_variable_isolation,
   continuous_score_preserved(0..1 默认尺度)`；supported=`continuous_score_side_by_side(同尺度)`；violated=∅。
7. 差异原因：无（与预期一致）。
8. 尚未验证的假设：manual-json 记录的 1.0 分无独立验证（manifest 态=artifact_observed，
   非 independently_verified）；mock 模型分数无基准含义。

## S2 同任务不同模型不同 Harness → **INADMISSIBLE**（两实现一致）※核心考察：正确拒绝

1. 数据来源及许可：同 S1（真实记录 + synthetic 记录，model=manual-model-b）。
2. 原始记录定位：同 S1 真实日志样本 1（`--task-label exp002`）；`authored-s2.json`。
3. 字段映射：同 S1，差异仅 `model`（mockllm/model vs manual-model-b）与 harness 同时不同。
4. 实际请求的比较主张：`score_comparison`（另验 `causal`）。
5. 预期结果的独立依据：SPEC §3.2-3（单变量隔离）与 §4 行 3（模型+Harness 同时不同 →
   INADMISSIBLE）；§3.3 causal 无重复实验一律 INADMISSIBLE。
6. 实际 CDR：`INADMISSIBLE`；violated=`same_model, single_variable_isolation`；
   unsupported=`score_comparison(任务/模型/尺度条件冲突)`。附带验证：`causal` 亦
   `INADMISSIBLE` 且 single_variable 违规在案。
7. 差异原因：无（系统正确拒绝了混淆比较，未包装成可信结论）。
8. 尚未验证的假设：无新增（同 S1 全局假设）。

## S3 验证失败与未决零分混合 → **PARTIAL**（两实现一致）

1. 数据来源及许可：同一真实日志的两次转换（操作者 `--status verified` /
   `--status unresolved_zero` 断言——断言本身是实验设计，逐条留痕于 manifest 警告）。
2. 原始记录定位：同 S1 真实日志样本 1（`--task-label exp003` 两次）。
3. 字段映射：两条记录除 `reward_status` 外完全相同（同 task/model/harness/reward=0.0）。
4. 实际请求的比较主张：`score_comparison`。
5. 预期结果的独立依据：SPEC §3.2-5 与 §3.3-4（零语义混同 → PARTIAL，支持分列率、禁止合并）。
6. 实际 CDR：`PARTIAL`；violated=`zero_semantics_uniform(verified_zero != unresolved_zero)`；
   supported=`per_status_stratified_rate(verified_zero/unresolved_zero 分列)`；
   unsupported=`pooled_fail_rate(0 分语义混同)`。
7. 差异原因：无（系统正确降级为分列表述，未合并成单一率）。
8. 尚未验证的假设：verified/unresolved_zero 的语义区分完全来自操作者断言，来源日志本身
   不含验证层（`verification_tier_absent_in_source`）。

## S4 证据或轨迹缺失 → **INCONCLUSIVE**（两实现一致）※核心考察：正确保留而非裁决

1. 数据来源及许可：synthetic 记录（`trajectory_available=false`），经 #16 离线 CLI 裁决。
2. 原始记录定位：`s4-input.json`（实验临时目录；内容见运行输出 records 字段）。
3. 字段映射：`trajectory_available=false`（人工声明轨迹缺失——构造 SPEC §3.3-1 场景）。
4. 实际请求的比较主张：`score_comparison`。
5. 预期结果的独立依据：SPEC §3.3-1（违反 trace_available → INCONCLUSIVE，来源评分转录
   保留、禁止删除）；优先级说明：证据缺失先于冲突裁决。
6. 实际 CDR：`INCONCLUSIVE`；violated=`trace_available`；
   supported=`score_transcription(source_verifier_attested)`；
   unsupported=`success_rate(含证据缺失记录)`；unknown 含 `source_reward_retained_but_unverifiable_by_us`。
7. 差异原因：无（系统保留数据并明确"不可判定"，未把证据缺失折叠成失败或成功）。
8. 尚未验证的假设：无新增。

---

## 结论

四场景裁决与 SPEC 冻结判定表完全一致，`independent_impl` 与参考实现同判——**未发现规范歧义**
（若发现，按程序应另开 Issue 展示最小复现，本实验无需）。核心考察点达成：S2/S4 被正确拒绝/
保留，S3 正确降级分列；没有任何证据不足被包装成可信结论。

## 未解决的证据缺口（如实）

- 真实第三方 harness（非 Inspect、非人工编写）的对照数据为零——S1/S2 的"harness 差异"由
  `inspect-ai` vs `manual-json` 构成，是真实来源差异但非两个 Agent harness；
- 真实模型（非 mock）的评测日志为零；
- 上述缺口不阻塞本实验对判定语义的验证，但阻塞"真实 Agent 基准场景"的更强结论——
  如外部数据可用，需先提供来源与许可。
