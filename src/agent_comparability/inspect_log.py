"""Inspect AI EvalLog → cmp 记录转换器（#20）。

只经官方 API 读取（read_eval_log / read_eval_log_sample_summaries；--full-read 时
全量读取轨迹），不解析 .eval 内部结构。逐样本记录粒度（聚合=语义猜测，拒绝）。

诚实映射政策（禁止静默猜测）：
  - reward_status：源日志不含验证层 → 必须由操作者显式 --status 断言（记入警告）；
  - 非数值 Score（如 exact 的 C/I）→ 必须显式 --score-map，否则报错；
  - task 身份：--task-label > dataset.name > 运行哈希（不稳定），来源记入警告；
  - trajectory_available：默认 summary 读不声明（未观察不声明）；--full-read 按实察设置；
  - score_scale 永不设置（[0,1] 数值走 SPEC 隐式默认，越界由核心如实判定）；
  - error/未完成样本跳过并记数（绝不编造 reward）。

用法：
  python -m agent_comparability.inspect_log LOG.eval --claim score_comparison \
      --status verified [--scorer exact] [--score-map C=1.0,I=0.0] \
      [--task-label T] [--harness-name H] [--full-read] \
      [-o cdr.json] [--manifest m.json] [--save-case c.json]

退出码：0 = 产出 CDR（裁决≠程序失败）；2 = 输入/映射错误。
"""
import argparse
import json
import sys

STATUS_FLAG_HINT = "源日志不含验证层（verification tier）——reward_status 必须由操作者显式断言：--status verified|unresolved_zero|…（禁止静默猜测）"


class MappingError(Exception):
    """映射无法诚实完成：消息进入诊断，绝不猜测。"""


def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def parse_score_map(spec):
    """'C=1.0,I=0.0' -> {'C': 1.0, 'I': 0.0}；格式/数值非法即 MappingError。"""
    m = {}
    for part in spec.split(","):
        part = part.strip()
        if "=" not in part:
            raise MappingError(f"--score-map 格式非法：'{part}'（应为 TOKEN=数值，逗号分隔）")
        k, v = part.split("=", 1)
        try:
            m[k.strip()] = float(v)
        except ValueError:
            raise MappingError(f"--score-map 数值非法：'{part}'")
    return m


def records_from_summaries(summaries, scorer, status, task_label, harness,
                           score_map=None):
    """官方 EvalSampleSummary 列表 → cmp records（逐样本）。跳过 error 样本；
    非数值 Score 无显式映射即 MappingError。"""
    epoch_count = {}
    for s in summaries:
        epoch_count[s.id] = epoch_count.get(s.id, 0) + 1
    records = []
    for s in summaries:
        if getattr(s, "error", None) or s.completed is False:
            continue  # 不编造 reward——跳过，调用方负责记警告
        score = s.scores[scorer]
        value = score.value
        if value is None:
            raise MappingError(f"sample {s.id}: score value 为 None（样本报错？检查日志）")
        if _is_number(value):
            reward = value
        else:
            if not score_map or str(value) not in score_map:
                raise MappingError(
                    f"sample {s.id}: 非数值 Score '{value}'（scorer={scorer}）——"
                    f"必须显式 --score-map {value}=数值（禁止静默猜测）")
            reward = score_map[str(value)]
        rec = {"task_id": f"{task_label}#{s.id}", "harness": harness,
               "model": None, "reward": reward, "reward_status": status}
        # model 由调用方按 log.eval.model 填入（summary 不携带）
        records.append((s, rec))
    out = []
    for s, rec in records:
        if epoch_count[s.id] > 1:
            rec["repetition_count"] = epoch_count[s.id]
        out.append(rec)
    return out


