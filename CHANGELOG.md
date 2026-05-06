# Changelog

All notable changes to FlowPilot will be documented in this file.

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
