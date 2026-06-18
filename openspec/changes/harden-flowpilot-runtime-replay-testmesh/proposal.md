## Why

FlowPilot now has broad fake-AI and Cartesian matrix coverage, but part of that
evidence still proves that bad cases can be generated rather than proving that
the runtime actually absorbs them end to end. Recent real-run issues show the
next hardening step must turn generated fake-AI cells into executable runtime
replay evidence for review windows, singleton live evidence, repair reissues,
and same-family break-glass thresholds.

## What Changes

- Add a hard orphan-review-flow gate: every runtime-issued Reviewer packet must
  bind to a declared structured `review_window` row, and missing/orphan/mismatched
  review windows must fail before a packet can be counted as covered.
- Add singleton live-evidence completeness tests covering every combination of
  the five required live evidence files: all present and valid can be `full`,
  while any missing or invalid file remains `evidence_insufficient`.
- Extend fake-AI testing from payload generation into executable runtime replay:
  submit bad output, observe precise runtime rejection, reissue or repair,
  submit corrected second output, and verify fifth same-family failure routes to
  break-glass through the existing threshold.
- Add a real-issue backfeed registry so every newly observed real-run anomaly
  must become a fake-AI profile, contract cell, Cartesian row, and runtime
  reaction replay before the issue can be closed.
- Register the new replay evidence through the existing ContractExhaustionMesh,
  TestMesh, Model-Test Alignment, topology, install-sync, and version gates
  instead of creating a parallel test framework.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `formal-gate-review-standards`: Reviewer packets must be unissued or blocked
  when their structured review flow is missing, orphaned, mismatched, or
  prose-only.
- `parallel-flow-block-authority`: singleton live evidence must distinguish
  complete live authority evidence from any missing or invalid current-run
  authority file.
- `synthetic-agent-coverage-matrix`: fake-AI cells must declare whether they
  are generated-only or runtime-replayed, and broad coverage must require replay
  evidence for the selected high-risk cells.
- `multiround-fake-ai-control-rehearsal`: multi-round rehearsal must execute the
  submit -> reject -> reissue/repair -> corrected retry -> threshold
  glassbreak loop through runtime-owned surfaces.
- `known-friction-defect-family-gates`: real-run anomalies must be backfed into
  durable fake-AI profiles, contract cells, Cartesian rows, and runtime replay
  tests.
- `tiered-flowpilot-test-validation`: TestMesh and model-test alignment must
  expose current child evidence for the new replay suites before the parent
  coverage claim is full.

## Impact

- Affected code: review-window contract rows, singleton identity live-audit
  helpers/tests, contract-driven fake AI responder, runtime replay harness,
  contract-exhaustion/current-contract matrices, real-issue backfeed registry,
  and version/install metadata.
- Affected tests/models: review-window completeness tests, singleton identity
  tests, fake-AI runtime replay tests, contract exhaustion mesh, Cartesian
  control-plane exhaustion, synthetic agent coverage matrix, TestMesh,
  model-test alignment, topology checks, install sync, and local git version.
- Affected prompts/cards: no broad prompt rewrite is intended; structured
  envelopes/contracts remain the authority. Prompt/card wording changes are
  allowed only if tests prove the structured contract already exists and roles
  still need a minimal current-contract instruction.
