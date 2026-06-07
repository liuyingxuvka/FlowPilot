## Why

Recent FlowPilot maintenance missed a live failure because a packet asked the
role to return one shape while the runtime accepted a different hidden shape,
and fake AI rehearsals supplied the hidden field. FlowPilot needs one explicit
source of truth for packet result contracts so packet text, runtime gates, fake
AI outputs, and tests cannot drift independently.

## What Changes

- Add a packet result contract source-of-truth capability that names each
  current packet family, required result body fields, forbidden legacy fields,
  runtime validator, fake-AI output boundary, and reissue metadata.
- Require runtime mechanical blockers and reissued packet bodies to expose the
  same contract-family metadata used by the model.
- Require fake AI rehearsals to run in contract-blind mode: they may emit only
  fields declared by the packet contract unless the scenario is explicitly a
  negative overproduction test.
- Add model/test/source alignment checks that fail when runtime checks a field
  not declared by the contract, fake AI emits hidden undeclared fields, or a
  negative matrix is missing for a packet family.
- **BREAKING**: unsupported old result fields, wrappers, aliases, and fallback
  evidence remain hard failures; no compatibility translation is added.

## Capabilities

### New Capabilities

- `packet-contract-source-of-truth`: governs the single contract table shared by
  packet wording, runtime validation, fake AI rehearsal, negative tests, and
  FlowGuard model evidence.

### Modified Capabilities

- `multiround-fake-ai-control-rehearsal`: fake AI rehearsal evidence must prove
  contract-blind output behavior, not merely happy-path control progression.
- `real-router-dry-run-rehearsal`: dry-run fake AI packages must report whether
  their output body is contract-declared, overproduced, or intentionally
  negative.
- `flowguard-boundary-test-alignment`: model-test alignment must bind packet
  contract rows to runtime validators, fake AI scenario rows, and negative
  tests before treating broad e2e evidence as green.

## Impact

- Runtime contract helpers in `skills/flowpilot/assets/flowpilot_core_runtime`.
- Field contract and field mesh models in `simulations/`.
- Fake AI rehearsal helpers and scenario matrices.
- Runtime, high-standard flow, fake project, and model-test alignment tests.
- OpenSpec specs and FlowGuard adoption/topology evidence.
