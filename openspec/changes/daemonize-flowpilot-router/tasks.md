## 1. Model And Contract Preflight

- [x] 1.1 Add `simulations/flowpilot_persistent_router_daemon_model.py` covering Router daemon, Controller action ledger, mailbox evidence, receipts, locks, heartbeat recovery, and terminal shutdown.
- [x] 1.2 Add `simulations/run_flowpilot_persistent_router_daemon_checks.py` with JSON output support and known-bad hazard assertions.
- [x] 1.3 Model the live bug: PM bundle ACK exists and Router can continue, but no persistent daemon consumes it and Controller has stopped at a nonterminal wait.
- [x] 1.4 Model duplicate daemon startup and require the run-scoped lock to prevent two Router writers.
- [x] 1.5 Model duplicate ACK/result observations and require idempotent single consumption.
- [x] 1.6 Model Controller action ledger clearing and require Controller to rescan for pending dependency-satisfied actions after every receipt.
- [x] 1.7 Model terminal stop and require daemon, Controller ledger execution, heartbeat continuation, and role activity to stop cleanly.
- [x] 1.8 Run the new daemon model and inspect counterexamples before editing runtime code.

## 2. Router Daemon State And Lock Scaffolding

- [x] 2.1 Define run-scoped daemon files under `.flowpilot/runs/<run-id>/runtime/`: `router_daemon.lock`, `router_daemon_status.json`, and daemon event logs.
- [x] 2.2 Add Router helpers for acquiring, refreshing, detecting stale, and releasing the run-scoped daemon lock.
- [x] 2.3 Add Router helpers for writing daemon status with run id, lifecycle status, tick interval, last tick time, current wait summary, current action ledger summary, process id when available, and recovery hints.
- [x] 2.4 Add CLI support for an observation-only daemon mode that ticks every one second, writes status, and scans current wait state without advancing route state.
- [x] 2.5 Add tests proving duplicate daemon start refuses to become the writer while a live non-stale lock exists.

## 3. Mailbox Reconciliation In The Daemon Loop

- [x] 3.1 Reuse existing card ACK, card bundle ACK, report, packet ACK, result envelope, and return-ledger validation helpers inside the daemon loop.
- [x] 3.2 Enable daemon consumption of valid card ACKs and bundle ACKs while preserving existing hash, role, run id, delivery id, and expected path checks.
- [x] 3.3 Add idempotency keys so repeated ticks over the same ACK do not duplicate return events or route advancement.
- [x] 3.4 Extend daemon reconciliation to role reports and result envelopes after card/bundle ACKs are stable.
- [x] 3.5 Add runtime tests showing that a complete PM bundle ACK is consumed by daemon tick and advances to the next Router decision without a manual `next` call.
- [x] 3.6 Add runtime tests showing that incomplete, wrong-role, wrong-hash, or stale ACKs do not advance the run and produce the existing blocker/wait behavior.

## 4. Controller Action Ledger

- [x] 4.1 Define `controller_action_ledger.json`, `controller_actions/<action-id>.json`, and `controller_receipts/<action-id>.json` schemas.
- [x] 4.2 Add Router helpers to create Controller action entries with action id, action type, dependencies, allowed reads, allowed writes, visibility boundary, expected receipt path, and status `pending`.
- [x] 4.3 Add Router reconciliation of Controller receipts into ledger state, preserving status ownership rules.
- [x] 4.4 Convert Controller-required Router actions into action ledger entries instead of treating them as one-off foreground return values in daemon mode.
- [x] 4.5 Preserve diagnostic/manual CLI compatibility for `next` and `apply` when daemon mode is disabled or used for recovery.
- [x] 4.6 Add tests for multiple pending Controller actions, dependency ordering, missing receipts, blocked receipts, and duplicate receipts.
- [x] 4.7 Add tests proving Router never marks a Controller-required action `done` without a valid Controller receipt.

## 5. Controller Executor Loop

- [x] 5.1 Define the Controller executor protocol: fixed one-second ledger scan while the run is active.
- [x] 5.2 Update Controller behavior so it executes all pending dependency-satisfied actions, writes one receipt per action, and rescans the ledger after every completed receipt.
- [x] 5.3 Add Controller self-audit rules for missed pending actions, stale `in_progress` actions, dependency-satisfied actions not attempted, and receipts not reconciled by Router.
- [x] 5.4 Add Controller recovery behavior that reattaches to the current ledger rather than relying on chat history.
- [x] 5.5 Add tests or scripted smoke coverage for Controller clearing a ledger with more than one action.
- [x] 5.6 Add tests or scripted smoke coverage showing Controller does not final at ordinary card/bundle/packet/report/result waits while daemon mode is active.

