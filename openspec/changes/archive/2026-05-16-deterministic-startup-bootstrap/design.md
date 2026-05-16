## Context

FlowPilot startup currently has a minimal bootloader, a startup daemon, a
Router scheduler ledger, a Controller action ledger, and Controller receipts.
Recent fixes made the daemon schedule startup rows before Controller core.
However, deterministic setup actions such as placeholder filling, mailbox
creation, user-request recording, and user-intake scaffold creation do not need
AI judgment or Controller work. Modeling them as scheduled Controller rows
creates duplicate ownership: startup-specific completion can mark a row
reconciled, while the generic receipt reconciler can later treat the same
receipt as unsupported and create a false PM blocker.

The user-approved direction is to reduce startup to one deterministic bootstrap
seed plus one unified scheduler/reconciliation path.

## Optimization Inventory

| Order | Optimization point | New owner | Output | Verification |
| --- | --- | --- | --- | --- |
| 1 | Create run shell, current pointer, run index, runtime directories, and empty ledgers | Bootstrap seed script | Run foundation and bootstrap evidence | Files exist, JSON parses, schemas match |
| 2 | Fill startup placeholders and startup-answer records | Bootstrap seed script | `startup_answers.json` and related bootstrap records | Required fields present and linked to run id |
| 3 | Initialize mailbox, packet ledger, prompt delivery ledger, card ledgers, and protocol ledgers | Bootstrap seed script | Empty ledgers and directories | Required ledger schemas and paths exist |
| 4 | Record raw user request or startup-intake reference and write user-intake scaffold | Bootstrap seed script | `user_request.json` and `mailbox/outbox/user_intake.json` | Body visibility and sealed/ref fields match source |
| 5 | Start unified Router scheduler only after seed success | Router daemon | Scheduler and Controller ledgers active | Seed evidence is complete before first row |
| 6 | Schedule only non-deterministic startup obligations | Router scheduler | Role slots, heartbeat binding, Controller core rows | Deterministic action types are absent from scheduler |
| 7 | Reconcile every scheduled row through one generic receipt/postcondition path | Router reconciler | `reconciled` rows or real blockers | Idempotent second pass does not emit blockers |
| 8 | Sync repository result into installed FlowPilot copy and local git | Installer/check scripts and git | Installed skill matches repo, git records change | Install checks and git status/stage/commit evidence |

## Risk Catalog

| Risk ID | Possible bug from this optimization | Why it matters | Required FlowGuard coverage |
| --- | --- | --- | --- |
| R1 | Scheduler starts before bootstrap seed writes all required files | Router may operate on missing ledgers | Model must reject scheduler activation before seed proof |
| R2 | Bootstrap seed silently skips a file but reports success | Later startup fails far from root cause | Model must require per-artifact proof before seed success |
| R3 | Deterministic file setup remains duplicated as Controller rows | Same false PM blocker class can return | Model must reject deterministic action types in scheduler rows |
| R4 | Seed creates PM blocker on foundation failure | PM receives a route repair before a route exists | Model must reject PM blocker before scheduler route start |
| R5 | Generic reconciler still creates a blocker after a row is reconciled | Idempotency failure and false blocker | Daemon reconciliation model must reject blocker after reconciled |
| R6 | Startup role/heartbeat/core work bypasses the scheduler | Work becomes untracked and unreconciled | Model must require non-deterministic startup work to be scheduled |
| R7 | User request or intake body visibility is weakened | Controller may see sealed/private user body content | Model/tests must require ref/sealed visibility rules |
| R8 | Startup failure is hidden as success | FlowPilot can continue from invalid foundation | Model must require failure terminal before scheduler when seed proof fails |
| R9 | Local install sync copies a stale version | User runs old behavior despite repo fix | Final checks must verify installed skill freshness |
| R10 | Peer-agent changes are overwritten | Parallel work is lost | Use narrow edits and inspect git status before each implementation slice |

## FlowGuard Coverage Matrix