def _fill_model(records, model):
    for rec in records:
        rec["model"] = model
    return records


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="python -m agent_comparability.inspect_log",
        description="Inspect AI EvalLog → cmp 记录 → CDR（官方 API；显式映射政策，禁止静默猜测）")
    p.add_argument("log", nargs="+",
                   help="Inspect .eval 日志路径（一个或多个；多日志=同 task-label 断言下的跨日志比较）")
    p.add_argument("--claim", required=True, help="请求结论类型（同核心 CLI）")
    p.add_argument("--status", help="reward_status 的操作者显式断言（必填：源日志不含验证层）")
    p.add_argument("--scorer", help="多 scorer 日志必须显式指定；单 scorer 自动选用")
    p.add_argument("--score-map", dest="score_map",
                   help="非数值 Score 显式映射，如 C=1.0,I=0.0（必填当存在字母/字符串分数）")
    p.add_argument("--task-label", dest="task_label",
                   help="任务身份标签（跨日志比较同一任务时必须显式断言）")
    p.add_argument("--harness-name", dest="harness", default="inspect-ai",
                   help="harness 标签（默认 inspect-ai；多日志可用逗号分隔逐日志赋值，数量须匹配）")
    p.add_argument("--full-read", action="store_true",
                   help="全量读取样本以观察轨迹（默认仅 header+summaries，不声明轨迹状态）")
    p.add_argument("-o", "--output", help="CDR 输出文件（缺省 stdout）")
    p.add_argument("--manifest", help="同时输出 Evidence Manifest")
    p.add_argument("--save-case", dest="save_case", help="保存转换后的 cmp case JSON（审计用）")
    args = p.parse_args(argv)

    if not args.status:
        print(f"error: 缺少 --status。{STATUS_FLAG_HINT}", file=sys.stderr)
        return 2
    score_map = None
    if args.score_map:
        try:
            score_map = parse_score_map(args.score_map)
        except MappingError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2

    harnesses = [h.strip() for h in args.harness.split(",")]
    if len(harnesses) not in (1, len(args.log)):
        print(f"error: --harness-name 提供了 {len(harnesses)} 个标签，但日志数为 {len(args.log)}"
              f"（须为 1 个或与日志数一致）", file=sys.stderr)
        return 2
    if len(harnesses) == 1:
        harnesses = harnesses * len(args.log)

    try:
        import inspect_ai  # noqa: F401
        from inspect_ai.log import read_eval_log, read_eval_log_sample_summaries
    except ImportError:
        print("error: 未安装 inspect-ai。转换器需要可选依赖：pip install -e .[inspect]",
              file=sys.stderr)
        return 2

    conv_warnings = []
    merged_records = []
    artifacts = {}
    eval_ids = []
    scorer_seen = None
    n_skipped = 0
    for log_path in args.log:
        try:
            hdr = read_eval_log(log_path, header_only=True)
            summaries = read_eval_log_sample_summaries(log_path)
        except Exception as e:  # 官方 API 对损坏/不存在文件的各类异常 → 统一诊断
            print(f"error: 无法读取日志 {log_path}: {type(e).__name__}: {e}", file=sys.stderr)
            return 2
        usable = [s for s in summaries if not getattr(s, "error", None) and s.completed is not False]
        if not usable:
            print(f"error: 日志无可用样本（{log_path}：{len(summaries)} 条全部 error/未完成）——不编造记录",
                  file=sys.stderr)
            return 2
        scorer_names = sorted({k for s in usable for k in (s.scores or {})})
        if args.scorer:
            if args.scorer not in scorer_names:
                print(f"error: 日志 {log_path} 不存在 scorer '{args.scorer}'（可用：{scorer_names}）",
                      file=sys.stderr)
                return 2
            scorer = args.scorer
        elif len(scorer_names) == 1:
            scorer = scorer_names[0]
        else:
            print(f"error: 日志 {log_path} 多 scorer（{scorer_names}）——必须显式 --scorer，禁止静默选择",
                  file=sys.stderr)
            return 2
        if scorer_seen is None:
            scorer_seen = scorer
        elif scorer != scorer_seen:
            print(f"error: 跨日志 scorer 不一致（{log_path} 为 '{scorer}'，先前为 '{scorer_seen}'）"
                  f"——拒绝混合不同 scorer 的分数", file=sys.stderr)
            return 2

        if args.task_label:
            task_label, src = args.task_label, "operator_override(跨日志比较的显式断言)"
        elif hdr.eval.dataset and hdr.eval.dataset.name:
            task_label, src = hdr.eval.dataset.name, "header.eval.dataset.name"
        else:
            task_label = f"run-{hdr.eval.task_id}"
            src = "header.eval.task_id(运行级哈希——跨日志比较需 --task-label 显式断言同一任务)"
        if not conv_warnings or not any(w.startswith("task_identity_source=") for w in conv_warnings):
            conv_warnings.append(f"task_identity_source={src}")
        n_skipped += len(summaries) - len(usable)

        try:
            recs = records_from_summaries(summaries, scorer=scorer, status=args.status,
                                          task_label=task_label, harness=harnesses[args.log.index(log_path)],
                                          score_map=score_map)
        except MappingError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        _fill_model(recs, hdr.eval.model)
        for rec in recs:
            artifacts[len(merged_records)] = log_path
            merged_records.append(rec)
        eval_ids.append(hdr.eval.eval_id or hdr.eval.task_id)

    conv_warnings.append(f"reward_status_asserted_by_operator(--status {args.status}；源日志不含验证层——未猜测)")
    conv_warnings.append(f"scorer_selected({scorer_seen})")
    if len(args.log) > 1:
        conv_warnings.append(f"multilog_merge({len(args.log)} 日志合并为单一 case；--task-label 共享断言同一任务)")
    if n_skipped:
        conv_warnings.append(f"skipped_error_samples({n_skipped} 条 error/未完成——不编造 reward)")

    records = merged_records
    distinct_tasks = {r["task_id"] for r in records}
    if len(distinct_tasks) > 1:
        conv_warnings.append(
            f"multi_task_merge({len(distinct_tasks)} 个不同 task_id——规范要求 score_comparison "
            f"全部记录同任务；跨题合并将被拒绝。逐题比较请用单样本日志或分题运行)")
    if score_map:
        conv_warnings.append(f"score_map_applied({args.score_map}——字母/字符串分数经显式映射)")

    case = {"id": "inspect-evallog:" + "+".join(eval_ids), "records": records}

    if args.full_read:
        try:
            for log_path in args.log:
                full = read_eval_log(log_path)
                by_id = {}
                for s in full.samples:
                    by_id.setdefault(str(s.id), []).append(s)
                for rec in records:
                    if rec.get("trajectory_available") is not None:
                        continue
                    sid = rec["task_id"].rsplit("#", 1)[1]
                    if sid in by_id:
                        obs = any(getattr(s, "messages", None) or getattr(s, "events", None)
                                  for s in by_id[sid])
                        rec["trajectory_available"] = obs
            conv_warnings.append("trajectory_inspected(full_read;按实察设置 trajectory_available)")
        except Exception as e:
            print(f"error: --full-read 读取失败: {type(e).__name__}: {e}", file=sys.stderr)
            return 2
    else:
        conv_warnings.append("trajectory_not_inspected(summary_read;--full-read 可观察轨迹)")

    from . import adjudicate
    cdr = adjudicate(case, args.claim).to_dict()
    out = json.dumps(cdr, ensure_ascii=False, indent=2)
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(out + "\n")
        except OSError as e:
            print(f"error: 无法写入 {args.output}: {e.strerror or e}", file=sys.stderr)
            return 2
    else:
        print(out)
    if args.save_case:
        try:
            with open(args.save_case, "w", encoding="utf-8") as f:
                f.write(json.dumps(case, ensure_ascii=False, indent=2) + "\n")
        except OSError as e:
            print(f"error: 无法写入 {args.save_case}: {e.strerror or e}", file=sys.stderr)
            return 2
    if args.manifest:
        from . import evidence
        m = evidence.build_manifest(case, source_kind="inspect_evallog",
                                    source_version=inspect_ai.__version__,
                                    artifacts=artifacts,
                                    requested_claim=args.claim,
                                    unsupported_capabilities=[
                                        "source_side_verification_unavailable",
                                        "verification_tier_absent_in_source"])
        m["mapping_warnings"].extend(conv_warnings)
        try:
            with open(args.manifest, "w", encoding="utf-8") as f:
                f.write(json.dumps(m, ensure_ascii=False, indent=2) + "\n")
        except OSError as e:
            print(f"error: 无法写入 {args.manifest}: {e.strerror or e}", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
