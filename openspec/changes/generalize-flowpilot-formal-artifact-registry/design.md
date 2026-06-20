## Context

FlowPilot already validates many runtime files and logical artifact ids. This
change is narrower: it covers AI-submitted, file-backed formal artifacts that
runtime expects in addition to the result body. Runtime-owned internal files
such as ledgers, packet envelopes, route snapshots, and generated indexes are
not AI-submitted formal artifacts and must not become role obligations through
this registry.

The current concrete registered artifact is the FlowGuard formal evidence file
`flowguard_evidence.json`, written under the packet-owned
`evidence_output_policy.run_local_evidence_root`. Logical artifacts such as
`subject_packet:<id>` or `target_result:<id>` are not filesystem attachments;
they are consumed through `subject_artifacts_consumed`.

## Goals / Non-Goals

**Goals:**

- Make a single registry the source for runtime-known AI-submitted formal file
  artifacts.
- Make fake-AI and ContractExhaustionMesh derive formal-artifact cells from the
  registry.
- Prove every registered artifact has missing-file, wrong-path, invalid-JSON,
  missing-field, wrong-value, body-conflict, retry, and fifth-attempt
  BreakGlass coverage when applicable.
- Keep subject artifact id consumption explicit but separate from file-backed
  artifact validation.

**Non-Goals:**

- Do not treat all runtime persistence files as AI-submitted attachments.
- Do not accept old paths, historical files, body-only substitutes, aliases, or
  compatibility shims.
- Do not add a new packet family, new role, or parallel artifact ledger.

## Decisions

### Decision: Registry before coverage claim

The registry lists only file-backed formal artifacts that runtime can require
from an AI result. Coverage tests read this registry and assert that each
registered artifact has corresponding fake-AI cells and ContractExhaustionMesh
cells. This makes future new artifacts fail closed until they add coverage.

### Decision: Logical artifact ids are not file-backed formal artifacts

Runtime may require `subject_artifacts_consumed` to mention ids such as
`subject_packet:<id>`. Those ids prove the AI considered a current artifact,
but they are not files the AI must write. They stay in result-body validation,
not the formal file registry.

### Decision: Keep current FlowGuard runtime path as the first registry row

The existing FlowGuard file validation remains the concrete runtime path. The
hard-coded constants are narrowed to values loaded from the registry, so future
registered artifacts cannot drift from the test matrix.

## Risks / Trade-offs

- Registry overreach could make roles responsible for runtime-owned files ->
  mitigate by adding tests that logical subject artifacts and internal ledgers
  are excluded from the file-backed formal artifact registry.
- Registry underreach could preserve hidden artifact requirements -> mitigate
  with code tests that every registered artifact is covered and direct string
  constants in runtime derive from the registry row.
- Future generic file-backed artifacts may need a non-FlowGuard validator ->
  add a new registry row and explicit validator owner then; do not pre-create a
  broad fallback validator now.
