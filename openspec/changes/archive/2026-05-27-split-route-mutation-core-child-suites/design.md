## Boundary

This is a TestMesh maintenance change. The parent route-mutation contract suite
continues to live in `tests/flowpilot_route_mutation_contracts.py` and remains
the fast parent evidence for the route-mutation event boundary. The full runtime
oracle remains available, but it is split into child suites by behavior family.

## Child Suite Ownership

| Suite | Owns |
| --- | --- |
| `router_route_mutation_draft_activation` | PM route draft preservation and reviewed route activation guards. |
| `router_route_mutation_model_miss_triage` | Reviewer block triage, model-miss decisions, and officer follow-up channel. |
| `router_route_mutation_acceptance_repair` | Node acceptance plan repair and same-node revision paths. |
| `router_route_mutation_preconditions` | Route-mutation prerequisites, final-ledger blocking, and root-entry replanning guard. |
| `router_route_mutation_transactions` | Multiple repair transactions and idempotency behavior. |
| `router_route_mutation_topology` | Supersede topology mutation and route reactivation. |
| `router_route_mutation_sibling_replacement` | Sibling replacement, stale sibling proof, and old packet disposition. |
| `router_route_mutation_parent_backward` | Parent backward targets, replay requirement, and non-continue parent segment repair. |

The compatibility aggregate `tests.router_runtime.route_mutation` may import
the child modules and expose a `load_tests` suite, but routine router tiers must
not use it as their primary child command.

## FlowGuard Evidence

The StructureMesh/TestMesh evidence must reject a route tier claim when any
route-mutation child owner is missing, stale, hidden behind the aggregate, or
represented only by progress output. Each child command needs its own
background artifact base name under `tmp/flowguard_background/`.
The tier runner must clear an old child artifact set before relaunching the
same child name, otherwise a previous `.exit.txt` can be mistaken for the new
run's completion result.

Model-test alignment should continue to treat route mutation as one product
obligation family, but its ordinary test evidence must reference the focused
child suites where the obligation actually lives.

## Validation

Focused validation:

```powershell
python -m unittest -v tests.router_runtime.route_mutation_draft_activation
python -m unittest -v tests.router_runtime.route_mutation_model_miss_triage
python -m unittest -v tests.router_runtime.route_mutation_acceptance_repair
python -m unittest -v tests.router_runtime.route_mutation_preconditions
python -m unittest -v tests.router_runtime.route_mutation_transactions
python -m unittest -v tests.router_runtime.route_mutation_topology
python -m unittest -v tests.router_runtime.route_mutation_sibling_replacement
python -m unittest -v tests.router_runtime.route_mutation_parent_backward
python -m unittest -v tests.router_runtime.route_mutation
```

Parent and model validation:

```powershell
python -m pytest tests/test_flowpilot_test_tiers.py -q
python simulations/run_flowpilot_structure_maintenance_checks.py --json-out simulations/flowpilot_structure_maintenance_results.json
python simulations/run_flowpilot_model_test_alignment_checks.py --json-out simulations/flowpilot_model_test_alignment_results.json
python scripts/run_test_tier.py --tier router-route --background --background-dir tmp/flowguard_background --background-max-parallel 4 --json
```
