## Why

FlowPilot still has several control-plane facts recorded in separate ledgers that can drift apart: signed material packet envelopes can be rewritten by migration repair, Controller scheduler identity can collapse different control blockers into one row, stateful receipts can be treated as local acknowledgements, and PM can declare a reviewer gate package without producing a reviewer-readable artifact.

Those failures are symptoms of the same structure problem: mutable indexes, immutable signed artifacts, Controller-visible work rows, Router-executable obligations, and reviewer gate packages do not share one contract kernel.

## What Changes

- Add a control-plane contract kernel for artifact authority, action identity, receipt effects, and reviewer gate package release.
- Keep signed packet/result envelopes immutable after Controller relay; legacy repair must write mutable indexes, ledgers, or sidecar migration records instead of rewriting sealed originals.
- Make `handle_control_blocker` identity include the blocker artifact identity and require a replayable Router postcondition when Controller marks it done.
- Prevent a closed Controller action row from being reused for a different action identity.
- Accept the existing Worker self-check vocabulary used in bodies, including `status: pass`, when it appears inside the Contract Self-Check section.
- Require PM absorbed package dispositions to create and reference a reviewer-readable formal gate package artifact.

## Capabilities

### New Capabilities

- `flowpilot-control-plane-contract-kernel`: Router and Controller ledgers share one action identity and receipt-effect contract.
- `flowpilot-artifact-authority`: immutable signed artifacts and mutable projection/index artifacts have explicit authority boundaries.
- `flowpilot-reviewer-gate-packages`: PM formal gate package release requires a reviewer-readable artifact path and hash.

### Modified Capabilities

- `control-plane-state-consistency`: reconciliation must honor artifact immutability and stateful receipt effects.
- `router-controller-ledger-reconciliation`: Controller-visible actions must correspond to one Router obligation identity.
- `packet-output-contracts`: self-check parser and role templates must accept the same pass/fail vocabulary.

## Impact

- Affected runtime code: Controller scheduler identity/write helpers, control blocker actions, Controller receipt evidence folds, terminal material packet migration repair, packet contract self-check parsing, and PM package disposition writers.
- Affected verification: OpenSpec validation, FlowGuard control-plane friction model, focused router runtime/unit tests, install checks, background meta/capability regression checks, local install sync, and local git version creation.
- No release publish, remote push, dependency upgrade, sealed-body visibility relaxation, or Worker-to-Worker information sharing is included.
