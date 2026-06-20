## Design

This change keeps the existing FlowPilot coverage architecture and adds a
freshness gate instead of a new compatibility surface.

The authoritative sources stay unchanged:

- Cartesian current-contract behavior is owned by
  `simulations/flowpilot_cartesian_control_plane_exhaustion_model.py` and its
  runner.
- Contract/fake-AI/review-window cell generation is owned by the existing
  ContractExhaustionMesh and fake-AI responder models.
- Full runner inventory is owned by `scripts/run_flowguard_coverage_sweep.py`
  plus `simulations/run_flowpilot_full_model_coverage_inventory.py`.
- Topology remains generated orientation evidence, not a behavioral authority.

The new guard compares durable evidence to current generated facts. It does not
accept old aliases, infer missing runner rows, or translate old result shapes.
If a runner is added or the Cartesian matrix expands, the durable evidence must
be regenerated before install/topology checks can support a completion claim.

## Verification Strategy

- Unit tests fail if persisted Cartesian counts drift from live model counts.
- Unit tests fail if persisted coverage sweep/inventory omit any current
  `run_*_checks.py` runner.
- Existing focused fake-AI, contract-exhaustion, runtime replay, liveness,
  topology, install, and OpenSpec checks prove the refreshed evidence is
  consumable.
