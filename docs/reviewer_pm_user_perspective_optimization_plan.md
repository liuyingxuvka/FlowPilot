# Reviewer and PM User-Perspective Challenge Optimization Plan

Date: 2026-05-12

## Purpose

Strengthen FlowPilot's existing `independent_challenge` and PM quality checks
so reviewer and PM decisions consistently ask whether the current result is
actually good enough from the final user's point of view.

This is intentionally not a new UX review framework, new route phase, or new
top-level report object. The user-perspective challenge is an internal
dimension of the existing reviewer `independent_challenge` and PM
high-standard/product-function checks.

## Optimization Points

| Step | Optimization point | Target files or areas | Intended behavior | Completion evidence |
| --- | --- | --- | --- | --- |
| 1 | Strengthen the reviewer core card wording. | `skills/flowpilot/assets/runtime_kit/cards/roles/human_like_reviewer.md` | Reviewer treats final-user intent, product usefulness, experience quality, and higher-standard improvement opportunities as part of `independent_challenge` when applicable. | Reviewer core text contains the fused requirement without introducing a separate review phase. |
| 2 | Strengthen PM core responsibility. | `skills/flowpilot/assets/runtime_kit/cards/roles/project_manager.md` | PM must carry the same final-user/product-quality lens while drafting product architecture, routes, node acceptance plans, final ledgers, and closure decisions. | PM core text states PM owns user-intent and higher-standard self-checks. |
| 3 | Apply the reviewer lens to worker result review. | `cards/reviewer/worker_result_review.md` | Reviewer checks whether the worker result is useful for the current user-facing slice, not only whether the packet was mechanically satisfied. | Card mentions final-user usefulness, user intent, and higher-standard PM suggestions. |
| 4 | Apply the reviewer lens to parent backward replay. | `cards/reviewer/parent_backward_replay.md` | Reviewer catches cases where child-local passes do not compose into a usable parent-level result. | Card requires composition review from the parent goal and user-facing outcome. |
| 5 | Apply the reviewer lens to final backward replay. | `cards/reviewer/final_backward_replay.md` | Reviewer starts from the delivered product/output and challenges whether it feels complete and satisfies the user's real goal, not only whether the ledger is clean. | Card requires delivered-product replay against user intent and improvement opportunities. |
| 6 | Apply the reviewer lens to evidence quality review. | `cards/reviewer/evidence_quality_review.md` | Reviewer checks whether evidence proves real use or final-output quality instead of only file existence, hashes, or report presence. | Card rejects existence-only proof for user-facing experience claims. |
| 7 | Slightly sharpen product architecture challenge. | `cards/reviewer/product_architecture_challenge.md` | Reviewer challenges user intent preservation, missing high-value capabilities, product usefulness, and semantic downgrades. | Card keeps this within the existing product architecture challenge. |
| 8 | Slightly sharpen node acceptance plan review. | `cards/reviewer/node_acceptance_plan_review.md` | Reviewer blocks node plans that cannot explain how the node contributes to final user value or how that contribution will be proven. | Card maps user-facing proof into existing acceptance-plan review. |
| 9 | Strengthen PM phase cards only where decisions are made. | `pm_product_architecture`, `pm_node_acceptance_plan`, `pm_route_skeleton`, `pm_final_ledger`, `pm_closure` cards | PM asks the user-perspective question before handing work to reviewer or claiming completion. | PM cards carry concise self-check language; no new phase is added. |
| 10 | Upgrade the existing FlowGuard reviewer active-challenge model. | `simulations/flowpilot_reviewer_active_challenge_model.py` and runner | Model catches reviewer passes that omit applicable user-perspective challenge or downgrade hard user-intent failures. | Hazard checks fail before the model upgrade and pass after safe behavior is represented. |
| 11 | Add a small PM planning-quality guard. | Prefer existing `simulations/flowpilot_planning_quality_model.py` if needed | PM product architecture, node plans, and closure cannot pass when user-intent/high-standard self-checks are missing for non-trivial product work. | Planning-quality checks cover PM-side omissions. |
| 12 | Add lightweight installation/card checks. | `scripts/check_runtime_card_capability_reminders.py`, `scripts/check_install.py` | Repository checks verify the prompt text was propagated to key cards. | Check scripts fail if core reviewer/PM wording or key-card reminders are missing. |
| 13 | Run local install sync after all repository checks pass. | `scripts/install_flowpilot.py`, installed Codex skill directory | Local installed FlowPilot matches the repository source. | Install check reports source-fresh or equivalent local sync success. |

