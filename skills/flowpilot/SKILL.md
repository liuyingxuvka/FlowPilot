---
name: flowpilot
description: Opt-in only. Use this skill only when the user explicitly asks to use FlowPilot or the flowpilot skill, for example "Use FlowPilot" or "使用 FlowPilot"; do not activate implicitly for large tasks, existing .flowpilot directories, UI redesigns, heartbeat requests, or repository work.
---

# FlowPilot

FlowPilot is a prompt-isolated router skill. This file stays small so activation does not load the full project-management protocol into main context.

## Activation Boundary

Use FlowPilot only after an explicit user request in the current thread. If the user is editing, auditing, discussing, or repairing this skill, treat that as ordinary repository work unless they ask to run a formal FlowPilot route.

Do not infer activation from task size, repository type, UI work, heartbeat language, or `.flowpilot/`.

## Dependency Bootstrap

Before a formal FlowPilot run, verify the required dependencies:

- real `flowguard` Python package from `https://github.com/liuyingxuvka/FlowGuard`;
- installed/readable `model-first-function-flow` skill;
- installed/readable `grill-me` skill;
- this `flowpilot` skill.

If this skill was installed from the full repository, prefer:

```powershell
python scripts\install_flowpilot.py --install-missing --install-flowguard
```

If only the skill directory is available, read `DEPENDENCIES.md` in this skill folder and ask before making heavy/global environment changes. Optional UI/design companions are not required for non-UI runs.

## Required Launcher Behavior

Before the daemon is started or attached, the assistant is only the FlowPilot bootloader. The bootloader may manually run the router only for minimal pre-daemon startup actions: create the run shell, write the current pointer, update the run index, and start or attach the Router daemon. After `start_router_daemon` succeeds, do not keep progress alive by manually looping back to Router commands; attach to daemon-owned status and the Controller action ledger, process exposed Controller rows, write receipts, and otherwise stay in standby.

Do not read FlowPilot reference files, old route state, old screenshots, old UI assets, old prompt bodies, or runtime kit cards unless the router action explicitly names them.

Fresh formal invocation:

```powershell
python skills\flowpilot\assets\flowpilot_router.py --root <project-root> --json run-until-wait --new-invocation
```

Manual diagnostic/repair commands:

```powershell
python skills\flowpilot\assets\flowpilot_router.py --root <project-root> --json next
python skills\flowpilot\assets\flowpilot_router.py --root <project-root> --json apply --action-type <action_type>
python skills\flowpilot\assets\flowpilot_router.py --root <project-root> --json run-until-wait
```

Use `run-until-wait` only before daemon takeover, for diagnostic, test, or explicit repair. In daemon mode, it is not the normal progress command after a row, wait, heartbeat, role response, or unclear next step; normal progress comes from daemon-owned status plus the Controller action ledger.

Formal startup creates only the minimal run shell, current pointer, and run index before it starts or attaches the built-in one-second Router daemon. The daemon is bound to that run's `run_id`/`run_root`; `.flowpilot/current.json` is UI focus/default-target metadata, not authority for later daemon ticks. The daemon then schedules startup UI, role startup, heartbeat, and Controller-core handoff rows through the ordinary Controller action ledger plus Router scheduler ledger. There is no startup option to disable it; if live daemon lock/status/ledger evidence is missing, startup must fail instead of bypassing daemon-driven startup.

During formal runtime, Router owns ordinary waiting through `runtime/router_daemon_status.json` and `runtime/controller_action_ledger.json`; Controller clears that ledger with `controller-receipt` and stays attached. `next`, `apply`, and `run-until-wait` remain diagnostic, test, and explicit repair tools, not the normal metronome that keeps a run alive.

