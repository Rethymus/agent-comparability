[English](README.md) | [简体中文](README.zh-CN.md)

# Agent Comparability — Experimental Specification & Conformance Suite

**When can you compare AI agent evaluation results — and what claims do they support?**

## 1. Project Overview

Agent Comparability is a framework-independent **specification** (`spec/SPEC.md`),
a frozen **conformance suite**, and a thin **reference implementation** that
adjudicates *comparability* of agent evaluation records — never the scores themselves.

## 2. Problem & Motivation

Agent rankings reverse across harnesses; scores mix semantics (a *verified failure*
and an *unresolved zero* both read `0.0`); missing traces silently inflate success
rates; two variables change at once and someone claims causation. Before comparing
results you need to know **what the evidence supports** — machine-checkably.

## 3. What It Does

- Adjudicates a **Requested Claim** (e.g. `score_compare`, `causal`,
  `descriptive_registration`) against a set of evaluation records
- Returns a **Comparison Decision Record (CDR)**: admissibility
  (`ADMISSIBLE / INADMISSIBLE / PARTIAL / INCONCLUSIVE`), satisfied/violated/unknown
  conditions, **supported claims AND forbidden claims**, evidence refs, policy version
- Enforces evidence-trust tiers (agent-claimed vs source-verifier vs independently
  verified), score-scale consistency (range/unit/verifier), zero-semantics splits,
  and unknown-field/unknown-claim rules
- Ships a frozen conformance suite run against three separated metrics

## 4. What It Does NOT Do

- Does **not** run agents, benchmarks, or models; no network, no credentials
- Does **not** score anything or certify any agent's reliability — conformance
  passing is *specification* conformance, not a reliability rating
- Does not merge its three metrics into one number (see §10)

## 5. Main Features

- `adjudicate(records, requested_claim) -> CDR` — pure Python, zero dependencies
- Priority-ordered decision table (evidence-missing > confounded > semantics > admissible)
- Machine-verifiable CDR JSON Schema (`spec/cdr.schema.json`)
- Frozen A/B conformance case sets; B5 public erratum precedent protected
- Optional adapters for Inspect AI and Pydantic Evals reusing the same core

## 6. Installation

From a clone (not yet on PyPI):

```bash
git clone <this-repo> agent-comparability && cd agent-comparability
pip install -e .            # core, zero deps
pip install -e .[suite]     # + conformance suite (pyyaml, jsonschema)
```

Requires Python ≥ 3.10. No Docker, no model keys.

## 7. Quickstart

```python
from agent_comparability import adjudicate

cdr = adjudicate({"id": "demo", "records": [
    {"task_id": "t1", "harness": "h1", "model": "m1",
     "reward": 1.0, "reward_status": "verified"},
    {"task_id": "t1", "harness": "h2", "model": "m1",
     "reward": 0.0, "reward_status": "unresolved_zero"}]},
    "score_compare")
```

## 8. Input/Output Example (actual output)

The quickstart call returns:

```
cdr.admissibility      -> PARTIAL
cdr.supported_claims   -> ['per_status_stratified_rate(verified_zero/unresolved_zero 分列)']
```

A confounded group instead:

```python
cdr = adjudicate({"id": "x", "records": [
    {"task_id": "a", "harness": "h1", "model": "m1", "reward": 1.0, "reward_status": "verified"},
    {"task_id": "b", "harness": "h2", "model": "m2", "reward": 0.0, "reward_status": "verified"}]},
    "score_compare")
```

```
cdr.admissibility       -> INADMISSIBLE
cdr.violated_conditions -> ['same_task_id', 'same_model', 'single_variable_isolation']
```

`cdr.to_dict()` emits the full CDR (schema-validated).

## 9. Architecture

```
spec/SPEC.md                     ← single source of truth (readable standalone)
spec/cdr.schema.json             ← machine-verifiable CDR
src/agent_comparability/core.py  ← thin reference implementation
src/agent_comparability/data/    ← SPEC + schema + frozen cases (packaged)
conformance/                     ← run_suite.py (3 metrics) + independent_impl.py + cases
adapters/                        ← optional inspect-ai / pydantic-evals wrappers
tests/                           ← smoke + property tests
```

## 10. Conformance Suite

`python conformance/run_suite.py` reports three **separated** metrics that must
never be merged:

1. **Policy correctness** — reference implementation vs frozen expectations
2. **Spec conformance** — an independent implementation written from SPEC alone
3. **Integration consistency** — the same core via Inspect/Pydantic adapters

A failure in each means a different defect class (implementation bug / spec
ambiguity or misread / adapter bug).

## 11. Inspect AI / Pydantic Evals Integrations

```bash
pip install -e .[inspect] && python adapters/inspect_adapter.py
pip install -e .[pydantic] && python adapters/pydantic_adapter.py
```

Both wrap the *same* core (no semantic duplication). Inspect scorer uses
`metrics=[]` — admissibility is deliberately **not** aggregated into accuracy.

## 12. Specification & Versioning

Three distinct lines: software tag (e.g. `v0.4.0`), specification `cmp/0.3.1`
(inside SPEC), and `agent_comparability.__version__`. Judgment-table changes
require a spec major bump (SPEC §5). See CHANGELOG for the full tag lineage
(v0.3.1–v0.3.6 are deprecated candidates kept immutably for the record).

## 13. Limitations

- Experimental specification; self-tested conformance, **no external certification**
- Single-writer trust domain: digest equality proves non-divergence, not
  tamper-resistance (SPEC §1)
- No repetition/cost modeling inside adjudication (handled by callers)
- Chinese/English docs kept equivalent; translation drift tracked in CI link checks

## 14. Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Key rule: **never edit frozen expectations
to make tests pass**; errata follow the public B5 precedent. PRs must pass all
three conformance metrics separately.

## 15. Security

See [SECURITY.md](SECURITY.md). Private vulnerability reporting preferred.

## 16. License & Acknowledgements

Apache-2.0 (see [LICENSE](LICENSE), [NOTICE](NOTICE)). Optional integrations
inspect-ai / pydantic-evals are MIT and **not bundled**. Conformance case data is
original to this project; no CC BY-NC data is distributed. Research lineage:
this repo was distilled from a private research repository; internal process
records live under `docs/internal/`.
