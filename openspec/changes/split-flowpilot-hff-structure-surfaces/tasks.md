## 1. StructureMesh Planning

- [x] 1.1 Inspect the four deferred split parents and derive child-module ownership for each.
- [x] 1.2 Record the FlowGuard StructureMesh/DevelopmentProcessFlow route snapshot and minimum revalidation plan.

## 2. HFF Parent Splits

- [x] 2.1 Split `simulations/run_flowpilot_core_runtime_checks.py` into a thin runner plus focused child ownership.
- [x] 2.2 Split `simulations/run_flowpilot_information_flow_alignment_checks.py` into a thin runner plus focused child ownership.
- [x] 2.3 Split `skills/flowpilot/assets/flowpilot_new.py` into a thin current-contract entrypoint plus focused child ownership.
- [x] 2.4 Split `scripts/flowguard_project_topology.py` into a thin CLI plus focused topology child ownership.

## 3. Focused Validation

- [x] 3.1 Run syntax/import checks for all touched parent and child modules.
- [x] 3.2 Run focused runtime, information-flow alignment, and topology tests.
- [x] 3.3 Fix any focused validation failures before broader evidence refresh.

## 4. FlowGuard Evidence Refresh

- [x] 4.1 Regenerate model-test alignment results and confirm the four deferred split findings are closed.
- [x] 4.2 Regenerate the full coverage inventory and human report.
- [x] 4.3 Rebuild and check the FlowGuard project topology.
- [x] 4.4 Audit models, tests, prompts, cards, and entrypoints for old FlowPilot paths, fallback/compatibility branches, legacy field aliases, and historical-artifact promotion.
- [x] 4.5 Run fake AI package, synthetic chaos, red-team, dry-run, shadow-launcher, historical replay, and PromptStore regressions.
- [x] 4.6 Run heavyweight Meta and Capability checks through the background log contract and inspect final artifacts.

## 5. Install And Git Synchronization

- [ ] 5.1 Run repository-owned FlowPilot install sync.
- [ ] 5.2 Run install check and installed freshness audit in order.
- [ ] 5.3 Recheck local git state and stage/commit only this change's owned files, or report git completion blocked by peer edits.

## 6. Closure

- [ ] 6.1 Update adoption logs with trigger, commands, evidence, skipped steps, findings, and remaining blockers.
- [ ] 6.2 Run OpenSpec validation/status checks and mark all completed tasks.
- [ ] 6.3 Perform predictive KB postflight and record any reusable lesson exposed by this pass.
