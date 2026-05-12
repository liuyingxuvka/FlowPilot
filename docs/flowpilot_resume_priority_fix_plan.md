# FlowPilot Resume Priority Fix Plan

## Goal

Heartbeat and manual resume are the control-plane reconnection gate. After a
wakeup is recorded, FlowPilot must reload current-run state, restore the visible
plan, rehydrate or replace the six role agents, and obtain the PM resume
decision before any old route work or active control blocker can proceed.

## Minimal Implementation Checklist

| Step | Change | Why it is required | Done signal |
| --- | --- | --- | --- |
| 1 | Add an explicit resume-priority rule to the resume FlowGuard model. | The current model protects resume loading and PM decision order, but does not model the active-control-blocker race that was observed at runtime. | Model has states for active blocker detection, deferral, and post-resume handling. |
| 2 | Add hazards for blocker-first resume failures. | The model must catch the exact bad class before production code changes. | Hazard checks fail known-bad states where a blocker is handled before load, before role rehydration, before PM resume decision, or is never returned to after resume. |
| 3 | Run the upgraded resume model before editing router code. | Confirms the intended order is internally consistent and still has progress paths. | `python simulations/run_flowpilot_resume_checks.py` passes after the new hazards are present. |
| 4 | Change router next-action priority so resume re-entry gates suppress old active blockers until PM resume decision returns. | Prompt text already says the right thing; the actual next-action selector currently lets `_next_control_blocker_action` win before `_next_resume_action`. | With `resume_reentry_requested=true` and no PM resume decision, next action is resume load/rehydration/cards/wait, not blocker handling. |
| 5 | Add router runtime regression tests. | The production selector needs a direct test for the current bug, not only an abstract model. | Tests cover active blocker before `load_resume_state`, before role rehydration, and after PM resume decision. |
| 6 | Run targeted checks after each meaningful patch, then broader checks before local sync. | Keeps this scoped and catches regressions while other agents may be changing nearby work. | Resume model, router runtime tests, install check, and relevant FlowGuard checks pass. |
| 7 | Sync the local installed FlowPilot skill only after the repo source passes. | The user wants the local installed version updated, but not remote GitHub. | `scripts/install_flowpilot.py --sync-repo-owned --json` and local sync check pass; no push is run. |

## Bug Risks This Change Must Catch

| Risk id | Possible new bug | Protected behavior | FlowGuard/model coverage | Runtime coverage |
| --- | --- | --- | --- | --- |
| R1 | A heartbeat wake sees an old active control blocker and handles it before `load_resume_state`. | Current-run state and ledgers must be loaded before any blocker work. | New hazard: `active_blocker_handled_before_resume_state_load`. | New router test expects `load_resume_state`. |
| R2 | A blocker wait/repair path starts after state load but before six-role liveness and rehydration. | Live role freshness must be known before PM or role work resumes. | New hazard: `active_blocker_waited_before_role_rehydration`. | New router test expects `rehydrate_role_agents`. |
| R3 | A blocker is handled after role rehydration but before PM resume decision. | PM owns the resume runway and must decide what to do with the old blocker. | New hazard: `active_blocker_handled_before_pm_resume_decision`. | New router test expects resume system cards and PM wait before blocker. |
| R4 | The fix hides or drops an existing active blocker permanently. | Old blockers are deferred, not cleared. | New hazard: `resume_completed_with_unhandled_active_blocker`. | New router test expects blocker handling after PM resume decision. |
| R5 | Resume priority blocks normal blocker handling when no resume is active. | Existing control-blocker behavior must remain unchanged outside heartbeat/manual resume. | Safe graph includes no-active-resume path where blocker handling is still legal. | Existing control-blocker tests continue to pass. |
| R6 | Resume priority skips manifest/card/PM wait boundaries and jumps straight to route work. | Resume cards, prompt manifest checks, and PM resume decision remain required. | Existing prompt/mail/PM ordering hazards remain active; new blocker deferral composes with them. | Existing resume runtime test continues to check cards and PM wait. |

## Intended Router Rule

When `resume_reentry_requested` is true and
`pm_resume_recovery_decision_returned` is false, the router is inside the
resume hard gate. During that period:

- `load_resume_state` has priority if resume state is not loaded;
- `rehydrate_role_agents` has priority if roles are not restored;
- resume system-card delivery and PM resume decision wait remain available;
- old `active_control_blocker` actions are suppressed, not deleted;
- once PM resume decision returns, normal blocker routing may resume.

## Validation Order

1. Compile the changed model and runner.
2. Run the upgraded resume model and confirm the known-bad hazards are detected.
3. Add router runtime tests and confirm they fail before the router priority fix.
4. Implement the minimal router priority fix.
5. Re-run the targeted resume model and router tests.
6. Run install/self-check and the relevant FlowGuard suites.
7. Sync the local installed skill and verify source/install freshness.
