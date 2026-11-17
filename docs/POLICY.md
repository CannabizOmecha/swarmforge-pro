# Governance Policy

## Authoritative runtime boundary
The FastAPI application enforces authorization through the immutable Python scope registry in aegis/policy.py. The registry contains exactly one scope: local-synthetic. Startup validation rejects additional scopes, network-enabled scopes, unsupported operations, and out-of-range batch budgets.

## Rego policy
- Policy identifier: aegis.authorization
- Policy version: 1.0.0
- Rego language: v1
- OPA CLI: 1.22.4
- Source: policy/aegis.rego
- SHA-256: 50a42b6d44bd45eb53285c846cd388e9693b146611f1fabbcc63afc4c9204759
- Manifest: spec/policy-manifest.json

The policy allows only the exact four-field authorization input for local-synthetic, approved operations, batch sizes 1–200, and network_enabled=false. Extra fields are denied.

## Verification
CI downloads the official OPA static Linux binary, verifies its SHA-256 asset digest before execution, runs OPA formatting and compilation checks, and executes positive/negative Rego tests. A separate script verifies the Rego source hash, the Python/Rego policy version agreement, and the fixed scope registry.

OPA is not yet invoked by the API at runtime. Python remains the runtime enforcement layer; OPA is an independently tested policy artifact. A future runtime integration must fail closed and preserve Python enforcement as a second boundary until parity and failure semantics are independently validated.
