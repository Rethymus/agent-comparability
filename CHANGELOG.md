# Changelog

All versions immutable once tagged. v0.3.1–v0.3.6 are **deprecated candidates**
kept for the record (each superseded for a verified defect; see git history notes).

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
