# 使用示例：六个真实用户旅程 / Usage Examples: Six Real User Journeys

> **English section below.** 覆盖四个 CLI 入口：`python -m agent_comparability`（离线 JSON，#16）、
> `python -m agent_comparability.inspect_log`（Inspect EvalLog 转换器，#20/#26）、
> `python -m agent_comparability.validate`（CDR 消费侧校验器）与
> `python -m agent_comparability doctor`（包环境自检）。本文只描述**可直接
> 复制的命令**与**预期裁决形态**（判定名、条件名、清单状态名），不展示具体 JSON 全文——以实际运行
> 输出为准。判定语义的单一来源是 [spec/SPEC.md](../spec/SPEC.md) §3.3。

## 中文

**产出侧两个 CLI 入口通用的退出码契约**（旅程 1–4；旅程 5 的消费侧校验器另有 0/1/2 三态
契约，旅程 6 的 doctor 另有 0/1 两态契约，各见该节）：

- **裁决 ≠ 程序失败**：`exit 0` 表示成功产出 CDR——`ADMISSIBLE / INADMISSIBLE / PARTIAL /
  INCONCLUSIVE` 四种裁决都是正常结果，脚本不应把非 ADMISSIBLE 当作崩溃处理；
- **`exit 2` = 输入/映射错误**（文件不可读、JSON 语法错误、契约字段缺失或类型错、缺
  `--status`、字母分数无映射等）：诊断精确到字段路径（如 `records[0].reward`），无效输入
  **绝不**被静默转换成貌似成功的裁决。

### 旅程 1：离线 JSON → CDR

```bash
python -m agent_comparability examples/demo-case.json --claim score_comparison
# 加 -o 写入文件而非 stdout：
python -m agent_comparability examples/demo-case.json --claim score_comparison -o cdr.json
```

`examples/demo-case.json` 是**合成/示意**样本（SYNTHETIC/illustrative）：两条记录同任务、同模型、
仅 harness 不同、均为 `verified`、reward 落在 [0,1] 且未声明 `score_scale`。

#### 四种裁决 × 可直接复制的命令

前提：先完成基础安装 `pip install -e .`（见 README §6——src 布局，未安装时
`python -m agent_comparability` 直接 ModuleNotFoundError），并在**仓库根目录**运行以下命令
（`examples/...` 为相对路径，在其他目录运行会得到 exit 2 的「无法读取输入文件」）。

四个示例文件都内嵌 `_comment`（SYNTHETIC/ILLUSTRATIVE + 预期裁决及一句「为何」）。以下每条
「为什么」均摘自实际运行输出的 CDR 字段（真实实跑后摘录，非虚构）：

**ADMISSIBLE（同尺度并排）**——`examples/demo-case.json`：

```bash
python -m agent_comparability examples/demo-case.json --claim score_comparison
```

为什么可并排：仅 harness 一个变量变化。`satisfied_conditions` 含 `same_task_id`、`same_model`、
`single_variable_isolation` 与默认尺度下的 `continuous_score_preserved(...)`；`supported_claims`
为 `continuous_score_side_by_side(同尺度)`；`violated_conditions` 与 `unsupported_claims` 均为空。

**INADMISSIBLE（混淆，拒绝比较）**——`examples/demo-inadmissible.json`：

```bash
python -m agent_comparability examples/demo-inadmissible.json --claim score_comparison
```

为什么拒绝：model 与 harness **同时**不同（两个变量纠缠，效应无法归因）。`violated_conditions`
含 `same_model` 与 `single_variable_isolation`；`unsupported_claims` 含
`score_comparison(任务/混淆/尺度条件冲突)`；`supported_claims` 为空（README §8 即此形态）。

**PARTIAL（零分语义混同，只许分列）**——`examples/demo-partial.json`：

```bash
python -m agent_comparability examples/demo-partial.json --claim score_comparison
```