## 6. Heartbeat And Manual Resume Recovery

- [x] 6.1 Update heartbeat prompt/request generation so heartbeat checks Router daemon liveness before route progress.
- [x] 6.2 If Router daemon is live, heartbeat must not start a second Router and must reattach Controller to the current action ledger.
- [x] 6.3 If Router daemon is dead or stale, heartbeat must restart daemon from current-run persisted state before any role or route work continues.
- [x] 6.4 Update manual resume to follow the same daemon, Controller, and role recovery path as heartbeat.
- [x] 6.5 Preserve six-role current-run memory rehydration and replacement rules after daemon/Controller recovery.
- [x] 6.6 Add tests for live daemon resume, stale daemon restart, missing Controller executor recovery, and missing role rehydration.
- [x] 6.7 Update terminal lifecycle reconciliation so user stop/cancel stops daemon active ticking, cancels/supersedes nonterminal Controller actions, pauses heartbeat, and closes role activity.

## 7. Prompt And Protocol Updates

- [x] 7.1 Update `skills/flowpilot/SKILL.md` so formal startup starts or verifies Router daemon, then attaches Controller to the Controller action ledger.
- [x] 7.2 Update `skills/flowpilot/assets/runtime_kit/cards/roles/controller.md` so Controller is a ledger executor and must not stop at ordinary nonterminal ACK/report/result waits.
- [x] 7.3 Update `skills/flowpilot/references/protocol.md` to make Router-owned waiting and Controller action ledger clearing the canonical control model.
- [x] 7.4 Update Controller resume/reentry cards to check daemon status, action ledger, and Controller receipts before role recovery or route work.
- [x] 7.5 Update PM, reviewer, worker, and officer role cards to clarify that roles write ACKs/reports/results to Router mailbox but do not directly advance Router.
- [x] 7.6 Update card/bundle check-in instructions so direct Router ACK means "write to Router mailbox"; Router daemon will consume it on a tick, and ACK is not semantic completion.
- [x] 7.7 Update packet body/result templates and active-holder instructions to mention Router daemon mailbox consumption and forbid Controller body reads.
- [x] 7.8 Extend prompt/source coverage checks so Controller prompt text that allows final stop at ordinary daemon-mode waits fails validation.

## 8. Startup, Display, And User-Facing Status

- [x] 8.1 Update startup bootstrap so daemon status is created before Controller core handoff when scheduled continuation or background agents are allowed.
- [x] 8.2 Update current status summary to show Router daemon status, current wait type, Controller ledger counts, and terminal/blocked state without sealed body content.
- [x] 8.3 Update Route Sign/status display rules so user-facing status is sourced from daemon status and current display summary.
- [x] 8.4 Add user-facing blocker messages for daemon lock conflict, stale daemon recovery, Controller ledger blockage, and terminal stop.

## 9. Validation And Install Sync

- [x] 9.1 Run the new persistent Router daemon FlowGuard checks and confirm known-bad hazards fail before the intended repair and pass after implementation.
- [x] 9.2 Run focused Router runtime tests for card/bundle ACK consumption, action ledger writing, receipt reconciliation, and terminal cleanup.
- [x] 9.3 Run focused card runtime and packet runtime tests to verify ACK/report/result files remain compatible.
- [x] 9.4 Run prompt/source coverage tests for Controller, roles, cards, packets, and heartbeat prompts.
- [x] 9.5 Run `python simulations/run_flowpilot_router_loop_checks.py --json-out simulations/flowpilot_router_loop_results.json`.
- [x] 9.6 Run `python simulations/run_flowpilot_resume_checks.py`.
- [x] 9.7 Run `python simulations/run_flowpilot_control_plane_friction_checks.py --json-out simulations/flowpilot_control_plane_friction_results.json`.
- [x] 9.8 Run `python simulations/run_flowpilot_event_contract_checks.py --json-out simulations/flowpilot_event_contract_results.json`.
- [x] 9.9 Run `python scripts/check_install.py`.
- [x] 9.10 Run local install sync and audit: `python scripts/install_flowpilot.py --sync-repo-owned --json`, `python scripts/audit_local_install_sync.py --json`, and `python scripts/install_flowpilot.py --check --json`.

## 10. Rollout And Fallback

- [x] 10.1 Start daemon mode behind a run-scoped `daemon_mode_enabled` flag for the first validation cycle.
- [x] 10.2 Keep manual `next`/`apply` CLI commands available for diagnostics and fallback when daemon mode is disabled.
- [x] 10.3 Add a documented fallback path that stops daemon mode, releases or marks stale lock state, and resumes the existing manual Router loop.
- [x] 10.4 Record FlowGuard adoption notes and OpenSpec task evidence after implementation.
