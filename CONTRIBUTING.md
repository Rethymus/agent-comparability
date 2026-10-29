# Contributing

- Spec changes: edit `spec/SPEC.md`; semver per §5 (judgment-table changes require major bump).
- Implementation PRs must pass all three conformance metrics separately (`python conformance/run_suite.py`).
- NEVER edit frozen expectations to make tests pass. Errata require a public entry
  (see conformance/boundary-cases.json B5 erratum precedent) and only when a newer
  expectation contradicts an older frozen set.
- New boundary cases welcome: freeze expectations BEFORE running implementations.
- AI contributors and coding agents: see [AGENTS.md](AGENTS.md) for the binding
  rules (instruction-source priority, closed check list, citation and data discipline).

## Security & disclosure

See SECURITY.md. No credentials in issues; private details via private vulnerability reporting.