为什么只算部分可用：`verified` 的 0 分与 `unresolved_zero` 的 0 分**语义不同**。
`violated_conditions` 含 `zero_semantics_uniform(verified_zero != unresolved_zero)`；
`supported_claims` 只支持按状态**分列**的 `per_status_stratified_rate(verified_zero/unresolved_zero 分列)`；
把两种 0 分合并成单一 fail 率被列入 `unsupported_claims`（`pooled_fail_rate(0 分语义混同)`）。

**INCONCLUSIVE（证据缺失，优先级最高）**——`examples/demo-inconclusive.json`：

```bash
python -m agent_comparability examples/demo-inconclusive.json --claim score_comparison
```

为什么无法下结论：记录声明 `trajectory_available=false`（未观察轨迹）。`violated_conditions` 含
`trace_available`——证据缺失在判定优先级中**高于**其他条件，直接主导裁决。源 reward 如实保留：
`unknown_conditions` 记 `source_reward_retained_but_unverifiable_by_us`，评分转写仍在
`supported_claims`（`score_transcription(source_verifier_attested)`），但成功率被列入
`unsupported_claims`（`success_rate(含证据缺失记录)`）。

未声明的 `--claim` 类型同样返回 `INCONCLUSIVE`（不猜测，`unknown_conditions` 记
`unrecognized_claim_type`）。

### 旅程 2：证据清单（Evidence Manifest）

```bash
python -m agent_comparability examples/demo-case.json --claim score_comparison \
    -o cdr.json --manifest cdr.manifest.json
```

清单三态（**证据制品级**，与 SPEC §1 的记录级信任分层是不同维度：不进入 `adjudicate()`、
不改变任何 CDR 字段或判定结果）：

| 状态 | 含义（唯一触发途径） |
|---|---|
| `source_claimed` | 默认地板：未提供制品 |
| `artifact_observed` | 制品路径存在**且被实际读取**且 sha256 已实算入清单 |
| `independently_verified` | 在 artifact_observed 之上存在显式 `verification` 条目（method/operator/at 三者齐备） |

不存在隐式升级。离线 JSON 的诚实默认：输入文件本身即每条记录的证据制品，因此全部记录
`artifact_observed`（读后实算 sha256），`verification` 为 `null`，**不含任何独立验证声明**，
`unsupported_capabilities` 声明 `source_side_verification_unavailable`。来源与可信边界的完整
说明见 [docs/evidence-manifest.md](evidence-manifest.md)。

审计复用：`verify_manifest()` 重读清单声明的制品、重算摘要并比对记录值——只验证已声明
观察过的制品，不产生新状态：

```python
from agent_comparability.evidence import verify_manifest

problems = verify_manifest(manifest)   # manifest 为清单 dict；返回问题列表
# 空列表 = 干净。制品事后被删/不可读 → artifact_missing_on_reverify；
# 内容被改动 → digest_mismatch；声明已观察但缺 artifact_ref/file_digest → structural。
```

### 旅程 3：单份 Inspect 日志

需要可选扩展 `pip install -e .[inspect]`。仓库内 `logs/`、`logs2/` 保存有真实管线产生的
`.eval` 日志（模型输出为 mock 性质、无基准含义，见
[experiments/scenarios_001/RECORD.md](../experiments/scenarios_001/RECORD.md)），可直接拿来运行：

```bash
python -m agent_comparability.inspect_log logs/2026-10-27T03-09-13-00-00_task_Y4UmUuMHoNanaYncL35tap.eval \
    --claim score_comparison --status verified --score-map C=1.0,I=0.0 --task-label my-task
```

显式映射政策（**禁止静默猜测**，任何一步不满足即 `exit 2`）：

- **`--status` 必填**：Inspect 源日志不含验证层，`reward_status` 必须由操作者显式断言（断言
  记入 manifest 警告）；省略时命令直接报错退出；
- **字母/字符串分数必须 `--score-map`**：如 `exact` scorer 的 `C`/`I` 需显式给出
  `--score-map C=1.0,I=0.0`；存在非数值分数而无映射时报错（如 `sample 1: 非数值 Score 'I' …`）；
- **任务身份显式断言**：优先级 `--task-label` > `header.eval.dataset.name` > 运行级哈希
  （哈希不稳定，跨日志比较必须 `--task-label`）；
