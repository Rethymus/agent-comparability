"""离线 JSON → CDR 命令行闭环（#16，零额外运行时依赖）。

用法：
    python -m agent_comparability input.json --claim score_comparison [-o cdr.json]

输入契约（= adjudicate 既有输入形状）：
    {"id": str,
     "records": [{"task_id": str, "harness": str, "model": str,
                  "reward": number, "reward_status": str,
                  ...可选 trajectory_available/score_scale/repetition_count}]}

退出码契约：
    0 = 产出 CDR（ADMISSIBLE/INADMISSIBLE/PARTIAL/INCONCLUSIVE 均为裁决成功，非程序失败）
    2 = 输入错误（文件不可读/JSON 语法/契约字段缺失或类型错）——诊断含出错路径；
        无效输入绝不允许被转换为貌似成功的裁决

自检元命令 doctor：python -m agent_comparability doctor —— 包环境只读自诊断
（PyPI 安装侧环境自证，见 doctor.py），退出码 0/1 与上述产出侧契约无关。

本模块只做契约存在性与类型检查；一切判定语义由 adjudicate() 负责（不重新实现判定表，
不改规范语义）。未知字段按 SPEC §5 忽略并记入 CDR 的 unknown_conditions，不在此报错。
"""
import argparse
import json
import sys

from . import adjudicate

REQUIRED_STR = ("task_id", "harness", "model", "reward_status")


class ContractError(Exception):
    """输入违反契约：消息含出错路径，如 records[2].reward。"""


def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def validate_case(case):
    if not isinstance(case, dict):
        raise ContractError("输入顶层必须是 JSON 对象，实际是 " + type(case).__name__)
    if "id" not in case:
        raise ContractError("缺少必填字段 id")
    if not isinstance(case["id"], str):
        raise ContractError("id 必须是字符串，实际是 " + type(case["id"]).__name__)
    if "records" not in case:
        raise ContractError("缺少必填字段 records")
    if not isinstance(case["records"], list) or not case["records"]:
        raise ContractError("records 必须是非空数组")
    for i, r in enumerate(case["records"]):
        where = f"records[{i}]"
        if not isinstance(r, dict):
            raise ContractError(f"{where} 必须是 JSON 对象，实际是 " + type(r).__name__)
        for k in REQUIRED_STR:
            if k not in r:
                raise ContractError(f"{where}.{k} 缺失（必填字段）")
            if not isinstance(r[k], str):
                raise ContractError(f"{where}.{k} 必须是字符串，实际是 " + type(r[k]).__name__)
        if "reward" not in r:
            raise ContractError(f"{where}.reward 缺失（必填字段）")
        if not _is_number(r["reward"]):
            raise ContractError(f"{where}.reward 必须是数值，实际是 " + type(r["reward"]).__name__)
        if "trajectory_available" in r and not isinstance(r["trajectory_available"], bool):
            raise ContractError(f"{where}.trajectory_available 必须是布尔值")
        if "score_scale" in r and not isinstance(r["score_scale"], dict):
            raise ContractError(f"{where}.score_scale 必须是对象 {{range, unit, verifier}}")
        if "repetition_count" in r and (not _is_int(r["repetition_count"]) or r["repetition_count"] < 1):
            raise ContractError(f"{where}.repetition_count 必须是 >=1 的整数")


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else list(argv)
    if args and args[0] == "doctor":  # 自检元命令分流（不占产出侧输入契约）
        from .doctor import main as doctor_main
        return doctor_main()
    p = argparse.ArgumentParser(
        prog="python -m agent_comparability",
        description="离线评测记录 JSON → 结构化 CDR（Comparison Decision Record）")
    p.add_argument("input", help="输入 JSON 文件路径（契约见模块文档）")
    p.add_argument("--claim", required=True,
                   help="请求结论类型：score_comparison / causal / descriptive_registration"
                        "（未支持类型 → INCONCLUSIVE，不猜测）")
    p.add_argument("-o", "--output", help="CDR 输出文件路径（缺省打印到 stdout）")
    p.add_argument("--manifest", help="同时输出 Evidence Manifest（#18）：输入文件作为证据制品"
                                      "实算 sha256，全部记录 artifact_observed，不含任何独立验证声明")
    args = p.parse_args(args)

    try:
        raw = open(args.input, encoding="utf-8").read()
    except OSError as e:
        print(f"error: 无法读取输入文件 {args.input}: {e.strerror or e}", file=sys.stderr)
        return 2
    try:
        case = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"error: JSON 解析错误 {args.input}（第 {e.lineno} 行第 {e.colno} 列）: {e.msg}", file=sys.stderr)
        return 2
    try:
        validate_case(case)
    except ContractError as e:
        print(f"error: 输入违反契约 {args.input}: {e}", file=sys.stderr)
        return 2

    cdr = adjudicate(case, args.claim).to_dict()
    out = json.dumps(cdr, ensure_ascii=False, indent=2)
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(out + "\n")
        except OSError as e:
            print(f"error: 无法写入输出文件 {args.output}: {e.strerror or e}", file=sys.stderr)
            return 2
    else:
        print(out)
    if args.manifest:
        from .evidence import build_manifest
        # 离线 JSON 的诚实默认：输入文件即证据制品（读后实算摘要）；无来源端验证能力，
        # 无独立验证声明——绝不把 source_claimed 冒充为已验证。
        m = build_manifest(case, source_kind="offline_json",
                           artifacts={i: args.input for i in range(len(case["records"]))},
                           requested_claim=args.claim,
                           unsupported_capabilities=["source_side_verification_unavailable"])
        try:
            with open(args.manifest, "w", encoding="utf-8") as f:
                f.write(json.dumps(m, ensure_ascii=False, indent=2) + "\n")
        except OSError as e:
            print(f"error: 无法写入 manifest 文件 {args.manifest}: {e.strerror or e}", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
