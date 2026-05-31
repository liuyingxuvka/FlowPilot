# FlowPilot Resume Role Reuse Optimization Plan

## Optimization Sequence

| Step | Change | Acceptance Check |
| --- | --- | --- |
| 1 | Keep heartbeat/manual resume recovery routed through `heartbeat_or_manual_resume_requested` and current-run state reload before any PM resume decision. | Resume tests still require state reload before role rehydration and PM decisions. |
| 2 | Change host role recovery semantics from broad replacement to rehydrating runtime-required bindings, reusing confirmed active bindings, and replacing only failed or uncertain roles. | Router action exposes `requires_host_role_rehydration=true`, `requires_host_role_binding=false`, and `new_binding_required_only_for_replacements=true`. |
| 3 | Require active roles to report `live_agent_continuity_confirmed` after current-run memory refresh. | Payload validation rejects replacement rehydration for active host liveness. |
| 4 | Require missing, cancelled, completed, unknown, or timeout roles to be replacement-opened from current-run memory. | Replacement records require `opened_after_resume_state_loaded=true` and matching memory/context fields. |
| 5 | Preserve unsupported historical with older payloads only where safe. | `rehydrated_after_resume_state_loaded=true` is required, while unsupported historical `opened_after_resume_state_loaded=true` remains accepted as proof that state was loaded. |

## Risk Coverage

| Risk | Failure Mode | FlowGuard / Test Coverage |
| --- | --- | --- |
| R1 | Active required bindings are replaced even though they could be reused. | `all_active_roles_replaced_instead_of_reused` hazard fails the resume model. |
| R2 | One failed role causes unrelated active bindings to be replaced. | `one_failed_role_replaced_all_runtime_roles` hazard fails the resume model. |
| R3 | Partial recovery replaces the failed role but does not reuse still-active roles. | `one_failed_role_does_not_reuse_active_roles` hazard fails the resume model. |
| R4 | A wait timeout is treated as proof that an agent is alive. | Existing timeout-unknown invariant remains active and timeout paths require replacement. |
| R5 | A replacement role is accepted without current-run memory/state refresh proof. | Router payload validation requires run id, tick id, memory hash, context hash, and rehydration state-loaded proof. |
| R6 | PM resume happens before role recovery is fully reported. | Existing resume model invariants still require role binding recovery report before PM resume decision. |

## Verification

| Check | Purpose |
| --- | --- |
| `python simulations\run_flowpilot_resume_checks.py` | Proves the updated resume model accepts the safe plan and rejects the targeted hazards. |
| `python -m pytest tests\test_flowpilot_router_runtime.py -k resume -q` | Verifies runtime behavior for heartbeat resume, active reuse, and partial replacement. |
| `python scripts\install_flowpilot.py --check --json` | Confirms the local installed FlowPilot skill matches the repository source after sync. |
