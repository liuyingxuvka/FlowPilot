## 0. Baseline And Audit

- [x] 0.1 Confirm prior `pre-release-repair-privacy-sync` work is complete and the worktree starts clean.
- [x] 0.2 Create an isolated maintenance branch from the current `main` baseline.
- [x] 0.3 Record baseline commit, version, rollback strategy, line counts, large functions, event areas, test entrypoints, and required validation commands.
- [x] 0.4 Run baseline `check_install` and core focused tests.

## 1. OpenSpec And FlowGuard Refactor Guard

- [x] 1.1 Create the OpenSpec proposal, design, specs, and tasks for behavior-preserving structure reduction.
- [x] 1.2 Add and run a focused FlowGuard structural-refactor process model with known-bad hazards.
- [x] 1.3 Validate the OpenSpec change strictly.

## 2. Event Entry Split

- [x] 2.1 Add `flowpilot_router_events.py` with a table-driven handler registry.
- [x] 2.2 Migrate stable event branches first: heartbeat/manual resume, stop/cancel, heartbeat binding, and route activation.
- [x] 2.3 Keep `_record_external_event_unchecked` as a thin compatibility entrypoint.
- [x] 2.4 Run migrated-event focused tests.

## 3. Controller Action Computation Split

- [x] 3.1 Add `flowpilot_router_action_providers.py` and provider ordering.
- [x] 3.2 Move lifecycle, pending action, card delivery, resume, startup, node loop, and closure action computation behind providers.
- [x] 3.3 Add provider-order tests and run controller/router-loop focused tests.

## 4. Controller Action Application Split

- [x] 4.1 Add `flowpilot_router_action_handlers.py` with an action-type registry.
- [x] 4.2 Move low-risk handlers for display sync, terminal summary, system-card delivery artifact commit, and passive wait handling.
- [x] 4.3 Add handler tests and run controller-action focused tests.

## 5. Test File Structure Split

- [x] 5.1 Add or expand domain test entry files for startup, resume, cards, packets, route mutation, closure, and controller/action behavior.
- [x] 5.2 Keep the legacy aggregate runtime test import path available during migration.
- [x] 5.3 Run full focused domain test commands and confirm helper reuse avoids broad duplication.

## 6. Router Runtime Domain Split

- [x] 6.1 Extract route activation/mutation helpers into a route-domain module.
- [x] 6.2 Extract one additional low-risk domain only after route-domain tests pass.
- [x] 6.3 Keep `flowpilot_router.py` as entrypoint/orchestration plus compatibility imports.
- [x] 6.4 Run route, resume/startup/card/closure focused tests for touched domains.

## 7. Meta/Capability Model Structure Split

- [x] 7.1 Split `meta_model.apply` into phase helper functions without changing state semantics.
- [x] 7.2 Split `capability_model.apply` into phase helper functions without changing state semantics.
- [x] 7.3 Run Meta and Capability checks using the background log contract when they are long-running, then inspect completion artifacts.

## 8. Install/Release Tooling Structure Split

- [x] 8.1 Split `scripts/check_install.py` main body into named check groups.
- [x] 8.2 Preserve the JSON output contract and severity semantics.
- [x] 8.3 Run install and public-boundary checks.

## 9. Final Sync

- [x] 9.1 Update HANDOFF, README, and FlowGuard adoption log with structure boundaries and validation evidence.
- [x] 9.2 Synchronize the local installed FlowPilot skill and audit source freshness.
- [x] 9.3 Run final focused tests, FlowGuard checks, install checks, and public-boundary privacy checks.
- [x] 9.4 Re-check peer/remote state, commit, and push the branch without tag/release/deploy.
- [x] 9.5 Run KB postflight and record reusable lessons.
