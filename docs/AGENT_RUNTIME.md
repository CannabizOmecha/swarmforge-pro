# Typed Expert Runtime

## Scope
The current runtime is a deterministic adapter harness for local synthetic fixtures. It is not a live LLM integration. It establishes the contracts and security boundaries that a future model-backed adapter must satisfy.

## Task routing
The caller submits a task type, not an expert name or capability grant. Static routing assigns:
- `inspect_fixture` → `test_generator`
- `validate_fixture` → `security_validator`
- `critique_candidate` → `critic`

All request and response models reject unknown top-level fields. Each task payload has a task-specific schema. Only two fixed fixture identifiers are available to the inspection task; validation is limited to the synthetic authorization-denial fixture.

## Capabilities
| Expert | Granted capability |
|---|---|
| test_generator | read_synthetic_fixture |
| security_validator | read_synthetic_fixture, validate_synthetic_assertion |
| critic | review_candidate |

The toolbox exposes no generic shell, filesystem, network, database, credential, or arbitrary URL operations. A capability must be present in the expert's static grant before a tool method can execute. Capability use is recorded in the result.

## Resource limits
- Per-task deadline: 10–2,000 ms.
- Input payload: maximum 8 KiB after task-specific validation and canonical serialization.
- Output payload: caller-selected 128 B–8 KiB.
- One adapter attempt per task; no automatic retry loop.
- Timeout and adapter failure produce an abstention with a sanitized reason.
- Invalid result schema, capability escalation, non-finite JSON, or output-budget violation fails the task contract.

The deadline is cooperative asynchronous cancellation via `asyncio.wait_for`. It is not a hard operating-system CPU or memory quota. A future untrusted model/tool worker must run in a separately constrained process or container.

## Three-stage pipeline
`POST /agent-pipelines/validate` executes sequentially:
1. **test_generator** reads the fixed fixture and returns the expected decision.
2. **security_validator** independently compares the observed decision with the fixture invariant.
3. **critic** checks the candidate structure, local scope, and SHA-256 digest of the canonical candidate.

The pipeline stops if a stage abstains or is rejected. The validator and critic are distinct adapters with different capability grants. The critic does not receive permission to validate the security invariant; the validator does not receive the critic's candidate-review capability.

The pipeline is an in-memory demonstration. Its candidate digest is not an evidence record. It does not persist a finding, evidence bundle, or workflow checkpoint. The normal `POST /runs` path remains the persistent synthetic assurance workflow.

## Future live-model adapter gates
Before connecting a provider:
- define a versioned provider/model identity and prompt template;
- validate provider outputs against the same strict response schema;
- keep authorization and policy decisions outside model control;
- use explicit per-provider cost/token budgets and circuit breakers;
- isolate model tools behind capability-scoped broker APIs;
- treat prompts, model output, tool output, and telemetry as untrusted;
- test prompt injection, malformed output, timeout, retry, refusal, and data leakage;
- run held-out benchmark evaluation and calibration before promotion;
- record provenance and preserve deterministic fallback behavior;
- do not provision credentials or incur paid usage without separate authorization.

No provider credentials or live model connections are present in this repository.
