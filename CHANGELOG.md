# Changelog

All notable changes to FlowPilot will be documented in this file.

## 0.6.0 - 2026-05-09

### Added

- Added unified packet runtime session entrypoints so packet recipients can
  open assigned sealed packet bodies, record minimal open receipts, submit
  result bodies, and receive runtime-generated result envelopes through one
  controlled path.
- Added result review session support so reviewers and PM-authorized result
  readers can record sealed-result open receipts without exposing result bodies
  to the Controller.
- Added regression coverage for runtime-generated packet/result receipts,
  result ledger absorption, protocol-contract conformance, repair transaction
  handling, and router recovery from mechanical metadata gaps.

### Changed

- Changed router classification so missing mechanical receipts and role-key
  agent-id metadata gaps can be reissued to the responsible role instead of
  escalating to PM repair by default.
- Updated worker, officer, reviewer, PM, and Controller cards so normal role
  work uses the runtime session path and returns controller-visible envelopes
  instead of hand-written packet/result metadata.
- Kept reviewer quality findings as PM decision-support unless they expose a
  hard blocker, preserving PM ownership of route choice, waiver, repair, and
  completion decisions.

### Fixed

- Prevented valid-looking worker results from being blocked solely because the
  prompt path failed to write runtime receipt metadata.
- Preserved sealed-body boundaries while reducing audit noise: the runtime now
  records minimal positive proof of authorized opens rather than persistent
  access-attempt histories or first-open counters.
- Hardened protocol and repair models so same-class packet reissue and repair
  transaction failures are covered before release.

## 0.5.5 - 2026-05-09

### Added

- Added FlowGuard planning-quality model coverage for planning profiles,
  Skill Standard Contracts, skill-standard route/work-packet projection, and
  reviewer hard-blindspot blocking.
- Added FlowGuard reviewer active-challenge model coverage for checklist-only
  review passes, generic challenge actions, missing evidence or waiver,
  hard-issue residual downgrades, unverified core commitments, and blockers
  without reroute requests.
- Added required reviewer `independent_challenge` report fields so reviewer
  pass decisions include scope restatement, explicit and implicit commitments,
  failure hypotheses, task-specific challenge actions, findings, pass/block
  status, reroute requests, and waivers.

### Changed

- Updated PM planning, child-skill manifest, node-acceptance, packet, and
  result templates so compiled skill standards are projected into routes,
  work packets, reviewer gates, artifacts, and result matrices.
- Updated reviewer cards so PM packets are treated as the review floor rather
  than the review boundary.
- Registered the planning-quality and reviewer active-challenge runners in
  install, smoke, output-contract, card-coverage, and coverage-sweep checks.

### Fixed

- Repaired FlowPilot runtime cross-plane drift from the post-0.5.4 local
  source so repository and installed-skill audits can converge after sync.
- Fixed the FlowGuard coverage sweep to recognize result files declared with
  `Path(__file__).resolve().with_name(...)`.

## 0.5.4 - 2026-05-08

### Added

- Added output-contract model coverage for the PM model-miss triage decision
  and FlowGuard officer model-miss report contracts.

### Changed

- Gated reviewer-block repair behind PM model-miss triage so
  FlowGuard-modelable bug classes require officer same-class findings, candidate repair
  comparison, and a minimal sufficient repair recommendation before normal
  repair starts.
- Kept PM as the repair owner while making non-modelable cases record an
  explicit FlowGuard incapability reason before using the ordinary repair path.

## 0.5.3 - 2026-05-08

### Added

- Added FlowGuard resume-model coverage for router wake recording, visible plan
  restoration, six-role liveness preflight, and timeout-unknown handling.

### Fixed

- Changed heartbeat and manual mid-run wakeups to always re-enter the router
  resume path instead of trusting an old `work_chain_status=alive` claim.
- Required resume role rehydration receipts to record host liveness status,
  liveness decision, bounded wait result, and an explicit
  timeout-not-treated-as-active receipt.
- Added PM resume, parent-segment, and terminal-closure output contracts,
  router-delivered payload contracts, and copyable JSON templates so PM
  decisions cite current route memory without repair retries.
- Allowed fatal protocol control blockers to absorb PM-recorded corrected
  follow-up replay while preserving the fatal lane requirement for explicit PM
  recovery.
- Aligned smoke validation with the model gate by skipping the current live-run
  audit for control-plane friction checks.

## 0.5.2 - 2026-05-08

### Added

- Added a FlowGuard route-display lifecycle model covering startup, route draft,
  activation, node transition, repair return, Cockpit, and chat fallback display
  paths.

### Fixed

- Updated FlowPilot route-sign generation to read real route nodes from
  `flow.json`, `flow.draft.json`, or `route_state_snapshot.json`, including
  `node_id`, `active_route_id`, and `active_node_id` aliases.
