# FlowPilot Layered Boundary Proof

Date: 2026-05-22

This report is generated from:

```powershell
python simulations/flowpilot_layered_boundary_proof.py --json-out simulations/flowpilot_layered_boundary_proof_results.json
```

## Claim Boundary

The layered proof now separates two claims:

- `layered_accounting_ok`: the FlowPilot coverage inventory is owned by child
  proof contracts, reattached to the parent coverage model, and represented by
  finite leaf matrix cells for the inventory boundary.
- `full_leaf_cartesian_ok`: the whole FlowPilot runtime/model system has no
  scoped replay gaps, no skipped/scoped evidence, no hard runner findings, no
  deferred StructureMesh split, and `full_coverage_ok=true`.

Both claims are currently green.

## Current Result

| Check | Result | Meaning |
| --- | --- | --- |
| Parent/child accounting proof | green | Coverage bookkeeping is internally owned and reattached. |
| Inventory leaf matrix | green | Every known gap class has a boundary cell and closure strategy. |
| Full leaf Cartesian requirement | green | No scoped replay gaps, skipped/scoped evidence gaps, hard runner findings, deferred StructureMesh splits, or `full_coverage_ok=false` blocker remains. |

Current blockers:

| Blocker | Count |
| --- | ---: |
| Blocking gap classes | 0 |
| Deferred StructureMesh runtime surfaces | 0 |
| `full_coverage_ok` | true |

Explicitly skipped StructureMesh surfaces:

- `skills/flowpilot/assets/flowpilot_router_protocol_external_event_data.py`
  because it is a table-only declarative contract, not a duplicated
  decision/effect path.

## Interpretation

The current work proves that FlowPilot no longer has an unowned
coverage-accounting gap in the model inventory layer and that the stricter full
leaf Cartesian readiness gate is green for the current repository evidence. Any
future scoped replay item must either attach to exact runtime/source evidence or
be split into a smaller leaf model whose `Input x State -> Output x Next State`
matrix can be fully tested before this claim remains green.
