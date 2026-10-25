"""自包含硬门禁：发行树任何 .py 不得引用研究仓路径/模块。CI 与本地共用。"""
import sys
from pathlib import Path

BAD = ["import cmp", "from cmp", "from arlib", "import arlib", '"scripts/', '"experiments/']
hits = [f"{f}:{p}" for f in Path(".").rglob("*.py")
        if "__pycache__" not in str(f) and ".git" not in str(f) and f.name not in ("terminal_scan.py", "test_gate_regressions.py")
        for p in BAD if p in f.read_text(encoding="utf-8", errors="ignore")]
for h in hits:
    print("RESIDUAL:", h)
sys.exit(1 if hits else 0)
