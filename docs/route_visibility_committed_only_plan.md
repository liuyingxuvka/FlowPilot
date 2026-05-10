# Committed-Only Route Visibility Plan

Date: 2026-05-10

## Risk Intent

FlowPilot must not present an internal route draft as the user-visible route.
The user-visible route is a commitment surface. It may show a waiting state, or
the last committed route version, but it must not switch to a draft, review
candidate, rejected draft, or repair candidate before the route is formally
activated as `flow.json`.

## Optimization Checklist

| Step | Optimization Point | Concrete Change | Acceptance Signal |
| --- | --- | --- | --- |
| 1 | Document the source-of-truth boundary | Define `flow.draft.json` as internal-only and `flow.json` as the only user-visible route source | This document and FlowGuard model both name the boundary |
| 2 | Upgrade the route-display FlowGuard model first | Replace the old model assumption that draft routes are displayable with a committed-only visibility lifecycle | Known-bad draft projection states fail before production code changes |
| 3 | Prove the model catches expected bug classes | Add hazards for draft display, draft-backed display plans, draft-backed snapshots, and draft-backed Cockpit/chat route signs | `run_flowpilot_route_display_checks.py` reports all hazards detected |
| 4 | Prove the intended plan passes | Model path keeps the visible surface at waiting/previous committed route through draft and review, then displays only after activation | FlowGuard explorer passes with required committed-route labels |
| 5 | Stop route draft from rewriting the visible plan | `pm_writes_route_draft` writes only the draft and resets route-review gates; it does not call display projection writers | Runtime test: after draft, no route-scope `display_plan.json` is written from `pm_writes_route_draft` |
| 6 | Stop visible snapshots from falling back to drafts | User-visible route snapshots read active `flow.json` only; draft reads remain available only to review gates | Runtime test: draft-only runs keep waiting/previous committed visible state |
| 7 | Stop chat/Cockpit route sign generation from using drafts by default | Route-sign generation excludes `flow.draft.json` unless explicitly requested by a diagnostic/internal caller | Unit test: draft-only route sign does not report `flow_draft` as a user-visible source |
| 8 | Keep formal activation behavior | `pm_activates_reviewed_route` promotes the reviewed draft into `flow.json`, writes frontier, writes display plan, and marks display dirty | Runtime test: sync action appears only after activation and references `flow_json` |
| 9 | Preserve local install synchronization | After repo changes pass, sync the installed FlowPilot skill from the repo and run install audit | Installed skill audit confirms source-fresh content |
| 10 | Keep remote GitHub untouched | Do not push, tag, release, or open PR | `git status` is local-only; no remote command is run |

## Risk And Bug Checklist

| Risk ID | Possible Bug | Why It Matters | FlowGuard Coverage Required |
| --- | --- | --- | --- |
| R1 | Draft route appears in chat or Cockpit before review | User sees an unapproved route as if it were the execution commitment | Hazard `draft_route_projected_to_user_visible_surface` must fail |
| R2 | `pm_writes_route_draft` rewrites `display_plan.json` to route scope | Router immediately asks for `sync_display_plan` after a draft | Hazard `draft_writes_visible_display_plan` must fail |
| R3 | `route_state_snapshot.json` uses `flow.draft.json` as visible route data | Cockpit can show draft nodes even if display plan is preserved | Hazard `draft_backed_route_state_snapshot_visible` must fail |
| R4 | Route-sign generator falls back to `flow.draft.json` | Chat fallback can display draft even when router display plan is guarded | Hazard `draft_backed_chat_route_sign` must fail |
| R5 | No committed route produces a fake route map instead of a waiting state | First run may imply a route commitment that does not exist | Model safe path must keep `visible_route_kind=waiting` until activation |
| R6 | Reviewed activation no longer displays the committed route | Fix could over-block route visibility | Required label `committed_route_synced_to_user_visible_surface` must be reachable |
| R7 | Previous committed route is overwritten by a new draft | A user may lose the last valid route while a replacement is under review | Hazard `draft_overwrites_previous_committed_visible_route` must fail |
| R8 | Route repair candidate is shown before recheck | Review-failure repair can leak unapproved topology | Hazard `repair_candidate_projected_before_commit` must fail |
| R9 | Node status semantics regress during activation display | Completed, active, selected, and pending states could be conflated | Existing status-distinction hazard must continue to fail |
| R10 | Internal evidence/source fields leak while changing display payloads | UI must not expose evidence tables or source fields | Existing evidence/source leakage hazards must continue to fail |

## Intended Protocol

1. `pm_writes_route_draft` writes `routes/<route-id>/flow.draft.json`.
2. The user-visible display remains at the prior committed route, or a waiting
   state if no committed route exists.
3. Process/product/reviewer checks read the draft through internal route-check
   paths.
4. Failed checks keep the visible surface unchanged.
5. `pm_activates_reviewed_route` promotes the reviewed draft to
   `routes/<route-id>/flow.json`, writes `execution_frontier.json`, writes the
   route display plan, and marks the visible projection dirty.
6. `sync_display_plan` may project the route only when its source route is
   `flow.json` or a snapshot explicitly built from `flow.json`.

## Local Sync Boundary

After model and runtime tests pass, sync only the local installation and local
git state:

- repository files under this workspace;
- installed local FlowPilot skill under the Codex skills directory;
- local git index/commit if requested by the user or needed for local tracking.

Remote GitHub sync is out of scope for this change.