- Changed display-plan sync to keep `display_plan.json` as the host/native plan
  projection while using the canonical Mermaid route sign as chat fallback once
  real route data exists.

## 0.5.1 - 2026-05-07

### Added

- Added a focused packet lifecycle FlowGuard model for envelope/ledger hash
  identity, packet/result open receipts, result ledger absorption, agent-id
  authority, and PM control-blocker follow-up resolution.

### Fixed

- Hardened packet runtime and router gates so forged envelope-only open
  markers, missing packet-ledger receipts, result envelopes without ledger
  absorption, role-string `completed_by_agent_id` values, and PM repair
  decisions without corrected follow-up events cannot advance packet work.
- Required PM research absorption to reference a passed packet-group runtime
  audit instead of only the reviewer report file.

## 0.5.0 - 2026-05-07

### Added

- Added a first-class GateDecision contract, router event, mechanical
  validation path, run-state record, and gate-decision ledger for PM,
  reviewer, and FlowGuard officer gate decisions.
- Added final-ledger collection of accepted GateDecision records.
- Added FlowGuard and unit-test coverage for GateDecision prompt fields,
  router mechanical validation, output-contract propagation, and card
  instruction coverage.

### Changed

- Updated PM, reviewer, process officer, product officer, and PM output
  contract catalog cards to require file-backed GateDecision bodies while
  keeping semantic sufficiency with PM/reviewer/officers instead of the router.
- Expanded the output-contract model to include valid GateDecision propagation.

### Fixed

- Preserved and released the post-0.4.1 control-plane fixes already in this
  checkout, including startup repair-cycle handling, startup fact ownership,
  material dispatch friction handling, live card context delivery, user-visible
  route signs, and control-blocker repair decision handling.

## 0.4.1 - 2026-05-06

### Added

- Added a command-refinement model and release checks for FlowPilot command
  folding candidates.
- Added CLI parsing coverage for all active router subcommands and explicit
  absence checks for retired high-risk folding commands.

### Changed

- Restored the unfolded router baseline and kept only the narrow
  `run-until-wait` startup fold that advances through internal router loading
  before stopping at the startup questions boundary.
- Updated the FlowPilot launcher guidance and smoke checks to use the safe
  startup fold instead of broader command-bundling shortcuts.

### Fixed

- Added copyable display-confirmation payload templates to router actions that
  require user-dialog display evidence, reducing rejected startup/display
  payload retries.
- Removed incomplete high-risk command folds that could break startup before
  FlowPilot reached the three-question pre-banner gate.
- Prevented retired fold commands such as `deliver-card-bundle-checked`,
  `relay-checked`, `prepare-startup-fact-check`, and
  `record-role-output-checked` from remaining exposed as CLI commands.

## 0.4.0 - 2026-05-06

### Added

- Added router artifact validation for node acceptance plans, packet
  envelopes, result envelopes, and role-output envelopes so PM and worker roles
  can repair missing fields in one pass before returning artifacts.
- Added controller-visible skill-observation reminders on router control
  blockers and router errors, with expanded observation categories for schema,
  router-state, ledger, heartbeat, display-projection, and controller
  compensation gaps.
- Added proof-backed `--fast` reuse for the slow FlowGuard meta and capability
  checks. Proof reuse is valid only when the model file, runner file,
  FlowGuard schema version, and result file still match a successful proof.
- Added focused tests for proof freshness, artifact validation, envelope alias
  handling, reviewer result-card gating, and display-plan advancement.

### Changed

- Tightened current-node review flow so reviewer pass/block decisions require
  the worker-result review card after the worker result is relayed to the
  reviewer.
- Normalized safe packet/result envelope aliases in the packet runtime,
  including `packet_body_path`, `packet_body_hash`, `body_path`, `body_hash`,
  `to_role`, and `next_holder`.
- Updated display-plan projection so completed nodes stay completed when the
  frontier advances to the next active node.
- Updated smoke checks to support proof-backed fast mode without changing the
  default full validation path.

### Fixed

- Prevented duplicated local background result snapshots from being published
  by ignoring `simulations/*.background_latest.json`.

## 0.3.1 - 2026-05-06

### Fixed

- Allowed PM-owned material understanding, product architecture, and root
  acceptance contract events to accept file-backed role payload envelopes using
  memo, architecture, contract, manifest, route, draft, plan, package, or
  ledger paths.
- Preserved role-output envelope metadata when PM file-backed material,
  architecture, and contract artifacts are written into the run directory.
- Added router runtime coverage for file-backed PM material understanding
  payloads.

## 0.3.0 - 2026-05-06

### Added

