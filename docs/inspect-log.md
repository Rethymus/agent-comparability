# Inspect EvalLog → cmp 转换器 / Inspect EvalLog converter

> **English summary below the Chinese section.** 对应模块：`agent_comparability.inspect_log`（#20）。

## 中文

### 定位与诚实映射政策

把**实际产生的** Inspect AI `.eval` 日志转换为 cmp 记录并产出 CDR 与 Evidence Manifest。只经官方 API 读取（`read_eval_log` / `read_eval_log_sample_summaries`；`--full-read` 才全量读轨迹），不解析内部文件结构。核心原则：**禁止静默猜测**——

- `reward_status`：源日志不含验证层 → 必须显式 `--status`（操作者断言，记入 manifest 警告）；
- 非数值 Score（如 `exact` 的 `C`/`I`）→ 必须显式 `--score-map C=1.0,I=0.0`，否则报错；
- 任务身份：`--task-label`（跨日志比较同一任务的显式断言）> `dataset.name` > 运行哈希（不稳定，警告提示）；
- `trajectory_available`：默认 summary 读**不声明**（未观察不声明）；`--full-read` 按实察设置；
- `score_scale` 永不设置；error/未完成样本跳过并记数（绝不编造 reward）；
- 逐样本记录粒度（`task_id = {label}#{sample.id}`）——聚合到单记录属语义猜测，拒绝。

### 用法

```bash
pip install -e .[inspect]
python -m agent_comparability.inspect_log run.eval \
    --claim score_comparison --status verified \
    --score-map C=1.0,I=0.0 --task-label my-benchmark \
    [-o cdr.json] [--manifest m.json] [--save-case c.json]
```

退出码：`0` = 产出 CDR（INADMISSIBLE/PARTIAL/INCONCLUSIVE 是裁决结果）；`2` = 输入/映射错误（缺 `--status`、字母分数无映射、未知 scorer、文件不可读、缺 inspect-ai、无可用样本）。

注意：同一日志内不同样本是不同任务（`task_id` 不同），对它们做 `score_comparison` 会得到 `INADMISSIBLE`——这是正确拒绝，不是缺陷。跨 harness/跨日志比较请对每个日志用相同的 `--task-label`。

### 与 Evidence Manifest 的关系

`--manifest` 产出 §3 的 Evidence Manifest：`source_kind=inspect_evallog`、`source_version=inspect_ai.__version__`、逐记录对 `.eval` 文件实算 sha256（artifact_observed）、全部映射决策入 `mapping_warnings`、`unsupported_capabilities` 含 `verification_tier_absent_in_source`。

## English

Converts an **actually-produced** Inspect AI `.eval` log into cmp records, a CDR, and an Evidence Manifest — official APIs only, never parsing internal file structure. Core rule: **no silent guessing** — `reward_status` requires an explicit `--status` operator assertion (logs carry no verification tier); non-numeric scores (e.g. `exact`'s `C`/`I`) require an explicit `--score-map` or the run fails; task identity prefers an explicit `--task-label` (needed to compare the same task across logs) over `dataset.name` over the run-scoped hash; `trajectory_available` is left unset under the default summary read (never claim what wasn't observed) and set from actual observation under `--full-read`; `score_scale` is never set; error/incomplete samples are skipped and counted, never assigned a fabricated reward. Records are per-sample (`task_id = {label}#{sample.id}`) — aggregation into a single record would be a semantic guess and is rejected. Note that comparing different samples within one log correctly yields `INADMISSIBLE` (different tasks); use the same `--task-label` across logs to compare harnesses on one task. Exit codes: `0` = CDR produced (verdicts are not failures), `2` = input/mapping errors. The manifest integrates §3: per-record sha256 of the `.eval` artifact (artifact_observed), all mapping decisions recorded as warnings, `verification_tier_absent_in_source` declared unsupported.

## 多日志比较（#26）

```bash
python -m agent_comparability.inspect_log run-a.eval run-b.eval \
    --claim score_comparison --status verified \
    --score-map C=1.0,I=0.0 --task-label my-benchmark \
    [--harness-name harness-a,harness-b] [--manifest m.json]
```

- 多个日志在共享 `--task-label`（同一任务的显式断言）下合并为单一 case，一次裁决；
- `--harness-name` 可逗号分隔逐日志赋值（数量须匹配；缺省全部 `inspect-ai`——**绝不虚标 harness**）；
- 跨日志 scorer 必须一致（混合不同 scorer 的分数 → exit 2）；
- 每记录的 manifest `artifact_ref` 指向其来源日志并分日志实算摘要；
- **语义提示**：`score_comparison` 要求全部记录同任务。两个多样本日志整体合并（跨题池化）会因
  `same_task_id` 被拒（INADMISSIBLE，附 `multi_task_merge` 警告）——逐题比较请用单样本日志；
- **已知规范歧义（#27）**："仅模型不同（同任务同 harness）"的 `score_comparison` 在
  SPEC §3.3-2（判定表，规范核心）下判 INADMISSIBLE，而 §4 变量表第 2 行写 ADMISSIBLE。
  实现与独立实现当前均按 §3.3 执行；歧义裁决前本行为锁定并如实标注。

## Multi-log comparison (English summary)

Pass multiple `.eval` paths with a shared explicit `--task-label` to merge them into one
case and one verdict; per-log harness labels via comma-separated `--harness-name` (count
must match; default all `inspect-ai` — harness labels are never fabricated). Scorers must
agree across logs (mixed scorers → exit 2). Each record's manifest artifact_ref points to
its own log with per-log digests. Semantics note: `score_comparison` requires all records
to share one task — pooling two multi-sample logs is correctly refused (INADMISSIBLE with a
`multi_task_merge` warning); compare per-question with single-sample logs. Known spec
ambiguity (#27): model-only variation under `score_comparison` follows SPEC §3.3-2
(INADMISSIBLE) although the §4 summary table says ADMISSIBLE; both implementations follow
§3.3 and the behavior is locked until the ambiguity is adjudicated.
