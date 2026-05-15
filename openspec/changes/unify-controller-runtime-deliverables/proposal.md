## Why

Controller stateful deliverables currently use a Controller-specific
`required_deliverables` path that can drift from the existing role-output
runtime contract. The live startup failure showed that Controller could submit
a human-readable confirmation file and receipt while Router rejected the file
because it was not the canonical runtime-shaped artifact.

## What Changes

- Route Controller formal deliverables through the existing output-contract and
  runtime-envelope layer instead of a parallel Controller-only deliverable
  format.
- Keep `runtime/controller_action_ledger.json` as the Controller work board and
  scheduler surface; it must not become a separate artifact-validation
  framework.
- Add narrow Controller output contracts for mechanical control-plane
  deliverables, starting with Controller boundary confirmation.
- Require Router reconciliation to trust runtime-generated artifact metadata,
  path/hash evidence, and receipts before stateful Controller postconditions are
  marked satisfied.
- Keep lightweight Controller actions receipt-only when they do not produce a
  Router-visible durable fact.
- Fix bounded repair semantics so a repair attempt counts as failed only after
  the corresponding repair action returns invalid or missing runtime evidence.

## Capabilities

### New Capabilities
- `controller-runtime-deliverables`: Defines how Controller formal
  control-plane deliverables use the shared runtime/output-contract evidence
  path without turning Controller into a worker role.

### Modified Capabilities
- None.

## Impact

- Affects FlowPilot Router/Controller action reconciliation, role-output
  runtime support for Controller control-plane outputs, output-contract
  registry metadata, and focused FlowGuard models.
- Does not run or require the heavyweight `meta_model` or `capability_model`
  regressions for this focused repair.
