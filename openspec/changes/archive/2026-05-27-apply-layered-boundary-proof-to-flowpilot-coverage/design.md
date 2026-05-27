# Design

## Approach

Build two FlowGuard layered proof plans from existing evidence:

1. `flowpilot-layered-boundary-accounting` proves the current coverage
   inventory boundary. It checks parent ownership, child evidence freshness,
   child reattachment, and a finite leaf matrix for all known gap classes and
   alignment gates.
2. `flowpilot-full-leaf-cartesian-requirement` is stricter. It is green only
   when the current inventory has no blocking gap classes, the full diagnostic
   has no deferred StructureMesh split, and alignment reports
   `full_coverage_ok=true`.

The first plan answers: "Is the current coverage bookkeeping internally
consistent and test-owned?" The second answers: "Can we claim the whole FlowPilot
system has finished the bottom-level full boundary Cartesian proof?"

## Claim Boundary

The accounting plan may be green while the requirement plan is red. That is
intentional. A scoped replay adapter or deferred split can be correctly tracked
and tested without being complete.

## Validation

Run:

- `python -m py_compile simulations/flowpilot_layered_boundary_proof.py tests/test_flowpilot_layered_boundary_proof.py`
- `python simulations/flowpilot_layered_boundary_proof.py --json-out simulations/flowpilot_layered_boundary_proof_results.json`
- `python -m unittest tests.test_flowpilot_layered_boundary_proof tests.test_flowpilot_full_model_coverage_inventory tests.test_flowpilot_full_model_test_gap_closure -v`
- `openspec validate apply-layered-boundary-proof-to-flowpilot-coverage --strict`