- Added the prompt-isolated FlowPilot router runtime, route-sign/user-flow
  diagram helpers, explicit next-recipient modeling, and broader router
  regression coverage.
- Added the physical packet runtime, barrier bundle support, packet envelope
  templates, and role-origin/holder checks for controller relay boundaries.
- Added route process/product officer cards, route challenge review, stronger
  role cards, and updated route templates for packet-driven execution.

### Changed

- Changed the `flowpilot` dependency source from repository-copy semantics to
  the public GitHub skill source while keeping a local checkout sync mode for
  development and self-checks.
- Reworked README positioning around FlowGuard models, packet mail, role
  authority, and router rhythm as the current source package shape.
- Expanded public release diagnostics to cover dependency source URLs,
  repository-owned local sync freshness, and active protocol residue checks.

### Fixed

- Removed machine-specific local paths from release-facing tracked files so
  public release checks pass without leaking workstation paths.
- Tightened install tooling so GitHub-sourced repo-owned skills can still be
  refreshed from the active checkout during local development.

## 0.2.1 - 2026-05-04

### Added

- Added PM-owned research packages so material, mechanism, source, validation,
  reconciliation, and experiment gaps must be assigned, reviewed, and absorbed
  before they can support route or product decisions.
- Added controller packet-gate evidence, including the run-local
  `packet_ledger` template and packet-control FlowGuard checks.
- Added repository backup artifacts for the previous installed `flowpilot`
  skill so rollback remains possible without deleting the new version.

### Changed

- Hardened the controller authority boundary: the controller relays PM,
  reviewer, officer, and worker packets but may not execute worker packets or
  self-approve role gates.
- Tightened PM product-function quality gates, high-standard node rechecks, and
  UI iteration budget guidance.
- Updated heartbeat/manual resume so continuation loads the packet ledger,
  requires PM `controller_reminder`, requires reviewer dispatch policy before
  worker execution, and blocks ambiguous worker state for PM recovery.
- Updated local install sync checks to require the legacy Cockpit prototype to
  be absent from the active tree before a clean UI restart.
- Updated install and local-sync audits to fail if retired external recovery
  scripts, prompts, or templates reappear in the active source tree.

### Removed

- Removed the previous native Cockpit prototype from the active source tree so
  the next Windows desktop UI can be rebuilt from scratch without reusing old
  UI assets or implementation code.
- Removed the retired external recovery scripts, Windows task helper, prompt,
  template, and obsolete findings page from the active source tree.

### Fixed

- Corrected README release/version language and the Chinese Cockpit section so
  both languages describe the current source package consistently.
- Removed post-`v0.2.0` changes from the `0.2.0` changelog section so the
  changelog matches the actual git tag boundary.
- Replaced the accumulated preflight findings page with the current effective
  FlowPilot continuation and startup boundaries so old recovery notes are not
  mistaken for live protocol.

## 0.2.0 - 2026-05-04

### Added

- Added the native Windows-oriented FlowPilot Cockpit package with a live route/task view, multi-task tabs, English/Chinese UI strings, settings, and support entry.
- Added `scripts/audit_local_install_sync.py` to verify repository-owned installed skills are source-fresh, installed skill names are not duplicated, and Cockpit source files are tracked before release.
- Added a `VERSION` file so release checks and documentation have a single current version marker.
- Added autonomous UI design rules for native desktop screenshot verification, concept/resource traceability, and real app icon realization checks.

### Changed

- Updated FlowPilot startup protocol from three questions to four by adding a display-surface choice: open Cockpit UI or continue with chat route signs.
- Updated the installer with `--sync-repo-owned` so repository-owned skills can be refreshed without pulling optional companion skills by default.
- Tightened release modeling so local install sync, duplicate installed skill names, and tracked Cockpit source are release gates.

### Fixed

- Made optional companion skill availability warning-only unless explicitly requested for installation.
- Removed stale release-version references and local absolute path leakage from release-facing documentation.

## 0.1.0 - 2026-05-02

Initial public source release.

### Added

- Published the `flowpilot` Codex skill.
- Added reusable `.flowpilot/` project-control templates.
- Added FlowGuard-backed simulations for process, capability, startup, and release-tooling checks.
- Added install, smoke, public-release, lifecycle, heartbeat, watchdog, busy-lease, and user-flow helper scripts.
- Added bilingual README positioning FlowPilot as FlowGuard-based finite-state project control.
- Added companion skill source metadata for FlowGuard, `model-first-function-flow`, `grill-me`, and `frontend-design`.
- Added minimal example material under `examples/minimal/`.

### Release Notes

- This is a source release. No binary assets are included.
- FlowPilot requires the real `flowguard` Python package; it does not vendor FlowGuard.
- Companion skills are referenced by source URL, but FlowPilot release tooling does not publish companion skill repositories.