| Planned change | Modeled state/events | Known-bad hazards that must fail | Safe path that must pass |
| --- | --- | --- | --- |
| Bootstrap seed writes foundation | `seed_started`, `foundation_files_written`, `seed_proof_written`, `seed_success` | `scheduler_before_seed_success`, `seed_success_without_all_artifacts`, `seed_failure_as_pm_blocker` | `deterministic_seed_creates_foundation_then_scheduler_starts` |
| Remove deterministic Controller rows | `scheduler_rows`, `deterministic_action_in_scheduler` | `deterministic_setup_left_as_controller_row` | `scheduler_contains_only_startup_obligations` |
| Unified reconciliation | `row_reconciled`, `receipt_seen_again`, `control_blocker_written` | `reconciled_row_false_pm_blocker`, `unsupported_startup_receipt_escalated_to_pm` | `receipt_replay_idempotently_skips_reconciled_row` |
| Startup obligations remain scheduled | `role_slots_scheduled`, `heartbeat_scheduled`, `controller_core_scheduled` | `role_slots_bypass_scheduler`, `controller_core_loaded_before_seed_and_scheduler` | `obligations_schedule_after_seed` |
| User request/intake handled by seed | `user_request_source`, `body_visibility`, `intake_scaffold_written` | `controller_reads_sealed_user_body`, `intake_written_without_user_request_ref` | `seed_records_request_ref_and_intake_scaffold` |
| Install and git sync | `repo_changed`, `installed_synced`, `git_recorded` | `installed_skill_stale_after_fix` | `repo_install_check_git_ready` |

## Goals / Non-Goals

**Goals:**
- Keep only one real Router scheduler/reconciliation system after startup
  foundation exists.
- Make deterministic startup file work code-owned, auditable, and repeatable.
- Prevent false PM blockers for already reconciled startup work.
- Keep startup obligations that need waiting or host/AI work in the scheduler.
- Preserve peer-agent changes by editing only the startup/bootstrap and focused
  model/test surfaces.

**Non-Goals:**
- Do not redesign PM/Reviewer/Worker protocol.
- Do not run heavyweight Meta or Capability simulations in this task.
- Do not push or publish remotely.
- Do not remove the Router daemon or the two-table scheduler.

## Decisions

1. Use a deterministic bootstrap seed, not an AI Controller row, for pure file
   setup.
   - Rationale: these actions are local, deterministic, and required before
     Controller work is meaningful.
   - Alternative rejected: keep them as startup Controller rows and add skip
     guards. That fixes the immediate bug but preserves duplicate ownership.

2. Treat seed failure as startup failure, not PM repair.
   - Rationale: PM repair lanes are route-level mechanisms; before the
     scheduler and Controller core exist, there is no valid PM repair owner.
   - Alternative rejected: create a PM blocker from seed failure. That repeats
     the same category error.

3. Keep role slots, heartbeat binding, and Controller core in the scheduler.
   - Rationale: these actions need host interaction, waiting, or explicit
     postcondition reconciliation.
   - Alternative rejected: put all startup work in the seed. That would hide
     non-deterministic work and weaken auditability.

4. Use one generic reconciliation path for scheduled rows.
   - Rationale: scheduled rows should not care whether they are startup or
     normal work; postcondition contracts and row state decide completion.
   - Alternative rejected: startup-specific final reconciliation owner. That is
     the duplicate path that caused the false blocker.

## Risks / Trade-offs

- Bootstrap seed becomes larger -> keep it limited to deterministic file work
  and protect it with FlowGuard plus focused runtime tests.
- Some existing tests expect deterministic startup actions in Controller
  ledgers -> update tests to assert bootstrap evidence instead.
- A partial refactor could leave both paths active -> add model hazards and
  runtime regression tests for deterministic rows in the scheduler.
- Heavyweight models are skipped -> record the residual risk and run focused
  models/tests that own this boundary.

## Migration Plan

1. Complete the FlowGuard model hardening gate.
2. Update the bootstrap model and daemon reconciliation model before production
   code changes.
3. Refactor startup seed creation in small slices.
4. Remove deterministic startup action rows from daemon scheduling.
5. Simplify receipt reconciliation so startup scheduled obligations use the
   generic path and already reconciled rows are idempotent.
6. Update focused tests after each slice.
7. Sync the installed FlowPilot skill and run install freshness checks.
8. Record adoption and KB postflight.
