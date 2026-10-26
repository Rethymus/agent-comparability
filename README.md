<div align="center">

# Agent Comparability

**Experimental Specification & Conformance Suite** for AI agent evaluation comparability

[![CI](https://github.com/Rethymus/agent-comparability/actions/workflows/ci.yml/badge.svg)](https://github.com/Rethymus/agent-comparability/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)

**English** | [简体中文](README.zh-CN.md)

*When can you compare AI agent evaluation results — and what claims do they support?*

</div>

---

> [!IMPORTANT]
> This project adjudicates **comparability of evaluation records** — it does **not** run
> agents, score benchmarks, or certify any agent's reliability. Passing the conformance
> suite means *specification* conformance, nothing more.

**The 30-second path**: [Install](#6-installation) → [Quickstart](#7-quickstart) →
[Real input/output](#8-inputoutput-example-actual-output).

<details open>
<summary><b>Table of Contents</b></summary>

1. [Project Overview](#1-project-overview)
2. [Problem & Motivation](#2-problem--motivation)
3. [What Agent Comparability Does](#3-what-agent-comparability-does)
4. [What It Does Not Do](#4-what-it-does-not-do)
5. [Main Features](#5-main-features)
6. [Installation](#6-installation)
7. [Quickstart](#7-quickstart)
8. [Input/Output Example (actual output)](#8-inputoutput-example-actual-output)
9. [Architecture](#9-architecture)
10. [Conformance Suite](#10-conformance-suite)
11. [Inspect AI / Pydantic Evals Integrations](#11-inspect-ai--pydantic-evals-integrations)
12. [Specification & Versioning](#12-specification--versioning)
13. [Limitations](#13-limitations)
14. [Contributing](#14-contributing)
15. [Security](#15-security)
16. [License & Acknowledgements](#16-license--acknowledgements)

</details>

---

## 1. Project Overview

Agent Comparability is a framework-independent **specification** ([spec/SPEC.md](spec/SPEC.md)),
a frozen **conformance suite**, and a thin **reference implementation** that adjudicates
*comparability* of agent evaluation records — never the scores themselves.

## 2. Problem & Motivation

Three failure modes silently corrupt agent-evaluation conclusions:

| Failure mode | What actually goes wrong |
|---|---|
| **Semantics mixing** | A *verified failure* and an *unresolved zero* both read `0.0` — pooled "fail rates" become meaningless |
| **Confounded variables** | Model and harness change at the same time — a two-variable diff gets reported as causation |
| **Evidence gaps** | Missing traces quietly inflate success rates; rankings reverse across harnesses |

These boundaries should be **machine-checkable**, not vibes. That is what this project ships.

## 3. What Agent Comparability Does

- Adjudicates a **Requested Claim** (e.g. `score_comparison`, `causal`,
  `descriptive_registration`) against a set of evaluation records
- Returns a **Comparison Decision Record (CDR)**: admissibility
  (`ADMISSIBLE / INADMISSIBLE / PARTIAL / INCONCLUSIVE`), satisfied/violated/unknown
  conditions, **supported claims AND forbidden claims**, evidence refs, policy version
- Enforces evidence-trust tiers (agent-claimed vs source-verifier vs independently
  verified), score-scale consistency (range/unit/verifier), zero-semantics splits,
  and unknown-field/unknown-claim rules
- Ships a frozen conformance suite run against three separated metrics

## 4. What It Does Not Do

> [!WARNING]
> - Does **not** run agents, benchmarks, or models; no network, no credentials, no Docker
> - Does **not** score anything or certify any agent's reliability
> - Never merges its three conformance metrics into one number (see [§10](#10-conformance-suite))

## 5. Main Features

- `adjudicate(records, requested_claim) -> CDR` — pure Python, zero dependencies
- Priority-ordered decision table (evidence-missing > confounded > semantics > admissible)
- Machine-verifiable CDR JSON Schema ([spec/cdr.schema.json](spec/cdr.schema.json))
- Frozen A/B conformance case sets; B5 public erratum precedent protected
- Optional adapters for Inspect AI and Pydantic Evals reusing the same core

## 6. Installation

From a clone (not yet on PyPI):

```bash
git clone https://github.com/Rethymus/agent-comparability.git && cd agent-comparability
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
    "score_comparison")
```

## 8. Input/Output Example (actual output)

> Note: the reference implementation's condition/claim messages are currently in Chinese; the admissibility verdict itself is locale-neutral.

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
    "score_comparison")
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

Three distinct lines: software tag (e.g. `v0.5.0`), specification `cmp/0.3.1`
(inside SPEC), and `agent_comparability.__version__`. Judgment-table changes
require a spec major bump (SPEC §5). See [CHANGELOG](CHANGELOG.md) for the full tag lineage
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
