## Design

### Rehearsal Boundary

The rehearsal uses prepared fake AI artifacts, but the control plane must be
real:

- Router decisions come from `flowpilot_router` and the Router CLI, not manual
  state edits.
- Cards are opened and ACKed through `card_runtime` with read receipts.
- Packets are created, opened, ACKed, and submitted through `packet_runtime`.
- PM, reviewer, and officer work outputs use role-output envelopes or accepted
  runtime payload contracts.
- External events are limited to Router-declared events for the current wait.
- Background proof is only accepted when final out/err/combined/exit/meta
  artifacts exist and classify as passed.
- Terminal closure is only accepted after clean ledgers, backward replay, PM
  closure approval, terminal summary, and lifecycle terminalization.

The test may use helper methods to reduce repetition, but those helpers must
call the real runtime surfaces above. The CLI boundary test separately proves
that the public Router command path can read, apply, and record events for a
prepared fake role output.

### Scenarios

The matrix has three scenario classes:

1. Full happy rehearsal: startup through closed lifecycle with fake AI work
   packages and runtime receipts.
2. Authority/rejection rehearsal: missing ACKs, invented events, direct state
   mutation, and overclaiming are invalid matrix evidence.
3. Recovery/proof rehearsal: dead daemon or duplicate resume events restore a
   legal state, and progress-only background output is not completion proof.

### Confidence Boundary

Passing this change supports a scoped claim:

> Prepared fake AI packages can exercise the real FlowPilot control plane from
> startup to terminal closure, including selected compounded control-plane and
> package faults, and the run returns to standard state when recovery evidence
> is complete.

It does not support a universal claim:

> Every possible live AI semantic error has been proven impossible.

The matrix therefore requires `live_ai_semantic_quality_proven: false` for all
rows. Semantic quality remains a reviewer/PM/modeling responsibility.

### FlowGuard Route

DevelopmentProcessFlow owns the staged implementation and final evidence
freshness. Model-Test Alignment owns the mapping between the new rehearsal
obligation and executable tests. TestMesh owns the fast-tier gate registration.
Skipped or progress-only checks cannot be reported as passed.