- 记录粒度是**逐样本**：`task_id = {label}#{sample.id}`；error/未完成样本跳过并记数（绝不编造
  reward）；`trajectory_available` 默认 summary 读**不声明**（`--full-read` 才按实察设置）；
  `score_scale` 永不设置。

预期裁决形态：上面这条命令对一份**多样本**日志输出 `INADMISSIBLE`（`violated_conditions` 含
`same_task_id`）——同一日志内不同样本是**不同任务**，对它们做 `score_comparison` 被正确拒绝，
这是规范行为而非缺陷。逐题比较请对单样本日志运行，或分题运行。

### 旅程 4：跨日志比较（两份日志 + 共享 `--task-label`）

```bash
python -m agent_comparability.inspect_log \
    logs/2026-10-27T03-09-13-00-00_task_Y4UmUuMHoNanaYncL35tap.eval \
    logs2/2026-10-27T12-25-53-00-00_task_nEuWNXdmFPKn73rUP4C56Y.eval \
    --claim score_comparison --status verified --score-map C=1.0,I=0.0 \
    --task-label my-task --manifest multi.manifest.json
```

- 多份日志在共享 `--task-label`（同一任务的显式断言）下合并为单一 case、一次裁决；跨日志
  scorer 必须一致，混合不同 scorer 的分数 → `exit 2`；`--harness-name` 可逗号分隔逐日志赋值
  （数量须与日志数一致，缺省全部 `inspect-ai`——绝不虚标 harness）；manifest 中每条记录的
  `artifact_ref` 指向其来源日志并分日志实算摘要；
- **跨题池化会被正确拒绝**：若两份日志各含多个**不同题**的样本（如上两条仓库内日志各 2 样本），
  合并后组内 task_id 不唯一 → `INADMISSIBLE`（`same_task_id`），manifest 的
  `mapping_warnings` 含 `multilog_merge` 与 `multi_task_merge` 提示。逐题比较请用单样本日志；
- **仅模型不同 → `ADMISSIBLE`（cmp/0.4.0）**：两份**单样本**日志（路径换你自己的 `run-a.eval`、
  `run-b.eval`）共享同一 `--task-label`、harness 相同、仅模型不同时，`score_comparison` 依
  #27 单变量对称性判 `ADMISSIBLE`（冻结对 D1 锚定）。形态注意：`same_model` 仍作为条件不一致
  记入 `violated_conditions`，但 cmp/0.4.0 起不再**单独**触发 INADMISSIBLE——模型-only 变化改由
  `score_scale_consistent` 与 `zero_semantics_uniform` 独立把关（尺度违规仍拒绝，见冻结对 D2）：

```bash
python -m agent_comparability.inspect_log run-a.eval run-b.eval \
    --claim score_comparison --status verified --score-map C=1.0,I=0.0 --task-label same-task
```

### 旅程 5：校验收到的 CDR

产出侧两个入口都会输出 CDR；**消费侧**在采信他人产出的 CDR 之前，先用校验器检查——
纯 stdlib，无任何额外依赖：

```bash
python -m agent_comparability.validate cdr.json
# OK: 结构有效，policy_version 可识别（cmp/0.4.0）  → exit 0
```

消费侧退出码契约（三态，与产出侧的 0/2 契约互补）：

- **`exit 0`** = 结构有效且 `policy_version` 可识别（`cmp/0.3.x` 或 `cmp/0.4.x`——旧
  CDR 向后兼容），可作为结论依据；
- **`exit 1`** = 结构有效但 `policy_version` 无法识别：按 SPEC §5 版本规则，**必须丢弃
  该 CDR 并重新判定**，不得部分信任——即使其 `admissibility` 看似可用，任何字段都不得
  采信；诊断给出处置指引（向产出方确认版本，或用本包重新判定）；
- **`exit 2`** = 结构/schema 违规（缺必填字段、类型错、`admissibility` 越出四值枚举、
  `limitations` 缺防篡改声明、CDR 顶层未知字段等）：诊断精确到字段与数组下标（如
  `limitations[0]`、`admissibility`、`supported_claims[1]`）。