## Risk and Bug Checklist

| Risk id | Possible bug introduced by this optimization | Why it matters | FlowGuard or test coverage that must catch it |
| --- | --- | --- | --- |
| R1 | Reviewer still treats `independent_challenge` as evidence-only and omits final-user usefulness when applicable. | The original weakness remains. | Reviewer active-challenge hazard: applicable user-perspective challenge missing. |
| R2 | Reviewer records user-experience hard failures as residual risks or PM suggestions. | Core user intent can be falsely completed. | Reviewer active-challenge hazard: hard user-intent failure downgraded. |
| R3 | Reviewer drops higher-standard improvement opportunities instead of routing them to PM suggestion support. | Useful product improvements are lost. | Existing higher-standard PM signal hazard remains required. |
| R4 | Every review becomes a heavyweight UX pass, including simple or protocol-only reviews. | FlowPilot becomes slower and noisy. | Existing simple-review-overburdened hazard plus an applicability/waiver path. |
| R5 | Reviewer becomes a second PM and starts making route decisions. | Role authority is violated. | Existing role-boundary and PM-reroute-request checks remain required. |
| R6 | PM relies on reviewer to find all product-quality issues and stops doing its own user-intent self-check. | Bad plans reach reviewer too late. | Planning-quality hazard: PM user-intent/high-standard self-check missing. |
| R7 | PM blocks too much by treating every improvement opportunity as a hard requirement. | Higher standard becomes scope creep. | Planning-quality hazard: nonblocking improvement incorrectly treated as required for simple/current gate. |
| R8 | Final replay passes from a clean ledger without challenging delivered product usefulness. | Completion can still be false-positive. | Reviewer final backward replay card check plus active-challenge delivered-product scenario. |
| R9 | Evidence-quality review accepts file existence as proof of user-facing experience. | Screenshots or reports can substitute for real use. | Reviewer card reminder check and existing evidence-quality safeguards. |
| R10 | The prompt wording is added only to the core card, not to the key gate cards where models actually act. | Prompt pressure stays too centralized and weak. | Card reminder check for key reviewer and PM cards. |
| R11 | The model is green but production cards are not updated. | Model coverage does not change runtime behavior. | `check_install.py` propagation check plus targeted card reminder script. |
| R12 | Local repository passes but installed FlowPilot remains stale. | User invokes old behavior. | Local install sync and install check after repository validation. |

## Required FlowGuard Order

1. Write or update this plan.
2. Upgrade the reviewer active-challenge model to include the applicable
   final-user/product-usefulness challenge.
3. Add PM planning-quality coverage for PM self-checks if existing coverage is
   insufficient.
4. Run model hazard checks and confirm each listed risk is caught by a model or
   targeted check.
5. Only then update runtime cards and lightweight install/card checks.
6. Run focused checks after each edit batch.
7. Run final repository checks.
8. Sync the installed local skill.
9. Review local git state. Do not push to GitHub.

## Non-Goals

- Do not add a separate UX review stage.
- Do not add a large new top-level report object.
- Do not require every gate to perform a full walkthrough.
- Do not allow reviewer to replace PM route decisions.
- Do not convert every improvement opportunity into a blocker.
- Do not touch remote GitHub publication or release state.
