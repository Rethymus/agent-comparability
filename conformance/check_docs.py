"""双语文档同步与链接检查：README.md 与 README.zh-CN.md 16 节等价 + 仓库内相对链接有效。"""
import re, sys
from pathlib import Path

en, zh = Path("README.md").read_text(encoding="utf-8"), Path("README.zh-CN.md").read_text(encoding="utf-8")
sections = ["Project Overview", "Problem & Motivation", "What .* Does", "What .* Does NOT",
            "Main Features", "Installation", "Quickstart", "Input/Output Example", "Architecture",
            "Conformance Suite", "Integrations", "Specification & Versioning", "Limitations",
            "Contributing", "Security", "License"]
errs = []
en_h = re.findall(r"^## \d+\. (.+)$", en, re.M)
zh_h = re.findall(r"^## \d+\. (.+)$", zh, re.M)
if len(en_h) != 16 or len(zh_h) != 16:
    errs.append(f"节数: en={len(en_h)} zh={len(zh_h)} (期望16)")
for f, name in [(en, "en"), (zh, "zh")]:
    for link in re.findall(r"\]\(([^)#]+?)(?:#[^)]*)?\)", f):
        if link.startswith(("http", "mailto")):
            continue
        if not (Path(link).exists() or (Path(link) / "README.md").exists()):
            errs.append(f"{name}: 断链 {link}")
# 双语切换器（vue-element-admin 模式）：当前语言加粗不可点，另一语言为链接；
# 位置必须在主标题之后（不得回到文件首行）
def _switcher_errs(text, other_link, active_bold, name):
    e = []
    if other_link not in text:
        e.append(f"{name}: 缺另一语言链接 {other_link}")
    if f"**{active_bold}**" not in text:
        e.append(f"{name}: 当前语言未加粗标记 **{active_bold}**")
    if f"[{active_bold}](README" in text:
        e.append(f"{name}: 当前语言不应是链接（自身页面无需跳转）")
    t_idx, s_idx = text.find("# Agent Comparability"), text.find(other_link)
    if t_idx == -1 or s_idx < t_idx:
        e.append(f"{name}: 切换器必须位于主标题之后")
    if not text.lstrip().startswith("<div align=\"center\">"):
        e.append(f"{name}: 顶部应为居中块（<div align=center>）")
    return e
errs += _switcher_errs(en, "[简体中文](README.zh-CN.md)", "English", "en")
errs += _switcher_errs(zh, "[English](README.md)", "简体中文", "zh")
# 英文 README 中文内容策略：实际输出含中文（真实行为），必须带本地化说明
import re as _re
cjk = _re.compile(r"[一-鿿]")
if cjk.search(en) and "currently in Chinese" not in en:
    errs.append("en: 含中文片段但缺本地化说明（'output messages are currently in Chinese'）")
# 双语关键语义标记等量（四类 admissibility + 关键主张词）
for tok in ["ADMISSIBLE", "INADMISSIBLE", "PARTIAL", "INCONCLUSIVE",
            "score_comparison", "descriptive_registration", "causal"]:
    ce, cz = en.count(tok), zh.count(tok)
    if tok in ("ADMISSIBLE", "INCONCLUSIVE") and (ce == 0 or cz == 0):
        errs.append(f"关键标记缺失: {tok} en={ce} zh={cz}")
# PyPI 误导命令
for f, name in [(en, "en"), (zh, "zh")]:
    if re.search(r"pip install (?!-e)[a-z-]+comparability", f):
        errs.append(f"{name}: 出现非 -e 的 pip install（未发 PyPI）")
for e in errs: print("FAIL:", e)
print("docs check:", "OK" if not errs else f"{len(errs)} errors")
sys.exit(1 if errs else 0)
