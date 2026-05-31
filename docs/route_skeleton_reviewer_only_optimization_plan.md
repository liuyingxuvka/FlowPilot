# Route Skeleton Reviewer-Only Optimization Plan

Date: 2026-05-13

## Risk Intent Brief

This change uses FlowGuard before production edits because it changes the
default FlowPilot route-control workflow. The protected harm is speed-oriented
gate removal accidentally allowing route activation without product coverage,
process viability, reviewer challenge, route-mutation freshness, or terminal
ledger/replay evidence.

The intended optimization is narrow:

- keep FlowGuard operator ownership of the product behavior model during
  product architecture;
- keep FlowGuard operator ownership of the serial route/process model;
- remove FlowGuard operator's second default route-product check after
  PM accepts the process route model;
- send the route directly from PM process-model acceptance to Reviewer route
  challenge;
- remove final-closure role-slice requirements for FlowGuard operators while
  preserving final ledger and terminal backward replay requirements.

## Optimization Sequence

| Step | Current behavior | Target behavior | Files/model areas |
| --- | --- | --- | --- |
| 1 | Route hard-gate model requires a route product review pass. | Model route activation as requiring the product behavior model, FlowGuard operator route-scope process route pass, PM process-model acceptance, Reviewer route challenge pass, and no route FlowGuard operator product-scope second pass. | `simulations/flowpilot_route_hard_gate_model.py`, `simulations/run_flowpilot_route_hard_gate_checks.py` |
| 2 | Explicit next-recipient model dispatches FlowGuard operator product-scope route check before Reviewer route challenge. | Model Reviewer route challenge as the next default recipient after FlowGuard operator route-scope pass and PM acceptance. | `simulations/router_next_recipient_model.py`, `simulations/run_router_next_recipient_checks.py` |
| 3 | Historical equivalence proof layers were kept as release gates. | New-only runtime checks own the route skeleton and final closure contract directly. | `simulations/flowpilot_new_only_runtime_model.py`, `simulations/run_new_only_runtime_checks.py` |
| 4 | Router default system card sequence waits for `flowguard_operator_route_check_passed` before delivering Reviewer route challenge. | Router delivers Reviewer route challenge after `pm_process_route_model_accepted`. | `skills/flowpilot/assets/flowpilot_router.py` |
| 5 | Route activation previously required a FlowGuard operator product-scope route check artifact. | Route activation requires the FlowGuard operator product-scope product behavior model, the FlowGuard operator route-scope process route model, and Reviewer route challenge pass. | `skills/flowpilot/assets/flowpilot_router.py`, router runtime tests |
| 6 | Reviewer route challenge and block paths previously required a FlowGuard operator product-scope route check artifact as source evidence. | Reviewer route challenge uses the route draft, process route model, PM process-model decision, root contract, child-skill manifest, and original product behavior model evidence. | Reviewer card, router source-path specs, tests |

## Bug/Risk Checklist

| Risk | What could go wrong | FlowGuard/test guard |
| --- | --- | --- |
| 1 | PM route activates before the FlowGuard operator product-scope product behavior model exists. | Route hard-gate model rejects missing product behavior model; router keeps `_require_product_behavior_model_report`. |
| 2 | FlowGuard operator route-scope passes a route without checking product-model coverage. | Route hard-gate model rejects process pass without `product_behavior_model_checked` and `route_can_reach_product_model`; router already requires both fields. |
| 3 | Reviewer route challenge is delivered before PM accepts the process route model. | Route hard-gate and next-recipient models require PM process-model acceptance before Reviewer route challenge. |
| 4 | Route activation bypasses Reviewer challenge after removing FlowGuard operator product-scope route check. | Route hard-gate model rejects missing Reviewer challenge; router activation still requires `reviewer_route_check_passed`. |
| 5 | Unsupported FlowGuard operator product-scope route events accidentally become default blockers. | System card sequence no longer delivers the FlowGuard operator product-scope route card by default; unsupported direct events are rejected by current event intake. |
| 6 | Reviewer report still requires deleted FlowGuard operator product-scope route-check source evidence. | Router checked paths and reviewer card text are updated; runtime tests cover Reviewer pass without a second FlowGuard operator product-scope route check. |
| 7 | Final closure still claims FlowGuard operator role slices are required even though no fresh final FlowGuard operator check runs. | Current final-ledger and terminal replay checks own final closure without barrier-equivalence layers. |
| 8 | Route mutation/recheck accidentally preserves stale route approvals. | Existing route reset tests continue to run; reset code still clears route review/activation flags. |

## Required Validation Order

1. Run the upgraded route hard-gate model and confirm all known-bad risks fail.
2. Run the upgraded explicit next-recipient model and confirm the Product
   FlowGuard operator route step is no longer in the default chain.
3. Run the upgraded barrier equivalence model and confirm final ledger/replay
   hazards still fail.
4. Only then edit the router/card runtime.
5. Run targeted router runtime tests after the router edit.
6. Run the broader FlowGuard/meta/capability checks before installing or
   pushing.
