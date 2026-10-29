"""CDR 消费侧校验器（#41 后开发单元：补上 CDR 的消费闭环）。

用法：
    python -m agent_comparability.validate cdr.json

定位：产出侧（__main__.py / inspect_log.py）负责"生成 CDR"；本模块是**消费侧**
工具——收到他人产出的 CDR 后、采信之前先校验。只做结构与版本识别，绝不复用/
修改 adjudicate() 判定语义（不 import 包内任何判定代码，纯 stdlib）。

规则来源（镜像包内 data/cdr.schema.json）：
  - required 字段清单：**运行时读取**该文件（单一事实来源，schema 变更即生效）；
  - 类型/数组/元素字符串/minItems/additionalProperties=false：按同一文件的
    properties 泛化执行；
  - admissibility 四值枚举、policy_version 正则、limitations 防篡改 contains
    （"抗恶意篡改|tamper"）：**手工镜像**（同步来源见常量处注释——这三条是消费
    信任语义，不随 schema 文件静默变化，schema 修订时必须人工同步）。

退出码契约（消费侧三态，与产出侧"0=裁决成功/2=输入错误"互补）：
    0 = 结构有效且 policy_version 可识别（cmp/0.3.x 或 cmp/0.4.x，旧 CDR 向后兼容）
    1 = 结构有效但 policy_version 无法识别——按 SPEC §5 版本规则：必须丢弃该 CDR
        并重新判定，不得部分信任（即使其 admissibility 看似可用也不得采信任何字段）
    2 = 结构/schema 违规（含 JSON 语法/文件不可读/顶层非对象）——诊断精确到字段
        与数组下标（如 limitations[0]、admissibility、supported_claims[1]）
"""
import argparse
import json
import re
import sys
from importlib.resources import files as _pkg_files

# ---- 手工镜像规则（同步来源：src/agent_comparability/data/cdr.schema.json）----

# 同步来源：data/cdr.schema.json properties.admissibility.enum（四值，手工镜像）
_ADMISSIBILITY_VALUES = ("ADMISSIBLE", "INADMISSIBLE", "PARTIAL", "INCONCLUSIVE")
# 同步来源：data/cdr.schema.json properties.policy_version.pattern（手工镜像）。
# 该正则即"可识别版本"集合 = cmp/0.3.x ∪ cmp/0.4.x；不匹配 → exit 1（非 exit 2）：
# 结构良好但出自本工具不认识的 policy 世代，按 SPEC §5 丢弃并重判。
_KNOWN_POLICY_VERSION = re.compile(r"^cmp/0\.[34](\.\d+)?$")
# 同步来源：data/cdr.schema.json properties.limitations.contains.pattern（手工镜像）；
# SPEC §6：limitations 必须含 §1 防篡改声明。
_TAMPER_DECLARATION = re.compile(r"抗恶意篡改|tamper")


def load_schema():
    """运行时读取包内 data/cdr.schema.json（required 清单的单一事实来源）。"""
    text = (_pkg_files("agent_comparability") / "data" / "cdr.schema.json").read_text(
        encoding="utf-8")
    return json.loads(text)


def _type_name(v):
    # JSON 语义：bool 不是整数也不是字符串（Python 里 bool 是 int 子类，须排除）
    if isinstance(v, bool):
        return "boolean"
    if isinstance(v, str):
        return "string"
    if isinstance(v, (int, float)):
        return "number"
    if isinstance(v, list):
        return "array"
    if isinstance(v, dict):
        return "object"
    if v is None:
        return "null"
    return type(v).__name__