Router-ready state preempts foreground waits. After Controller relays or observes router-authored work, scan daemon status and the Controller action ledger before waiting on any role or subagent. Use `controller-standby` semantics to consume Router-ready Controller rows before any foreground role wait. During a nonterminal active run, the foreground Controller does not end: `foreground_required_mode=process_controller_action` means do the queued Controller work, and `foreground_required_mode=watch_router_daemon` means keep the `continuous_controller_standby` row in progress, sync the visible Codex plan from the ledger, and run `python skills\flowpilot\assets\flowpilot_router.py --root . --json controller-patrol-timer --seconds 10`. This patrol exists to prevent accidental foreground exit while FlowPilot is still running. Wait for the command output; if it returns `continue_patrol`, immediately run the same command again and wait for the next output. Starting or restarting the command is not completion. One poll, a live target role, or diagnostic `timeout_still_waiting` does not complete standby. If Router exposes `send_wait_target_reminder`, send only the Router-authored `reminder_text` to the named waiting role, do not edit it or read sealed bodies, and write the Controller receipt with the matching reminder hash and liveness fields. Only terminal status with `controller_stop_allowed: true` may end the Controller role.

A Controller receipt is local Controller evidence only; Router must reconcile it into Router-owned workflow facts before progress is counted. For mail delivery, progress is counted only after Router folds the receipt into the mail ledger and the packet runtime ledger shows the packet released to the addressed role with a controller relay signature.

When the router returns `open_startup_intake_ui`, open the native startup intake UI with the command and output directory in the action envelope. Formal startup must use the interactive native UI result produced by that window. Do not satisfy this action with headless auto-confirmation, scripted result synthesis, chat-text substitution, direct JSON creation, or any other non-interactive intake. If the UI cannot be opened or does not return an interactive result, stop and report the startup UI failure instead of continuing. After the UI closes, return to Router daemon status and the Controller action ledger before continuing. Do not paste the user's work request into chat, do not include body text in the router payload, and do not continue if the UI result status is `cancelled`.

The UI result replaces the old chat three-question startup boundary. The router maps the UI toggles to canonical startup answer enum fields and seals the work request body behind a path/hash record. The startup UI record is the authority for activation; reviewer live review checks `startup_intake/startup_intake_record.json`, its receipt/envelope/hash evidence, and independently observable startup facts requested by the router, not private chat authenticity or chat history.

Startup progress uses the same two-table rule as later runtime work: Controller checks off simple ledger rows, while Router owns order, barriers, scope reconciliation, and ACK joins. Router may dispatch independent startup PM prep cards before Reviewer live review, but Reviewer startup fact review starts only after current startup-scope rows, receipts, required postconditions, and pre-review card ACKs are clear; PM startup activation then uses the ordinary same-role `pm.startup_activation` ACK rule, not a second all-startup join.

The startup banner and FlowPilot Route Sign are user-facing display text. When a direct pending action returns `display_text`, paste that exact text into chat before applying that direct pending action. When the same display work appears as a Controller ledger row, paste the text into chat before writing the row's `controller-receipt`, and put the display confirmation in the receipt payload. Do not add display-gate, evidence, source-health, confirmation, or controller/audit metadata to the user-visible body; those details belong in packets, ledgers, and action payloads. Generated files, paths, flags, and state records do not count.

When no Cockpit/UI surface is open, show the router's public route sign together with the current status summary. Use only `current_status_summary.json` and public route-display text for that summary; do not show evidence tables, source fields, hashes, or sealed packet/result body details. When the Cockpit/UI surface is open, let the UI render the same status summary and keep chat updates short.

When the router returns `record_user_request` after a native startup intake result, apply it with no payload; the router will materialize the sealed UI record into the run and create the PM-bound `user_intake` packet. Only use the legacy `payload.user_request.text` path when the action envelope explicitly requires `requires_payload: user_request`.

When the router returns `start_role_slots` with `requires_host_spawn: true`, spawn all six requested role agents before completing the action. For a direct pending action, apply it with the required payload. For a Controller ledger row, write `controller-receipt` with one current `agent_id` per requested role, `model_policy: strongest_available`, `reasoning_effort_policy: highest_available`, `spawn_result: spawned_fresh_for_task`, `spawned_after_startup_answers: true`, and current `spawned_for_run_id` in the receipt payload. Every background role agent must be explicitly requested with the strongest available host model and the highest available reasoning effort; do not rely on inheriting the foreground/Controller model. Do not treat empty role slots, prior-route agent IDs, or later on-demand subagents as startup success.