规则来源：required 字段清单**运行时读取**包内 `data/cdr.schema.json`（单一事实来源）；
`admissibility` 四值枚举、`policy_version` 正则（`cmp/0.3.x|cmp/0.4.x`）与 limitations
防篡改声明（含 `抗恶意篡改|tamper`）三条信任语义手工镜像同一 schema，并在源码注释同步
来源。结构违规优先于版本识别：结构已坏时不会落入 `exit 1` 的"可丢弃但结构良好"分支。

### 旅程 6：自检已安装环境（doctor）

wheel 里没有 `conformance/` 与 `adapters/`（pyproject 只随包分发 `src/` 与 `data/*`），
从 PyPI 安装的用户无法运行仓库的五项封闭门禁。doctor 是安装侧的只读自诊断——环境
是否完整（随包冻结案例在位、判定行为与随包预期一致、版本线一致）由它自证：

```bash
python -m agent_comparability doctor
# stdout 输出 JSON 报告；stderr 输出一行 verdict；exit 0 = 通过
```

报告要点（实际运行输出）：`overall`（pass/fail）、双锚点 `package_version`（软件线）
与 `policy_version`（语义线，与 SPEC 是不同版本空间，不互比），以及五项检查：

| 检查 | 内容 |
|---|---|
| `frozen_case_files` | 随包三份冻结案例在位，A/B/D 对数 = 9/13/4（合计 26）；A 集随包只有预期无 records，如实标注 |
| `frozen_expectations` | B+D 集随包带 records，17 对逐对判定 vs 随包冻结预期（全量核对，超出抽样下限） |
| `policy_version_line` | 随包 SPEC.md 声明的 policy 版本 == 参考实现的 `POLICY_VERSION` |
| `demo_cdr` | 内置合成记录可产出演示 CDR，必填字段齐备（required 运行时读自随包 schema） |
| `schema_validation` | 有 jsonschema（`[suite]` extra）→ 演示 CDR 结构校验；没有 → 如实 `not_run` + 原因 + 安装指引 |

退出码契约（两态）：`exit 0` = 可执行检查全部通过；`exit 1` = 任一检查失败。
**not_run 不是 pass**：缺可选依赖的检查在报告 `checks_not_run` 中如实列出，绝不静默
计为通过。doctor 是用户环境自检，**不是**仓库封闭门禁清单（AGENTS.md §3）的成员，
也不能替代其中任何一项。

边界说明：名为 `doctor` 的输入文件会与该元命令撞名——请改用 `./doctor` 形式或重命名。

## English

