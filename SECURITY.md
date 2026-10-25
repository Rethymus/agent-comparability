# Security

- Report vulnerabilities via GitHub private vulnerability reporting (preferred) or
  an issue marked [SECURITY] without exploit details; maintainers will coordinate.
- Scope: pure-Python adjudication logic; no network, no eval execution, no secrets
  handling. Supply-chain surface = pyyaml/jsonschema (suite) and optional
  inspect-ai/pydantic-evals.
- Threat model (in-spec): digest equality proves non-divergence only, NOT
  tamper-resistance (single-writer trust domain) — see SPEC §1.