def structural_errors(doc, schema):
    """结构/schema 违规诊断列表（空列表 = 结构有效）。逐字段收集，不 fail-fast。

    required/类型/数组形状泛化自运行时 schema；admissibility/limitations 的
    信任语义三条为手工镜像（见模块头注释）。
    """
    if not isinstance(doc, dict):
        return [f"顶层必须是 JSON 对象（schema type: object），实际是 {_type_name(doc)}"]
    errs = []
    props = schema.get("properties", {})
    if schema.get("additionalProperties") is False:
        for k in doc:
            if k not in props:
                errs.append(f"{k}: 顶层未知字段（schema additionalProperties=false；"
                            f"注意 SPEC §5 的「忽略未知字段」仅适用于 Record 层，不适用于 CDR 顶层）")
    for k in schema.get("required", []):
        if k not in doc:
            errs.append(f"{k}: 缺少必填字段（schema required 清单，运行时读自 data/cdr.schema.json）")
    for k, spec in props.items():
        if k not in doc:
            continue
        v = doc[k]
        t = spec.get("type")
        if t == "string":
            if not isinstance(v, str) or isinstance(v, bool):
                errs.append(f"{k}: 必须是字符串（schema type: string），实际是 {_type_name(v)}")
        elif t == "array":
            if not isinstance(v, list):
                errs.append(f"{k}: 必须是数组（schema type: array），实际是 {_type_name(v)}")
                continue
            min_items = spec.get("minItems")
            if min_items is not None and len(v) < min_items:
                errs.append(f"{k}: 数组至少 {min_items} 项（schema minItems={min_items}），"
                            f"实际 {len(v)} 项")
            items = spec.get("items", {})
            if items.get("type") == "string":
                for i, item in enumerate(v):
                    if not isinstance(item, str) or isinstance(item, bool):
                        errs.append(f"{k}[{i}]: 数组元素必须是字符串，实际是 {_type_name(item)}")
            contains = spec.get("contains")
            if k == "limitations" and contains is not None:
                # 手工镜像执行（同步来源见 _TAMPER_DECLARATION）：至少一项匹配防篡改声明
                bad = [i for i, item in enumerate(v)
                       if not (isinstance(item, str) and _TAMPER_DECLARATION.search(item))]
                if len(bad) == len(v):
                    where = "、".join(f"limitations[{i}]" for i in bad[:4]) or "数组为空"
                    errs.append(
                        "limitations: 必须包含至少一条防篡改声明"
                        "（匹配 '抗恶意篡改|tamper'，同步来源 data/cdr.schema.json "
                        "properties.limitations.contains）；"
                        f"不匹配项：{where}（SPEC §6/SPEC §1）")
        # 手工镜像：admissibility 四值枚举（同步来源见 _ADMISSIBILITY_VALUES）
        if k == "admissibility" and (not isinstance(v, str) or v not in _ADMISSIBILITY_VALUES):
            errs.append(f"admissibility: 必须是四值枚举之一 "
                        f"{'|'.join(_ADMISSIBILITY_VALUES)}"
                        f"（同步来源 data/cdr.schema.json properties.admissibility.enum），"
                        f"实际是 {v!r}")
    return errs


def validate_cdr(doc, schema):
    """返回 (退出码, 诊断列表)：2=结构违规；1=结构有效但版本不可识别；0=通过。"""
    errs = structural_errors(doc, schema)
    if errs:
        return 2, errs
    pv = doc["policy_version"]
    if not _KNOWN_POLICY_VERSION.match(pv):
        return 1, [pv]
    return 0, []


_EXIT1_GUIDANCE = (
    "按 SPEC §5 版本规则：消费方遇到不认识的 policy_version 时必须丢弃该 CDR 并重新判定，"
    "不得部分信任——不得将该 CDR 的任何字段（包括 admissibility）用作结论依据。"
    "请向产出方确认其 policy 版本，或用本包重新判定："
    "python -m agent_comparability <输入.json> --claim <claim 类型>")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="python -m agent_comparability.validate",
        description="CDR（Comparison Decision Record）消费侧校验器："
                    "结构镜像 data/cdr.schema.json + policy_version 识别（SPEC §5）")
    p.add_argument("cdr", help="待校验的 CDR JSON 文件路径")
    args = p.parse_args(argv)

    try:
        raw = open(args.cdr, encoding="utf-8").read()
    except OSError as e:
        print(f"error: 无法读取 CDR 文件 {args.cdr}: {e.strerror or e}", file=sys.stderr)
        return 2
    try:
        doc = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"error: JSON 解析错误 {args.cdr}（第 {e.lineno} 行第 {e.colno} 列）: {e.msg}",
              file=sys.stderr)
        return 2

    code, diags = validate_cdr(doc, load_schema())
    if code == 2:
        print(f"error: CDR 结构/schema 违规 {args.cdr}（{len(diags)} 处，诊断精确到字段）：",
              file=sys.stderr)
        for d in diags:
            print(f"  - {d}", file=sys.stderr)
        print("结构无效的 CDR 不得采信；请向产出方反馈或重新判定。", file=sys.stderr)
        return 2
    if code == 1:
        print(f"error: 结构有效，但无法识别 policy_version '{diags[0]}'"
              f"（本工具识别 cmp/0.3.x 与 cmp/0.4.x）。{_EXIT1_GUIDANCE}", file=sys.stderr)
        return 1
    print(f"OK: 结构有效，policy_version 可识别（{doc['policy_version']}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
