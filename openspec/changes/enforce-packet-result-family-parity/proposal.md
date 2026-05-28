## Why

The research batch repair showed that FlowPilot already had the right durable-result pattern for one packet family, but no hard gate forced sibling packet families to carry the same reconciliation, test, and evidence obligations.

This change upgrades the existing Router wait-reconciliation and FlowGuard evidence path so a same-class miss in one packet-result family becomes an obligation-family check across material scan, research, current-node, and PM role-work flows.

## What Changes

- Extend the existing durable wait reconciliation contract from a material/research pair to a packet-result family parity requirement.
- Require Router-owned reconciliation to prove durable result envelopes can fold missing result-return events for `material_scan`, `research`, `current_node`, and `pm_role_work`.
- Require partial-batch waits, stale reminder suppression, sealed-body provenance, and wrong-recipient rejection for every packet-result family.
- Add FlowGuard obligation-family parity and analogous-defect scan evidence before model-test alignment or final confidence can claim this class is covered.
- Add a focused router runtime child evidence surface for packet-result family reconciliation.

## Capabilities

### New Capabilities

None. This change upgrades existing FlowPilot control-plane and FlowGuard maintenance capabilities rather than introducing a parallel process.

### Modified Capabilities

- `wait-reconciliation`: durable result reconciliation must be family-complete across packet-result families.
- `partial-batch-accounting`: partial/full batch status must be consistent for current-node and PM role-work, not only material and research.
- `flowguard-boundary-test-alignment`: alignment must consume obligation-family parity rows and block stale or missing sibling evidence.
- `router-runtime-testmesh`: router runtime evidence must expose a packet-result family child suite.
- `known-friction-defect-family-gates`: known-friction confidence must consume the new obligation-family parity decision for this defect class.

## Impact

- Affected runtime helpers:
  `flowpilot_router_work_packets_next_actions.py`,
  `flowpilot_router_work_packets_current_node_validation.py`,
  `flowpilot_router_work_packets_pm_role_actions.py`,
  and reconciliation/barrier wrappers.
- Affected tests: focused router runtime packet-result family tests and related material/research/current-node/PM role-work tests.
- Affected simulations: FlowGuard model-test alignment, control-plane state consistency, known-friction/final-confidence evidence, and a new focused packet-result family parity model if needed.
- Affected local distribution: repository-owned FlowPilot skill assets must be synced to the local installed copy and then audited serially.
