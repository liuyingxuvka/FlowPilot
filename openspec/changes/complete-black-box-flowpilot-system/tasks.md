## 1. Contract And Preflight

- [x] 1.1 Verify real FlowGuard import, package version, and project adoption audit.
- [x] 1.2 Run predictive KB preflight and record overclaim/scoped-confidence lessons for this route.
- [x] 1.3 Create the complete-system OpenSpec proposal, design, and specs.
- [x] 1.4 Validate the complete-system OpenSpec change strictly before implementation.
- [x] 1.5 Run `openspec validate --all --strict` after all spec artifacts and before broad confidence.

## 2. FlowGuard Development And Structure Models

- [x] 2.1 Add a complete-system FlowGuard development-process model covering model, code, UI, host, fake-agent, historical replay, live-run, install, and git gates.
- [x] 2.2 Add a complete-system FlowGuard code-structure model mapping FunctionBlocks to runtime modules and validation boundaries.
- [x] 2.3 Add a complete-system UI-flow model for startup intake, Cockpit/status, chat fallback, pause/resume/stop, and sealed-body isolation.
- [x] 2.4 Add a complete-system TestMesh model separating routine, release, background, historical replay, and live-host evidence.
- [x] 2.5 Add model-test alignment evidence mapping complete-system requirements to focused tests.
- [x] 2.6 Add no-write/routine runners and result artifacts for all complete-system FlowGuard models.

## 3. Complete Runtime State And Router

- [x] 3.1 Extend `ai_project_runtime` with a run-shell abstraction for `.flowpilot/current.json`, `.flowpilot/index.json`, and `.flowpilot/runs/<run-id>/`.
- [x] 3.2 Add typed event records and append-only event history for startup, route, packet, lease, FlowGuard, review, UI, lifecycle, validation, and closure actions.
- [x] 3.3 Extend the ledger schema to cover route mutation, lifecycle, Cockpit projection, host driver state, imported evidence, and cutover gates.
- [x] 3.4 Extend deterministic router next-action selection for startup intake, contract freeze, route drafting, FlowGuard work orders, packet execution, review, repair, route mutation, resume, UI projection, and closure.
- [x] 3.5 Add mechanical blockers for old-state authority, stale projection authority, stale unowned result replay, wrong modeled target, self-review, lease timeout, body hash mismatch, and progress-only completion.

## 4. Dynamic Host And Responsibility Leases

- [x] 4.1 Add a host-driver interface with deterministic fake-host, dry-run host, and live-host evidence boundaries.
- [x] 4.2 Implement dynamic responsibility leases for PM, reviewer, explicit FlowGuard officer, worker, research worker, and UI/QA worker responsibilities.
- [x] 4.3 Add lease replacement, expiration, close, supersede, and late-output quarantine behavior.
- [x] 4.4 Add role-memory/current-run seeding records that allow replacement without trusting old agent ids.
- [x] 4.5 Add host evidence rows that distinguish fake, dry-run, and real live background-agent confidence.

## 5. FlowGuard Work-Order Runtime

- [x] 5.1 Extend the modeled-target scheduler with complete-system targets and required selected skills.
- [x] 5.2 Add FlowGuard work-order envelope/body persistence under the current run.
- [x] 5.3 Add officer-owned report records with model target, selected skill, proof artifacts, confidence boundary, PM decision, and stale-evidence behavior.
- [x] 5.4 Add rejection paths for missing target, wrong target, report-only confidence, stale proof artifacts, and skipped checks.

## 6. Startup Intake And Cockpit Operation Surface

- [x] 6.1 Reuse or adapt the existing startup intake panel so it writes sealed current-run intake evidence.
- [x] 6.2 Add a public status projection model that renders route stage, packets, leases, FlowGuard orders, blockers, validation rows, lifecycle state, and closure status without sealed bodies.
- [x] 6.3 Add a minimal Cockpit/status command surface for pause, resume, stop, open logs, refresh, and chat fallback events.
- [x] 6.4 Add UI-flow tests proving Cockpit is projection-only and cannot directly mutate canonical state.
- [x] 6.5 Add chat route-sign fallback rules when Cockpit is unavailable.

## 7. Review, Repair, Route Mutation, And Closure

- [x] 7.1 Add independent review report records with reviewer lease identity, direct evidence, scope restatement, failure hypotheses, pass/block decision, waivers, and PM routing decision.
- [x] 7.2 Add route mutation records that supersede stale packets/results and require affected replay or rebinding.
- [x] 7.3 Add parent backward replay and final backward closure records over active route, accepted results, review, FlowGuard, validation, and unresolved gaps.
- [x] 7.4 Add closure blockers for completion-report-only approval, unresolved resources, unresolved residual risks, stale validation, and old UI/visual evidence.

## 8. Migration, Install, And Cutover

- [x] 8.1 Add migration/import helpers that classify old FlowPilot files as reference, negative-test, diagnostic, or imported read-only evidence.
- [x] 8.2 Add cutover gate evidence that blocks preferring the new runtime until complete-system validation, install sync, and git evidence are current.
- [x] 8.3 Update install inventory to include new complete-system runtime, models, result artifacts, and tests.
- [x] 8.4 Update version and changelog after implementation scope is known.
- [x] 8.5 Sync repo-owned FlowPilot skill into the local installed skill and run install audit/check in serialized order.

## 9. Tests And Regressions

- [x] 9.1 Add focused tests for run-shell persistence, event history, router decisions, lease behavior, host evidence, Cockpit projection, FlowGuard work orders, review, route mutation, and closure.
- [x] 9.2 Add fake-agent multiround and chaos tests for dead workers, late outputs, duplicate outputs, route mutation, wrong FlowGuard target, stale evidence, progress-only background logs, and Cockpit disconnect.
- [x] 9.3 Add historical bad-case replay rows for ACK-only completion, stale display projection, stale unowned package disposition, wrong FlowGuard target, stale result artifacts, and background progress-only confidence.
- [x] 9.4 Add live-host readiness tests that block full live confidence when real host evidence is missing.
- [x] 9.5 Run focused pytest, OpenSpec validation, complete-system model runners, existing protocol/runtime checks, and relevant existing FlowPilot regression tests.
- [x] 9.6 Launch heavyweight Meta and Capability checks in background artifacts and inspect exit/proof artifacts before claiming release/full-system confidence.

## 10. Completion Audit And Git

- [x] 10.1 Run final `git status`, review intended scope, and avoid unrelated changes.
- [x] 10.2 Run final install sync/audit/check after all code/test changes.
- [x] 10.3 Run final complete-system confidence gate and verify every explicit requirement has direct evidence.
- [x] 10.4 Commit the local git result without push, tag, release, deploy, or secret handling.
- [x] 10.5 Record FlowGuard adoption log and KB postflight observations for reusable route lessons.
