## Overview

The decomposition follows FlowGuard TestMesh ownership rather than command-only
tiering:

- Child contract owner: prepares and verifies the detailed route-mutation
  preconditions.
- Parent contract owner: calls `pm_mutates_route_after_review_block` and checks
  only parent-owned outputs.
- Release/full oracle: old aggregate flow remains available when the full
  child workflow itself must be replayed.

## Contract Boundary

The child contract binds these parent inputs:

- current run and active route;
- `execution_frontier.json` with active route/node/version;
- route action policy registry copied into the run;
- one active model-miss review-block flag;
- `model_miss_triage_closed` when the parent scenario requires mutation;
- optional active packet ledger when packet disposition is the parent output.

The parent owns only these outputs:

- `routes/route-001/mutations.json`;
- `routes/route-001/flow.draft.json`;
- `execution_frontier.json.pending_route_mutation`;
- `evidence/stale_evidence_ledger.json`;
- `packet_ledger.json.route_mutation_packet_disposition`.

Parent contract tests explicitly fail if future edits call child-flow helpers
such as `boot_to_controller`, `complete_pre_route_gates`,
`deliver_current_node_cards`, or
`prepare_current_node_result_for_review`.

## FlowGuard Model

`simulations/flowpilot_slow_test_contract_model.py` models valid and known-bad
contract decisions. Hazards rejected by the model include missing child owner,
unbound input/output contracts, parent replaying child boot or packet-worker
flow, duplicate state owner, hidden child skips, stale child evidence, and
release-scope claims without a current child oracle.

## Validation Strategy

- `python simulations/run_flowpilot_slow_test_contract_checks.py --json-out simulations/flowpilot_slow_test_contract_results.json`
- `python -m pytest tests/test_flowpilot_router_runtime_route_mutation.py -q --durations=20`
- `python -m pytest tests/test_flowpilot_test_tiers.py -q`
- `python scripts/run_test_tier.py --tier router-route --dry-run --json`
- `python scripts/check_install.py --json`
