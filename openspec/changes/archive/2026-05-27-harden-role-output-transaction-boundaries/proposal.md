## Why

FlowPilot already has separate mechanisms for role-output contracts, generated envelopes, control transactions, and Controller action identity, but PM package disposition still has gaps where formal decisions can be hand-shaped or only partially committed. This causes role-body fields to leak into Controller-visible envelopes, PM absorption to stop halfway through state finalization, and control-blocker waits to reuse stale action identity.

## What Changes

- Add a registry-backed PM package disposition role output so material, research, and current-node package dispositions use the same `role_output_runtime` envelope path as other formal PM decisions.
- Require Router waits for PM package disposition to name the expected output contract and output type, so the Router decides the envelope shape before the PM writes the decision.
- Extend the existing control transaction registry so PM package disposition is evaluated as result absorption before it mutates run state, package records, wait flags, or status projections.
- Generalize existing control-blocker identity fields to all control-blocker-related actions that carry blocker identity, not only the initial `handle_control_blocker` action.
- Keep legacy/manual event envelopes blocked or quarantined for these formal outputs instead of treating them as valid continuation evidence.
- Add FlowGuard and ordinary regression coverage for the new contract, transaction, identity, and source-conformance obligations.

## Capabilities

### New Capabilities
- `role-output-transaction-boundaries`: Defines the fixed contract/runtime/transaction boundary for formal PM package dispositions and control-blocker action identity.

### Modified Capabilities
- `packet-open-authority-exits`: PM package result disposition must use the registry-backed formal-output path before packet evidence can be released to reviewer gates.
- `router-external-wait-reconciliation`: Router wait reconciliation must reject or quarantine manual envelopes for PM package dispositions when a registry-backed role-output envelope is required.
- `controller-action-ledger`: Control-blocker-related waits must include blocker identity in their deterministic action IDs and scheduler idempotency keys.

## Impact

- Affected runtime assets: `runtime_kit/contracts/contract_index.json`, `runtime_kit/control_transaction_registry.json`, PM package disposition wait/action cards, role-output runtime schema specs, Router event dispatch, and control-plane action identity helpers.
- Affected FlowGuard models: role-output runtime, control transaction registry, PM package absorption, and control-plane friction/identity checks.
- Affected tests: Router runtime material/research/current-node PM disposition tests, role-output runtime contract tests, control transaction registry tests, and Controller action identity/idempotency tests.
- No release, publish, dependency, or stack changes are included.
