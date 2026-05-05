# FlowPilot Clean Rebuild Plan

Date: 2026-05-04

This plan tracks the prompt-isolated rebuild of FlowPilot itself. It is not a
formal FlowPilot run. No heartbeat automation, Cockpit launch, release, remote
push, or installed-skill synchronization is part of this plan unless a later
user request explicitly asks for it.

## Operating Rules

1. Preserve the second legacy backup under
   `backups/flowpilot-20260504-second-backup-20260504-195841/` and the
   matching zip archive. Cleanup must not delete it.
2. Keep `skills/flowpilot/SKILL.md` small. It is a launcher that runs the
   router and follows exactly one router action at a time.
3. Treat the router as a deterministic delivery controller, not as PM. The
   router computes the next allowed action, and the actor applies only that
   pending action.
4. Treat Controller as relay-only after startup. Controller may check manifests,
   check ledgers, deliver cards, relay mail, record status, and wait for role
   events. It must not infer route progress or inspect sealed bodies.
5. Deliver system cards only from the copied runtime kit, with
   `from: system`, `issued_by: router`, and `delivered_by: controller`.
6. Deliver ordinary role mail through the packet ledger. PM, reviewer, officers,
   and workers communicate through packet envelopes and result envelopes rather
   than broad prompt context.
7. Use FlowGuard before behavior-bearing protocol changes. Large simulations
   and regressions should run in background agents when available.

## Work Items

1. Record the legacy-to-router equivalence map.
   - Output: `docs/legacy_to_router_equivalence.md`.
   - Output: `docs/legacy_to_router_equivalence.json`.
   - Check: `scripts/check_install.py` verifies the JSON exists, parses, and
     all required old obligations are accounted for.

2. Repair the adoption log for the first clean-rebuild pass.
   - Record the background capability-model result that completed after the
     main-thread timeout.
   - Keep the unsynced installed-skill caveat visible.

3. Design heartbeat/manual-resume as a stable wake launcher.
   - Add a runtime card for Controller resume.
   - Add a runtime card for PM resume decision.
   - Add a small stable prompt template that loads persisted state and returns
     to the router.
   - Keep route/frontier state out of the heartbeat prompt body.

4. Model heartbeat/manual-resume with FlowGuard.
   - Model that wakeup loads current pointer, active run root, router state,
     prompt ledger, packet ledger, execution frontier, and crew memory.
   - Model crew restoration or replacement before PM resume decision.
   - Model that ambiguous state blocks for PM recovery.
   - Model that Controller cannot read sealed packet/result bodies or use chat
     history as route state.
   - Output: `simulations/flowpilot_resume_model.py`.
   - Output: `simulations/run_flowpilot_resume_checks.py`.
   - Output: `simulations/flowpilot_resume_results.json`.

5. Extend the router into the current-node packet loop.
   - Add route/frontier resolver state under the active run root.
   - Add PM packet issue events for material scan, product architecture, route
     model, current-node work, repair, final ledger, and closure.
   - Add reviewer dispatch and worker result events using the existing packet
     runtime.
   - Add explicit route mutation events that invalidate stale evidence and
     rewrite the frontier.
   - Add final ledger events that require current route scan, generated
     resource disposition, terminal backward replay, and PM completion approval.

6. Complete missing runtime cards.
   - Material scan and research package cards.
   - Product-function architecture and route-skeleton cards.
   - Child-skill selection and gate extraction cards.
   - FlowGuard officer modeling request and report cards.
   - Current-node work, worker implementation, worker repair, and reviewer
     recheck cards.
   - Route mutation and stale-evidence cards.
   - Final ledger, terminal replay, closure, and role-memory archive cards.

7. Add implementation validators.
   - Router pending-action validator.
   - Prompt manifest validator.
   - Packet ledger and chain validator.
   - Role isolation validator.
   - Runtime kit card coverage validator.
   - Legacy equivalence coverage validator.
   - Backup preservation validator.

8. Expand FlowGuard coverage.
   - Startup prompt isolation.
   - Heartbeat/manual resume.
   - Packet loop.
   - Route mutation.
   - Final ledger.
   - Legacy equivalence/refinement from old protocol obligations to new
     router/card artifacts.

9. Run verification.
   - Fast checks in the main thread: compile, unit tests, install self-check.
   - Heavy checks in background agents: meta model, capability model, expanded
     resume/prompt/packet models.
   - Main thread integrates failures and reruns the narrow failed checks.

10. Finish documentation and KB postflight.
    - Update `HANDOFF.md`.
    - Update `docs/flowguard_adoption_log.md`.
    - Record one predictive-KB postflight observation if the work exposed a
      reusable lesson or route/card weakness.

## Current Status

The ten-step clean-rebuild pass is implemented in the repo source.

Completed runtime coverage now includes the small launcher, router, runtime
kit, second backup, prompt-isolation model, install checks, startup and resume
cards, material and research packet loops through physical packet envelopes,
current-node packet relay, reviewer-pass gating before PM node completion,
parent backward replay for route nodes with children, route-mutation frontier
rewrites after reviewer blocks, PM evidence/resource/quality ledgers, UI/visual
evidence freshness checks, PM resume-decision recovery, PM final route-wide
ledger writing, reviewer terminal backward replay, and closure-card gating.

Foreground checks passed:

- `python -m py_compile skills\flowpilot\assets\flowpilot_router.py scripts\check_install.py tests\test_flowpilot_router_runtime.py`
- `python -m unittest tests.test_flowpilot_router_runtime`
- `python scripts\check_install.py`

Heavy meta, capability, prompt-isolation, resume, router-loop, and broad unit
regressions passed through background agents:

- broad unit regression: 58 tests
- prompt isolation: 349 states, 348 edges, 54 hazards detected
- resume: 129 states, 128 edges, 1986 traces, zero violations
- router loop: 91 states, 90 edges, 5199 traces, zero violations
- meta model: 578663 states, 598835 edges, zero invariant failures
- capability model: 550013 states, 575473 edges, zero invariant failures

The global installed Codex `flowpilot` skill was then refreshed from this repo
with `python scripts\install_flowpilot.py --sync-repo-owned --json`; both
`audit_local_install_sync.py --json` and `install_flowpilot.py --check --json`
now report `source_fresh: true`.

Known residual expansion areas after this rebuild are generalized async officer
modeling packets, automatic multi-node traversal beyond the current active-node
resolver, richer old-state import quarantine for continuation runs, and
closure-suite lifecycle writing.
