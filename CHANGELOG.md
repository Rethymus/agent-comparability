# Changelog

## Unreleased

- Examples now cover all four verdicts: new `examples/demo-inadmissible.json` (model+harness
  confounded → INADMISSIBLE), `examples/demo-partial.json` (a verified 0 meets an
  unresolved_zero 0 → PARTIAL, stratified-only) and `examples/demo-inconclusive.json`
  (trajectory_available=false → INCONCLUSIVE, source reward retained verbatim). Each file
  embeds a `_comment` marking SYNTHETIC/ILLUSTRATIVE + the expected verdict, in the style of
  `examples/demo-case.json`. docs/usage-examples.md Journey 1 (旅程 1, CN+EN) now maps all four
  verdicts to copy-paste commands and explains each "why" with excerpts from actual run output
  (violated/supported/unsupported_claims), replacing the previous hypothetical mutation
  bullets. Docs/examples layer only — no src/ changes
- CDR consumer-loop closure: new `python -m agent_comparability.validate cdr.json`
  (consumer-side validator — check a CDR received from someone else before trusting it;
  pure stdlib, zero extra dependencies, independently runnable). Three-state exit
  contract: 0 = structurally valid and policy_version recognizable (cmp/0.3.x or
  cmp/0.4.x — old CDRs stay valid); 1 = structurally valid but unrecognized version —
  per SPEC §5 the diagnostic instructs 必须丢弃该 CDR 并重新判定，不得部分信任 (discard
  and re-adjudicate; no partial trust, not even admissibility); 2 = structure/schema
  violation with field- and index-precise diagnostics (e.g. limitations[0],
  admissibility, supported_claims[1]). The required-field list is read at runtime from
  the packaged data/cdr.schema.json (single source of truth); the admissibility
  four-value enum, the policy_version regex and the limitations tamper contains-rule
  (抗恶意篡改|tamper) are hand-mirrored with sync-source comments; structural violations
  dominate version recognition (a broken CDR never lands in the exit-1 branch).
  tests/test_validate.py: 22 cases written negative-first (module absent → 22 failed),
  incl. the pipeline identity (adjudicate output passes our own validator), a
  runtime-schema injection proving required is not hardcoded, and all three exit paths.
  docs/usage-examples.md gains Journey 5 (bilingual); README §7 (EN+zh) gains the
  consumer-validation sentence. CHANGELOG attribution fix: the #38 multilog diagnostic
  fix split out of the (#36) entry into its own bullet (see v0.5.5 section)

## v0.5.5 (2026-10-27)
- (#38) Multilog MappingError diagnostic fix — standalone entry (split out of the
  (#36) test-hardening bullet after the audit flagged imprecise attribution: a src/
  fix was folded into a tests-only entry): when `records_from_summaries` raises
  MappingError in the per-log loop, the diagnostic now names the source log
  (`error: 日志 <path>: <原消息>`) so multi-log operators can tell which log failed;
  exit-2 contract and the original message content unchanged. The unmapped-letter-score
  test (introduced by #36) now asserts the three-element locator in stderr: failing
  log path + sample id + unmapped value
- (#39) CI: weekly schedule trigger (`cron "3 3 * * 1"`, Mondays 03:03 UTC) so
  upstream breakage (e.g. inspect-ai API changes) is caught without anyone
  pushing; new independent non-required job `compat-py310` (Python 3.10)
  empirically verifies the `requires-python = ">=3.10"` claim — on 3.10 pip
  resolves older inspect-ai/pydantic-evals (upstream now needs ≥3.11), and the
  job proved those older versions work: run_suite 26/26 on all three metrics
  and 512 tests passed on Python 3.10.22 (first CI run, evidence recorded in
  PR #39). Required job name `conformance` untouched
- (#36) Test hardening, no src/ or frozen-case changes (the multilog diagnostic fix
  that had been folded into this entry now lives in its own (#38) bullet above):
  new `tests/test_properties_04.py` randomized generalizations of the frozen
  cmp/0.4.0 D-set (model-only symmetry stays ADMISSIBLE with same_model as honest
  info item; model+harness confound INADMISSIBLE; causal rejected; missing-trace
  INCONCLUSIVE dominates; scale gate not relaxed); `tests/test_inspect_log.py`
  multilog boundaries (epochs=2 log + single-sample log merge with per-log
  repetition_count and faithful per-record artifact refs; unmapped letter score in
  the second log exits 2)
- (#37) `docs/usage-examples.md`: four real user journeys with copy-paste
  commands and verdict shapes — offline JSON → CDR with the exit-code contract;
  --manifest three-state semantics + verify_manifest() audit reuse; single
  Inspect log with the explicit mapping policy; cross-log comparison with
  shared --task-label (pooling refused, model-only ADMISSIBLE under cmp/0.4.0).
  README.md / README.zh-CN.md §7 link to it in both languages
- (#35) README badge style discipline: the three shields.io badges now carry
  `style=flat-square` (readme-anatomy dogfood round 1; mechanical fix, zero
  prose changes, both language files kept in lockstep)

## v0.5.4 (2026-10-27)
- Ships specification **cmp/0.4.0** (PR #33, #27 direction B — single-variable
  symmetry: model-only score_comparison is now ADMISSIBLE side-by-side, guarded
  independently by score-scale and zero-semantics conditions). First PyPI release
  carrying 0.4 semantics; CDRs carry policy_version cmp/0.4.0 (schema accepts both
  0.3.x and 0.4.x — old records stay valid). Frozen D-set (D1/D2) anchors the new
  branches; all 22 legacy pairs verified unchanged. #27 remains open for explicit
  owner confirmation; the change is fully revertible
- (#27, direction B) Specification cmp/0.3.1 -> **cmp/0.4.0** (minor per SPEC §5:
  adjudication-table branch change): score_comparison no longer treats a
  same_model violation as an independent INADMISSIBLE trigger — single-variable
  symmetry per §4 row 2 (model-only variation is now ADMISSIBLE side-by-side),
  while score_scale_consistent / zero_semantics_uniform keep guarding
  independently. Executed per the owner's standing strict-execution directive
  after the evaluation memo recommended B; fully revertible in-repo; issue
  stays open until explicit owner confirmation
  - Frozen D-set added BEFORE implementation (conformance/cases-0.4.json,
    following the B5 precedent — old A/B expectations untouched): D1
    model-only -> ADMISSIBLE (+causal still INADMISSIBLE), D2 model+undeclared
    out-of-range scale -> INADMISSIBLE (proves scale guarding is NOT relaxed);
    all 22 pre-existing frozen pairs verified unchanged under 0.4 semantics
    (negative-repro first: D1 failed on metric3/metric2/metric1-pydantic)
  - core.py + conformance/independent_impl.py mirrored; cdr.schema.json
    policy_version pattern now accepts cmp/0.3.x and cmp/0.4.x (old CDRs stay
    schema-valid); release_gate anchor updated; bilingual README/docs version
    mentions synced; multi-log diff-model acceptance flipped with provenance

## v0.5.3 (2026-10-27)
- (#26) Multi-log comparison entry: `inspect_log A.eval B.eval …` merges logs under a
  shared explicit --task-label into one case/CDR/manifest; per-log harness labels via
  comma-separated --harness-name (count-validated; never fabricated); cross-log scorer
  must agree (mixed scorers → exit 2); per-record artifact_ref + digest per source log;
  pooling multi-sample logs is correctly refused (same_task_id violated) with an explicit
  multi_task_merge warning; single-log CLI contract unchanged. Real-log acceptance:
  two-run single-sample ADMISSIBLE, whole-log pooling refused, sample-id mismatch
  refused, count-mismatch/unreadable-log exit 2
- (#27) Spec ambiguity REPORTED (no spec/frozen changes): §3.3-2 (same_model violation →
  INADMISSIBLE, labeled the normative decision table) conflicts with §4 row 2
  (model-only variation → ADMISSIBLE); surfaced by real two-model logs; both
  implementations follow §3.3, behavior locked in tests pending adjudication
- (#28) Real multi-epoch (epochs=2) acceptance: repetition_count=2 derived from real
  log data; --full-read now correctly matches sample ids (str-key fix) and sets
  trajectory_available from actual observation (messages/events); summary-read still
  declares nothing
- Maintenance: `[project.urls]` added to pyproject (Homepage/Repository/Issues/Changelog —
  PyPI project page now links back to GitHub once included in a future release);
  PyPI version badge added to both READMEs (package is published since 0.5.2)
- (#22) Real-pipeline comparative experiment 001 (`experiments/scenarios_001/`):
  four scenarios through the actual pipeline (real .eval produced in-test via
  mockllm -> #20 converter -> #16 CLI -> core), covering all four verdicts —
  same-task/same-model/diff-harness ADMISSIBLE; diff-model+diff-harness
  INADMISSIBLE (correct refusal, causal also refused); verified-vs-unresolved
  zero PARTIAL (stratified, pooled refused); trajectory-missing INCONCLUSIVE
  (transcription retained). Expected outcomes anchored to the SPEC §3.3/§4
  frozen tables AND cross-checked by independent_impl — full agreement, no
  spec ambiguity found. RECORD.md documents the 8 required fields per scenario
  with honest labeling (real logs are mock-model artifacts, not real benchmark
  evidence; manual-json records are synthetic); permanent regression test
  negative-first (module absent -> 3 failed). Explicit evidence gaps recorded:
  no third-party-harness data, no non-mock model logs
- (#20) Inspect AI EvalLog converter (`python -m agent_comparability.inspect_log`):
  converts actually-produced .eval logs into cmp records -> CDR + Evidence
  Manifest via official APIs only (read_eval_log / sample summaries; --full-read
  for trajectories). Explicit mapping policy — no silent guessing:
  reward_status requires an operator --status assertion (logs carry no
  verification tier); non-numeric scores (exact's C/I) require an explicit
  --score-map; task identity prefers explicit --task-label over dataset.name
  over the run-scoped hash; trajectory_available unset under summary read
  (never claim unobserved facts), set from observation under --full-read;
  score_scale never set; error samples skipped and counted, never fabricated.
  Per-sample record granularity (aggregation rejected as a semantic guess);
  comparing different samples in one log correctly yields INADMISSIBLE.
  Manifest integration (§3): per-record sha256 of the .eval artifact, all
  mapping decisions as warnings, verification_tier_absent_in_source declared.
  Acceptance uses a REAL log produced in-test by running inspect eval with
  mockllm/model (zero API calls); 10-path suite negative-first
  (module absent -> all failed), incl. missing-dependency clean exit-2 path
- (#18) Evidence Manifest (`evidence/0.1`, CDR-external): artifact-level trust
  states source_claimed < artifact_observed < independently_verified with strict
  no-auto-upgrade rules — artifact_observed only after the artifact file is
  actually read and its sha256 computed; independently_verified only with an
  explicit method/operator/at entry on top of an observed artifact;
  verification-without-artifact is flagged inconsistent, never an upgrade.
  Deliberately orthogonal to SPEC §1 record-level tiers: never enters
  adjudicate(), zero SPEC/schema changes. CLI gains --manifest (honest offline
  default: input file as artifact, all records artifact_observed, no
  independent-verification claims); verify_manifest() recomputes digests for
  audit; bilingual contract doc docs/evidence-manifest.md; 9-path test suite
  negative-first (rules module absent → collection failure), incl. tamper
  detection via digest recompute
- (#16) Offline JSON → CDR CLI closure (`python -m agent_comparability input.json
  --claim <type> [-o out.json]`): zero extra runtime dependencies (stdlib argparse
  + json), reuses adjudicate() with no judgment-semantics changes; exit-code
  contract 0 = CDR produced (all four admissibility values are verdicts, not
  failures) / 2 = invalid input with path-precise diagnostics (never silently
  converted into a verdict); unknown record fields stay SPEC §5 behavior (ignored
  + recorded); contract validation covers structure/types only; bilingual usage
  docs + SYNTHETIC-labeled demo case in examples/; 20-path test suite written
  first as negative repro (all failed pre-implementation), clean-copy execution
  recorded in the PR

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
  (`tests/test_gate_regressions.py`, original failure record preserved in
  docs/internal/VALIDATION.md
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
