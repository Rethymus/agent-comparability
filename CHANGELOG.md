# Changelog

## Unreleased
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
