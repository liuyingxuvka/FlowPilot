# Resume Manifest Checkpoint Recovery Plan

Date: 2026-05-13

## Situation

Heartbeat/manual resume can currently rehydrate the six-role crew, reach the
prompt-manifest controller action, report that the current checkpoint manifest
has not yet entered the PM resume decision, and then stop. That is the wrong
behavior: `check_prompt_manifest` is an internal router safety check before a
prompt card, not a role/user wait boundary.

## Optimization List

| ID | Optimization | Intended behavior | Files |
| --- | --- | --- | --- |
| O1 | Treat `check_prompt_manifest` as safe for run-until-wait folding | After resume rehydration, the router may apply the manifest check and continue until it reaches a real wait boundary such as a PM card delivery or role/user/host/packet boundary. | `skills/flowpilot/assets/flowpilot_router.py` |
| O2 | Make heartbeat resume instructions explicit | A heartbeat-woken agent must continue the router loop after `check_prompt_manifest` and must stop only at a real wait boundary. | `skills/flowpilot/assets/flowpilot_router.py`, `tests/test_flowpilot_router_runtime.py` |
| O3 | Sync derived status after computing a pending controller action | `current_status_summary.json` must show the actual pending action/next step immediately after the router computes it, so a resumed agent does not read a stale summary and stop. | `skills/flowpilot/assets/flowpilot_router.py`, `tests/test_flowpilot_router_runtime.py` |
| O4 | Upgrade the FlowGuard resume model before relying on the patch | The abstract model must represent the manifest-check folding rule, true wait boundaries, heartbeat instruction boundary, and status-summary freshness. | `simulations/flowpilot_resume_model.py`, `simulations/run_flowpilot_resume_checks.py` |
| O5 | Verify targeted runtime behavior and local installation sync | The patch must pass focused router tests, resume model checks, and local install audit/checks before local git recording. | `tests/`, `simulations/`, `scripts/` |

## Risk List

| ID | Possible bug introduced by the optimization | Required model/test catcher |
| --- | --- | --- |
| R1 | The router still stops at `check_prompt_manifest` and never reaches the PM resume card. | Model hazard: manifest-check stop before PM card. Runtime test: run-until-wait folds manifest check and stops at the prompt card boundary. |
| R2 | The router skips or duplicates the manifest check before delivering a prompt. | Existing and upgraded manifest request/check invariants. Runtime prompt-ledger assertions. |
| R3 | The router continues too far and crosses a real role/user/host/payload/packet wait boundary. | Model hazard: run-until-wait crossing a true wait boundary. Runtime test stops at card/action boundary after folding only safe controller checks. |
| R4 | Heartbeat prompt wording still lets the resumed agent treat the manifest checkpoint as a final stop. | Model field requiring heartbeat prompt continuation guidance. Runtime assertion on heartbeat startup prompt text. |
| R5 | Status summary remains stale after a pending controller action is computed, causing the resumed agent to stop from misleading display state. | Model field requiring summary sync after pending action. Runtime assertion on `current_status_summary.json`. |
| R6 | The patch lets the controller advance route progress or read sealed packet/result bodies during resume. | Existing controller relay-only, sealed-body, and reviewed-packet progress invariants remain hard gates. |
| R7 | Local installed FlowPilot skill is not synced, or local sync overwrites unrelated peer work. | Use repo-owned install sync/check scripts after validation; no remote push; preserve concurrent local changes. |

## Model Coverage Plan

| Risk | FlowGuard model addition |
| --- | --- |
| R1 | Add state for run-until-wait manifest folding and a hazard for stopping at `check_prompt_manifest`. |
| R2 | Keep prompt delivery tied to one manifest-check instruction and one manifest check. |
| R3 | Add state for real wait-boundary crossing and make it an invariant failure. |
| R4 | Add state that heartbeat startup guidance forbids stopping at manifest check before PM resume. |
| R5 | Add state that derived status is synced and names the pending manifest action before PM card delivery. |
| R6 | Reuse existing controller relay-only, sealed-body, and reviewed-packet progress invariants. |
| R7 | Verify with local install sync/check scripts and keep GitHub remote untouched. |

## Execution Order

1. Record this plan and risk table.
2. Upgrade the FlowGuard resume model to catch R1-R7.
3. Run `simulations/run_flowpilot_resume_checks.py` and confirm both safe graph and hazard detection pass.
4. Re-run focused router runtime tests for resume/run-until-wait/heartbeat startup.
5. Run long meta/capability checks in the background and inspect their logs.
6. Sync the local installed FlowPilot skill from the local repository and audit it.
7. Record the validated local change in local git only; do not push to GitHub.