**Exit-code contract common to the two producing CLI entry points** (journeys 1–4;
Journey 5's consumer-side validator has its own three-state 0/1/2 contract, and
Journey 6's doctor has its own two-state 0/1 contract — see those sections):

- **A verdict is not a failure**: `exit 0` means a CDR was produced — all four verdicts
  (`ADMISSIBLE / INADMISSIBLE / PARTIAL / INCONCLUSIVE`) are normal outcomes; scripts must not
  treat a non-ADMISSIBLE verdict as a crash;
- **`exit 2` = input/mapping error** (unreadable file, malformed JSON, missing or mistyped
  contract fields, missing `--status`, unmapped letter scores, …): diagnostics are precise to the
  field path (e.g. `records[0].reward`), and invalid input is **never** silently converted into a
  seemingly successful verdict.

### Journey 1: Offline JSON → CDR

```bash
python -m agent_comparability examples/demo-case.json --claim score_comparison
# Add -o to write to a file instead of stdout:
python -m agent_comparability examples/demo-case.json --claim score_comparison -o cdr.json
```

`examples/demo-case.json` is a **synthetic/illustrative** sample: two records, same task, same
model, differing only in harness, both `verified`, rewards within [0,1] with no declared
`score_scale`.

#### The four verdicts × copy-paste commands

Prerequisites: install the package first — `pip install -e .` (see README §6; src layout, so
without installation `python -m agent_comparability` fails with ModuleNotFoundError) — and run
from the **repository root** (`examples/...` are relative paths; running elsewhere yields the
exit-2 "cannot read input file" error).

All four example files embed a `_comment` (SYNTHETIC/ILLUSTRATIVE + the expected verdict with a
one-line "why"). Each "why" below is excerpted from the CDR fields of an actual run (transcribed
from real output, not invented):

**ADMISSIBLE (side-by-side on the same scale)** — `examples/demo-case.json`:

```bash
python -m agent_comparability examples/demo-case.json --claim score_comparison
```

Why admissible: only the harness varies. `satisfied_conditions` include `same_task_id`,
`same_model`, `single_variable_isolation` and `continuous_score_preserved(...)` under the
implicit default scale; `supported_claims` carry `continuous_score_side_by_side(同尺度)`;
`violated_conditions` and `unsupported_claims` are both empty.

**INADMISSIBLE (confounded — comparison refused)** — `examples/demo-inadmissible.json`:

```bash
python -m agent_comparability examples/demo-inadmissible.json --claim score_comparison
```

Why refused: model **and** harness differ at the same time (two entangled variables, the effect
cannot be attributed). `violated_conditions` include `same_model` and
`single_variable_isolation`; `unsupported_claims` include
`score_comparison(任务/混淆/尺度条件冲突)`; `supported_claims` is empty (the README §8 shape).

**PARTIAL (zero-score semantics differ — stratified only)** — `examples/demo-partial.json`:

```bash
python -m agent_comparability examples/demo-partial.json --claim score_comparison
```

Why only partially usable: a `verified` 0 and an `unresolved_zero` 0 **do not mean the same
thing**. `violated_conditions` include `zero_semantics_uniform(verified_zero != unresolved_zero)`;
`supported_claims` carry only the per-status **stratified** rate
(`per_status_stratified_rate(verified_zero/unresolved_zero 分列)`); pooling the two kinds of
zeros into a single fail rate is listed in `unsupported_claims`
(`pooled_fail_rate(0 分语义混同)`).

**INCONCLUSIVE (missing evidence — highest priority)** — `examples/demo-inconclusive.json`:

```bash
python -m agent_comparability examples/demo-inconclusive.json --claim score_comparison
```

Why no conclusion: the record declares `trajectory_available=false` (no trace observed).
`violated_conditions` include `trace_available` — missing evidence outranks every other
condition in the priority ladder and dominates the verdict. The source reward is retained
verbatim: `unknown_conditions` record `source_reward_retained_but_unverifiable_by_us`, score
transcription stays in `supported_claims`
(`score_transcription(source_verifier_attested)`), while the success rate is listed in
`unsupported_claims` (`success_rate(含证据缺失记录)`).

An unrecognized `--claim` type also returns `INCONCLUSIVE` (no guessing;
`unknown_conditions` record `unrecognized_claim_type`).

### Journey 2: Evidence Manifest

```bash
python -m agent_comparability examples/demo-case.json --claim score_comparison \
    -o cdr.json --manifest cdr.manifest.json
```

The three manifest states (**evidence artifact level** — a different dimension from SPEC §1's
record-level trust tiers: they never enter `adjudicate()` and never alter any CDR field or
verdict):

| State | Meaning (sole trigger) |
|---|---|
| `source_claimed` | Default floor: no artifact provided |
| `artifact_observed` | Artifact path exists **and was actually read** and its sha256 computed into the manifest |
| `independently_verified` | On top of artifact_observed, an explicit `verification` entry exists (method/operator/at all present) |

No implicit upgrades exist. The honest offline-JSON default: the input file itself is the
evidence artifact for every record, so all records are `artifact_observed` (sha256 computed after
reading), `verification` is `null`, **no independent-verification claim is made**, and
`unsupported_capabilities` declares `source_side_verification_unavailable`. Full provenance and
trust-boundary discussion: [docs/evidence-manifest.md](evidence-manifest.md).

Audit reuse: `verify_manifest()` re-reads the artifacts a manifest claims to have observed,
recomputes digests and compares them against the recorded values — it verifies only declared
observations and never produces new states:

```python
from agent_comparability.evidence import verify_manifest

problems = verify_manifest(manifest)   # manifest dict; returns a list of problems
# Empty list = clean. Artifact later deleted/unreadable → artifact_missing_on_reverify;
# content modified → digest_mismatch; declared-observed but missing
# artifact_ref/file_digest → structural.
```

### Journey 3: A single Inspect log

Requires the optional extra `pip install -e .[inspect]`. The repository keeps real
pipeline-produced `.eval` logs under `logs/` and `logs2/` (model outputs are mock in nature and
carry no benchmark meaning — see
[experiments/scenarios_001/RECORD.md](../experiments/scenarios_001/RECORD.md)); you can run
against them directly:

```bash
python -m agent_comparability.inspect_log logs/2026-10-27T03-09-13-00-00_task_Y4UmUuMHoNanaYncL35tap.eval \
    --claim score_comparison --status verified --score-map C=1.0,I=0.0 --task-label my-task
```

Explicit mapping policy (**no silent guessing**; any unmet step exits with code 2):

- **`--status` is required**: the Inspect source log carries no verification tier, so
  `reward_status` must be explicitly asserted by the operator (the assertion is recorded as a
  manifest warning); omitting it fails the run outright;
- **Letter/string scores require `--score-map`**: e.g. the `exact` scorer's `C`/`I` need an
  explicit `--score-map C=1.0,I=0.0`; a non-numeric score without a mapping is an error
  (e.g. `sample 1: 非数值 Score 'I' …`);
- **Task identity is an explicit assertion**: precedence `--task-label` >
  `header.eval.dataset.name` > run-scoped hash (the hash is unstable; cross-log comparison
  requires `--task-label`);
- Records are **per-sample**: `task_id = {label}#{sample.id}`; error/incomplete samples are
  skipped and counted (no fabricated rewards); `trajectory_available` is left **undeclared** by
  the default summary read (`--full-read` sets it from actual observation); `score_scale` is
  never set.

Expected verdict shape: the command above, run against a **multi-sample** log, yields
`INADMISSIBLE` (`violated_conditions` include `same_task_id`) — different samples within one log
are **different tasks**, and a `score_comparison` over them is correctly refused. That is
specified behavior, not a defect. Compare per-question by running single-sample logs, or run one
question at a time.

### Journey 4: Cross-log comparison (two logs + shared `--task-label`)

```bash
python -m agent_comparability.inspect_log \
    logs/2026-10-27T03-09-13-00-00_task_Y4UmUuMHoNanaYncL35tap.eval \
    logs2/2026-10-27T12-25-53-00-00_task_nEuWNXdmFPKn73rUP4C56Y.eval \
    --claim score_comparison --status verified --score-map C=1.0,I=0.0 \
    --task-label my-task --manifest multi.manifest.json
```

- Multiple logs are merged into a single case under the shared `--task-label` (an explicit
  assertion of the same task) and adjudicated once; scorers must agree across logs — mixing
  scorers → `exit 2`; `--harness-name` accepts a comma-separated list assigned per log (the count
  must match the log count; default is `inspect-ai` for all — harness labels are never
  fabricated); in the manifest, each record's `artifact_ref` points to its own log with per-log
  digests;
- **Cross-question pooling is correctly refused**: when the two logs each contain several
  **different** questions (as the two in-repo logs above, 2 samples each), the merged group's
  task_ids are not unique → `INADMISSIBLE` (`same_task_id`), with `multilog_merge` and
  `multi_task_merge` notes in the manifest's `mapping_warnings`. Compare per-question using
  single-sample logs;
- **Model-only variation → `ADMISSIBLE` (cmp/0.4.0)**: with two **single-sample** logs (substitute
  your own `run-a.eval`, `run-b.eval`) sharing one `--task-label`, the same harness, and only the
  model differing, `score_comparison` is adjudicated `ADMISSIBLE` per #27 single-variable symmetry
  (frozen pair D1). Shape note: `same_model` is still recorded in `violated_conditions` as a
  condition mismatch, but since cmp/0.4.0 it no longer **by itself** triggers INADMISSIBLE —
  model-only variation is guarded independently by `score_scale_consistent` and
  `zero_semantics_uniform` (a scale violation is still refused; frozen pair D2):

```bash
python -m agent_comparability.inspect_log run-a.eval run-b.eval \
    --claim score_comparison --status verified --score-map C=1.0,I=0.0 --task-label same-task
```

### Journey 5: Validating a received CDR

Both producing entry points emit CDRs; on the **consuming side**, check a CDR received from
someone else before trusting it — pure stdlib, zero extra dependencies:

```bash
python -m agent_comparability.validate cdr.json
# OK: 结构有效，policy_version 可识别（cmp/0.4.0）  → exit 0
```

Consumer-side exit-code contract (three states, complementing the producer-side 0/2 contract):

- **`exit 0`** = structurally valid and `policy_version` recognizable (`cmp/0.3.x` or
  `cmp/0.4.x` — older CDRs stay valid), safe to use as a decision basis;
- **`exit 1`** = structurally valid but `policy_version` unrecognized: per the SPEC §5 version
  rule you **must discard the CDR and re-adjudicate** — no partial trust, and none of its
  fields (including `admissibility`) may be relied upon; the diagnostic gives concrete
  guidance (confirm the producer's policy version, or re-adjudicate with this package);
- **`exit 2`** = structural/schema violation (missing required field, wrong type,
  `admissibility` outside the four-value enum, `limitations` missing the tamper declaration,
  unknown top-level CDR fields, …): diagnostics are precise to the field and array index
  (e.g. `limitations[0]`, `admissibility`, `supported_claims[1]`).

Rule provenance: the required-field list is **read at runtime** from the packaged
`data/cdr.schema.json` (single source of truth); the `admissibility` four-value enum, the
`policy_version` regex (`cmp/0.3.x | cmp/0.4.x`), and the limitations tamper-declaration rule
(containing `抗恶意篡改|tamper`) are hand-mirrored from the same schema with their sync source
cited in code comments. Structural violations take precedence over version recognition: a
structurally broken CDR never lands in the "discarding but structurally fine" `exit 1` branch.

### Journey 6: Self-checking the installed environment (doctor)

The wheel ships neither `conformance/` nor `adapters/` (pyproject distributes only
`src/` and `data/*` with the package), so a PyPI user cannot run the repository's five
closed gates. The doctor is the install-side read-only self-diagnosis — it proves
whether the local environment is intact (packaged frozen cases present, adjudication
matches the packaged expectations, version lines consistent):

```bash
python -m agent_comparability doctor
# JSON report on stdout; one verdict line on stderr; exit 0 = pass
```

Report highlights (from an actual run): `overall` (pass/fail), the dual anchors
`package_version` (software line) and `policy_version` (semantics line — a different
version space from the SPEC, not compared against each other), and five checks:

| Check | Content |
|---|---|
| `frozen_case_files` | The three packaged frozen-case files are present with A/B/D pair counts 9/13/4 (26 total); the packaged A set is expectations-only (no records) and says so |
| `frozen_expectations` | The packaged B+D sets carry records; all 17 pairs are adjudicated against packaged frozen expectations (full check, beyond a mere sample) |
| `policy_version_line` | The policy version declared by the packaged SPEC.md equals the reference implementation's `POLICY_VERSION` |
| `demo_cdr` | Built-in synthetic records produce a demo CDR with every schema-required key present (required read at runtime from the packaged schema) |
| `schema_validation` | With jsonschema (the `[suite]` extra) → structural validation of the demo CDR; without → an honest `not_run` + reason + install hint |

Exit-code contract (two states): `exit 0` = every executable check passed; `exit 1` =
any check failed. **not_run is not pass**: a check skipped for a missing optional
dependency is listed under `checks_not_run`, never silently counted as passed. The
doctor is a user-environment self-check — it is **not** a member of the repository's
closed check list (AGENTS.md §3) and cannot substitute for any item in it.

Edge note: an input file literally named `doctor` collides with this meta-command —
pass `./doctor` instead, or rename the file.
