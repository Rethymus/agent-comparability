# Changelog

## Unreleased

- None yet.

## v0.5.2 (2026-10-26)
- PyPI distribution debut (E phase): first published version is 0.5.2 via
  Trusted Publishing — dedicated publish-pypi.yml workflow (manual
  workflow_dispatch only, GitHub Environment `pypi`, OIDC short-lived
  credentials, no long-lived PyPI tokens), builds verified from the fixed
  release tag (version gate + twine check + package content gate before upload)
- Install docs now PyPI-primary (EN+zh): canonical `pip install
  agent-comparability` plus quoted extras forms; clone/`-e` kept for
  development; project-status distribution row updated (was "not yet on PyPI")
- Docs gate upgraded from "block every non-`-e` pip install" to an exact
  allowlist of the six canonical commands (fabricated package names still
  blocked — N4 semantics preserved, anchor updated); bilingual presence of the
  PyPI primary command now enforced
- No functional, test-semantics, or specification changes; specification
  remains cmp/0.3.1; v0.5.0/v0.5.1 tags untouched

## v0.5.1 (2026-10-26)
- (#12) Adapters are independently runnable in any order (external review finding):
  pydantic_adapter self-initializes conformance-results.json when missing (was
  FileNotFoundError on a clean checkout if run standalone); inspect_adapter now
  merges into the existing file instead of wholesale overwrite (previously
  silently dropped route2b when run after pydantic); regression N7 covers
  standalone clean-env run + both-order section preservation
- (#10) Pydantic route verdict hardening (external review finding): evaluators now
  check the task's REAL output (`ctx.output`) against frozen expectations instead
  of re-adjudicating inside the evaluator (false-consistency risk — a re-computing
  evaluator cannot prove the task output correct); applies to both run_suite's
  CDRParity and the adapter's CDRAdjudicator (which now receives the full CDR)
- (#10) Adapter exit code now derives from the full 22-pair report
  (report.cases + report.failures + coverage gate: reported == input count)
  instead of a legacy A-set re-adjudication loop; run_suite now reuses
  cases.all_pairs() directly (single loader, duplicate run_all_cases removed)
- (#10) New permanent negative regressions N5/N6: wrong task output must score
  0 (both evaluators, with positive control) and must propagate to adapter
  non-zero exit with all 22 pairs still reported
- (#8) Install docs now distinguish minimal core / suite basics / FULL conformance
  install (.[suite,inspect,pydantic]) — matching run_suite's adapter-required policy;
  §10 notes missing-adapter→FAIL behavior (EN+zh)
- (#8) Integration metric parity: shared case loader (conformance/cases.py, A+B 22
  pairs) used by both routes; run_suite reports Inspect and Pydantic separately
  (executed/passed/rows/error), textual placeholder removed; pydantic_adapter now
  covers the full 22 pairs; dual-route not-executed gate negative-verified
- README round 2: full real CDR JSON example (§8), mermaid adjudication
  flowchart (§9, GitHub-native render), admissibility quick-reference table (§3),
  tool-positioning table + audience line (§1), FAQ (6 Q&As), Project-status
  matrix; all mirrored in 简体中文 with field-level CDR parity audit
- Full README revamp modeled on popular OSS patterns (surveyed: ohmyzsh collapsible
  ToC + admonitions, vue-element-admin header/switcher, doocs/leetcode cross-link):
  real badge row (GitHub Actions CI / Apache-2.0 / Python 3.10+ — no fabricated
  metrics badges), collapsible table of contents, GitHub alert admonitions for
  the not-a-certification disclaimer, failure-mode table in Problem section,
  30-second quick path; fully mirrored in 简体中文 (information-equivalent)
- README language switcher redesigned after surveying popular bilingual OSS repos
  (pattern adopted from vue-element-admin): moved below the centered title block,
  active language rendered bold non-link, other language linked; check_docs now
  enforces the pattern (position, active/inactive roles, centered block)

## Post-publication validation fixes (2026-10-26)
- P0: README clone commands now use the real repo URL (EN + 简体中文)
- P0: run_suite treats integration metric NOT-EXECUTED (deps missing/adapter
  exception) as FAIL with non-zero exit (same defect family as N2); CI now
  installs [suite,inspect,pydantic] and runs both adapters explicitly
- P1: docs/tests use spec-canonical `score_comparison`; SPEC documents the
  frozen A-set legacy alias `score_compare`
- check_docs: EN-README Chinese-fragment policy (real output is Chinese →
  localization note required) + bilingual key-token parity

All versions immutable once tagged. v0.3.1–v0.3.6 are **deprecated candidates**
kept for the record (each superseded for a verified defect; see git history notes).

## v0.5.0 (2026-10-25)
- **Version identity unified**: tag v0.5.0 == pyproject == `__version__` == package
  metadata (v0.4.1 carried 0.4.0 inside — recorded as historical candidate defect,
  tag untouched). New `conformance/release_gate.py` enforces this on every CI run.
- Negative gates N1–N4 converted to permanent regression tests
  (`tests/test_gate_regressions.py`, original failure record preserved in VALIDATION.md
  and fix commits ad14fb5/541494d). Terminal scan gained an AST-based structured
  companion (N1b) instead of expanding string rules; documented self-exclusions.

## v0.4.1 (2026-10-25)
- Gate fixes proven by negative tests: terminal-scan pattern widened (`from cmp.core`
evaded trailing-space match), run_suite exit-code now propagates failures (was
always 0 — CI stayed green on failed verdicts)

## v0.4.0 (2026-10-25)
- Repository hardening: build artifacts untracked, process reports archived to
  `docs/internal/`, redundant QUICKSTART merged into README
- Full bilingual README (English + 简体中文, information-equivalent) with real
  verified examples; package version aligned (was 0.3.6 while tag was v0.3.7)
- Governance: CHANGELOG, PR/Issue templates, support policy, Dependabot config
- CI: main-branch triggers, YAML/package-content/doc-link checks added;
  negative gate test added
- Spec unchanged: `cmp/0.3.1`

## v0.3.7 — first remotely CI-verified candidate
- Fixed workflow YAML defect found by real GitHub Actions (heredoc → script);
  terminal scan became shared CI+local gate; pinned action SHAs; build+twine step

## v0.3.6 — deprecated (CI workflow syntax error)
## v0.3.5 — deprecated (wheel/sdist missing spec+cases; version misalignment)
## v0.3.4 — deprecated (comment-level residual import)
## v0.3.3 — deprecated (adapter path residues)
## v0.3.2 — deprecated (unasserted replacements silently skipped)
## v0.3.1 — deprecated (snapshot suite non-runnable; LICENSE present)
