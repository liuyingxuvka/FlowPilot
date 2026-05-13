# Route Skeleton Reviewer-Only Optimization Plan

Date: 2026-05-13

## Risk Intent Brief

This change uses FlowGuard before production edits because it changes the
default FlowPilot route-control workflow. The protected harm is speed-oriented
gate removal accidentally allowing route activation without product coverage,
process viability, reviewer challenge, route-mutation freshness, or terminal
ledger/replay evidence.

The intended optimization is narrow:

- keep Product FlowGuard Officer ownership of the product behavior model during
  product architecture;
- keep Process FlowGuard Officer ownership of the serial route/process model;
- remove Product FlowGuard Officer's second default route-product check after
  PM accepts the process route model;
- send the route directly from PM process-model acceptance to Reviewer route
  challenge;
- remove final-closure role-slice requirements for FlowGuard officers while
  preserving final ledger and terminal backward replay requirements.

## Optimization Sequence

| Step | Current behavior | Target behavior | Files/model areas |
| --- | --- | --- | --- |
| 1 | Route hard-gate model requires a route product review pass. | Model route activation as requiring the product behavior model, Process Officer process route pass, PM process-model acceptance, Reviewer route challenge pass, and no route Product Officer second pass. | `simulations/flowpilot_route_hard_gate_model.py`, `simulations/run_flowpilot_route_hard_gate_checks.py` |
| 2 | Explicit next-recipient model dispatches Product Officer route check before Reviewer route challenge. | Model Reviewer route challenge as the next default recipient after Process Officer pass and PM acceptance. | `simulations/router_next_recipient_model.py`, `simulations/run_router_next_recipient_checks.py` |
| 3 | Barrier equivalence treats route skeleton as PM + Reviewer + Process Officer + Product Officer, and final closure force-adds all role slices. | Route skeleton requires PM + Reviewer + Process Officer. Final closure requires PM + Reviewer only and no longer injects all role slices. | `skills/flowpilot/assets/barrier_bundle.py`, `simulations/barrier_equivalence_model.py`, `simulations/run_barrier_equivalence_checks.py` |
| 4 | Router default system card sequence waits for `product_officer_route_check_passed` before delivering Reviewer route challenge. | Router delivers Reviewer route challenge after `pm_process_route_model_accepted`. | `skills/flowpilot/assets/flowpilot_router.py` |
| 5 | Route activation requires `route_product_check.json`. | Route activation requires the Product Officer product behavior model, the Process Officer process route model, and Reviewer route challenge pass. | `skills/flowpilot/assets/flowpilot_router.py`, router runtime tests |
| 6 | Reviewer route challenge and block paths require `route_product_check.json` as source evidence. | Reviewer route challenge uses the route draft, process route model, PM process-model decision, root contract, child-skill manifest, and original product behavior model evidence. | Reviewer card, router source-path specs, tests |

## Bug/Risk Checklist

| Risk | What could go wrong | FlowGuard/test guard |
| --- | --- | --- |
| 1 | PM route activates before the Product Officer product behavior model exists. | Route hard-gate model rejects missing product behavior model; router keeps `_require_product_behavior_model_report`. |
| 2 | Process Officer passes a route without checking product-model coverage. | Route hard-gate model rejects process pass without `product_behavior_model_checked` and `route_can_reach_product_model`; router already requires both fields. |
| 3 | Reviewer route challenge is delivered before PM accepts the process route model. | Route hard-gate and next-recipient models require PM process-model acceptance before Reviewer route challenge. |
| 4 | Route activation bypasses Reviewer challenge after removing Product Officer route check. | Route hard-gate model rejects missing Reviewer challenge; router activation still requires `reviewer_route_check_passed`. |
| 5 | Legacy Product Officer route events accidentally become default blockers. | System card sequence no longer delivers the Product Officer route card by default; legacy direct events still require an explicit card delivery. |
| 6 | Reviewer report still requires deleted `route_product_check.json` source path. | Router checked paths and reviewer card text are updated; runtime tests cover Reviewer pass without route product check. |
| 7 | Final closure still claims officer role slices are required even though no fresh final officer check runs. | Barrier bundle and equivalence model remove final-closure officer role slices while retaining final ledger and terminal replay hazards. |
| 8 | Route mutation/recheck accidentally preserves stale route approvals. | Existing route reset tests continue to run; reset code still clears route review/activation flags. |

## Required Validation Order

1. Run the upgraded route hard-gate model and confirm all known-bad risks fail.
2. Run the upgraded explicit next-recipient model and confirm the Product
   Officer route step is no longer in the default chain.
3. Run the upgraded barrier equivalence model and confirm final ledger/replay
   hazards still fail.
4. Only then edit the router/card runtime.
5. Run targeted router runtime tests after the router edit.
6. Run the broader FlowGuard/meta/capability checks before installing or
   pushing.
