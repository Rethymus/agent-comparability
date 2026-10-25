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
# 双语互链
if "[简体中文](README.zh-CN.md)" not in en: errs.append("en 缺中文切换链接")
if "[English](README.md)" not in zh: errs.append("zh 缺英文切换链接")
# PyPI 误导命令
for f, name in [(en, "en"), (zh, "zh")]:
    if re.search(r"pip install (?!-e)[a-z-]+comparability", f):
        errs.append(f"{name}: 出现非 -e 的 pip install（未发 PyPI）")
for e in errs: print("FAIL:", e)
print("docs check:", "OK" if not errs else f"{len(errs)} errors")
sys.exit(1 if errs else 0)
