# Agent Comparability

**When can you compare AI agent evaluation results — and what claims do they support?**

A framework-independent specification (`spec/SPEC.md`, cmp/0.3.1), a frozen conformance
suite, and a thin reference implementation that adjudicates *comparability*, not scores.

```python
from agent_comparability import adjudicate
cdr = adjudicate({"id": "demo", "records": [
    {"task_id": "t1", "harness": "h1", "model": "m1", "reward": 1.0, "reward_status": "verified"},
    {"task_id": "t1", "harness": "h2", "model": "m1", "reward": 0.0, "reward_status": "verified"}]},
    "score_compare")
print(cdr.admissibility)       # ADMISSIBLE
print(cdr.supported_claims)    # what you MAY conclude
print(cdr.unsupported_claims)  # what you MAY NOT
```

## Why

Rankings reverse across harnesses; scores mix semantics (verified failure ≠ unresolved
zero); missing traces silently inflate success rates. This project makes those
boundaries machine-checkable.

## Install & test

```bash
pip install -e .[suite]
python conformance/run_suite.py        # 3 separated metrics, each must pass
```

Optional adapters: `adapters/inspect_adapter.py`, `adapters/pydantic_adapter.py`.

## What this is NOT

Not a benchmark, not an agent runner, not an accuracy metric. See SPEC §7: the three
conformance metrics (integration / spec / policy) must never be merged into one number.

License: Apache-2.0 (see NOTICE). Conformance cases are original data.
