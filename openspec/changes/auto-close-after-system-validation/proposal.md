## Why

The fresh FlowPilot runtime no longer needs a separate Closure Officer packet on
the ordinary success path. FlowGuard and reviewer work already produce the
evidence that the system validator can check mechanically. After that system
validation passes, asking another AI role to close the same subject adds a hop
without adding independent judgement.

The closure step still matters. It is the point where FlowPilot records that a
subject is done, clears the accounting, applies any staged high-risk PM
decision, and moves to the next work packet. This change moves that closure
step into a system-owned action after system validation.

## What Changes

- Record a system closure row after system validation passes.
- Automatically apply the same closure side effects that the old closure packet
  applied: preplanning acceptance, route materialization, node closure, PM
  disposition issuance, staged PM decision application, and final closure.
- Do not issue a Closure Officer packet on the ordinary successful path.
- If system validation fails, create a system-validation blocker and route it to
  PM repair through the same repair path used by reviewer, FlowGuard, system
  validation, and worker failures.
- Remove the validator and Closure Officer packet roles from the clean new
  runtime. Validation and closure are system actions, not worker packets.

## Capabilities

### New Capabilities

- `new-flowpilot-system-owned-closure`: System-owned closure after system
  validation, with PM repair routing for failed system validation.

### Modified Capabilities

- `new-flowpilot-validation-automation-and-pm-risk-gates`: The validation gate
  still exists, but passed validation now closes automatically instead of
  issuing a Closure Officer packet.

## Impact

- Runtime packet progression in
  `skills/flowpilot/assets/ai_project_runtime/runtime.py`.
- High-standard runtime tests and black-box rehearsal expectations.
- FlowGuard model and model-test alignment runner for validation/PM gates.
- Runtime check runners that previously completed a closure packet manually.
- Runtime responsibility/packet contracts that previously listed validator or
  Closure Officer as role-dispatch workers.
- Local install sync and local git commit only after OpenSpec, FlowGuard,
  targeted tests, fake AI rehearsal, background meta/capability, and install
  checks pass.