When a heartbeat or manual mid-run wakeup occurs, always record `heartbeat_or_manual_resume_requested`, then attach to daemon status, daemon lock evidence, and the Controller action ledger for the current run. If the daemon is live, process only exposed Controller rows or stay in standby; if it is missing or stale, use the explicit daemon repair/restart path. Treat any supplied `work_chain_status` as diagnostic only; never use `alive`, `active`, or a `wait_agent` timeout to skip `load_resume_state`.

When the router returns `rehydrate_role_agents` with `requires_host_spawn: true`, perform the six-role liveness preflight named by the action, then restore or spawn all six role agents before completing it. Direct pending actions still use apply. Controller ledger row completions use `controller-receipt` with the rehydration evidence in the receipt payload. Every restored or replacement background role agent must be explicitly requested with the strongest available host model and the highest available reasoning effort; do not rely on inheriting the foreground/Controller model during heartbeat, manual resume, liveness recovery, or missing-agent replacement. Give each role its listed core prompt and current-run memory/context; PM must receive the PM resume context. Echo `model_policy: strongest_available`, `reasoning_effort_policy: highest_available`, memory/core hashes, resume tick, host liveness status, liveness decision, bounded wait result, and the timeout-not-active receipt in `rehydrated_role_agents`. If an agent is missing, cancelled, unknown, or `timeout_unknown`, spawn a replacement from current-run memory instead of continuing to wait on that old agent.

When the router returns `create_heartbeat_automation`, create the requested Codex heartbeat with the router-provided name, prompt, schedule, and thread destination before completing it. Direct pending actions still use apply. Controller ledger rows use `controller-receipt` with the real `host_automation_id`, `host_automation_verified: true`, `route_heartbeat_interval_minutes: 1`, and a `host_automation_proof` receipt bound to the current `run_id`; never mark scheduled continuation active from a file, name guess, or self-attested status.

When the router returns a `payload_contract`, satisfy it exactly or return to the named role/user for missing fields. Do not guess missing payload fields or repair a rejected payload in Controller.

## Controller Boundary

After the router loads Controller core, the main assistant is Controller only. Controller may check the prompt manifest, check the packet ledger, deliver system cards, relay Router-authorized packet/result/role-output envelope metadata, update status, scan the Router daemon status and Controller action ledger, wait through `controller-patrol-timer`, and write Controller receipts. Controller may call `flowpilot_router.py next/apply/run-until-wait` only for diagnostics, tests, or explicit repair/recovery; normal progress comes from the daemon-owned status and ledger.

Controller must not:

- implement product work;
- write project evidence for a worker node;
- approve gates;
- mark route nodes complete;
- mutate the route from its own judgement;
- read, summarize, execute, edit, or repair sealed packet/result bodies.
- receive, write, relay as the return receiver, or submit system-card ACKs, active-holder packet ACKs, active-holder packet completions, or formal role outputs.

When the router returns a control blocker, Controller may deliver only the public blocker id plus sealed repair packet path/hash to the target role. Controller must not read, restate, or patch sealed repair details.

When the user asks to stop or cancel the active run, record `user_requests_run_stop` or `user_requests_run_cancel`, then follow the terminal lifecycle action. Do not continue route work after that.

All system cards are `from: system`, `issued_by: router`, and `delivered_by: controller`. Their ACKs go directly from the addressed role to Router through the card check-in command; Controller does not receive or relay those ACKs. Current packet completions go directly to Router through the active-holder lease, and formal file-backed role outputs go through `flowpilot_runtime.py submit-output-to-router`. Controller follows Router daemon status and the Controller action ledger, then relays only Router-authorized metadata. Role-to-role work uses packet/mail ledgers, not shared prompt context.

## Runtime Kit

The active prompt content lives in the copied runtime kit and prompt manifest, not in this file:

- `assets/flowpilot_router.py`
- `assets/flowpilot_runtime.py`
- `assets/card_runtime.py`
- `assets/runtime_kit/manifest.json`
- `assets/runtime_kit/cards/`
- `assets/packet_runtime.py`
- `assets/role_output_runtime.py`

Old long-form protocol material is legacy source material only. Formal FlowPilot runs receive prompt content through the router and manifest.
