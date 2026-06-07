---
name: flowpilot
description: Opt-in only. Use this skill only when the user explicitly asks to use FlowPilot or the flowpilot skill, for example "Use FlowPilot" or "使用 FlowPilot"; do not activate implicitly for large tasks, existing .flowpilot directories, UI redesigns, continuation requests, or repository work.
---

# FlowPilot

FlowPilot is a prompt-isolated router skill. This file is only a small launcher; the active run protocol lives in the copied runtime kit, cards, and Router output.

## Activation Boundary

Use FlowPilot only after an explicit user request in the current thread. If the user is editing, auditing, discussing, or repairing this skill, treat that as ordinary repository work unless they ask to run a formal FlowPilot route.

Do not infer activation from task size, repository type, UI work, continuation language, or `.flowpilot/`.

## Dependency Bootstrap

Before a formal FlowPilot run, verify the real `flowguard` package, the installed/readable `model-first-function-flow` skill, and this `flowpilot` skill.

If this skill was installed from the full repository, prefer:

```powershell
python scripts\install_flowpilot.py --install-missing --install-flowguard
```

If only the skill directory is available, read `DEPENDENCIES.md` and ask before making heavy/global environment changes.

## Required Launcher Behavior

The assistant is only the FlowPilot bootloader until a new `flowpilot_new.py` run has been created. A user request to start or use FlowPilot is always a fresh formal invocation, even if `.flowpilot/current.json` points at an old or still-running run.

Do not read FlowPilot reference files, prior run state, old screenshots, old UI assets, old prompt bodies, or runtime kit cards unless the Router action explicitly names them.

FlowPilot is new-only by default. Do not add or rely on compatibility shims, legacy field aliases, prose parsers, missing-field defaults, nested payload normalization, old-router alternate paths, newest-run alternate paths, or historical-artifact promotion. If a returned packet/result does not satisfy the current structured contract, block or reissue through the runtime command named by `foreground_duty`; do not translate the old shape into a valid current result.

Fresh formal invocation:

```powershell
python skills\flowpilot\assets\flowpilot_new.py --root <project-root> --json start
```

The public formal-run control surface is `flowpilot_new.py` only. The startup path uses the native startup intake UI; There is no requirement for a non-startup monitoring UI. `.flowpilot/runs/<run-id>/ledger.json` is authority; `.flowpilot/current.json` is UI focus/default-target metadata.

The internal router facade is retained for current tests and stateful runtime commands. Do not bypass `flowpilot_new.py` during a new formal run.

Before the background driver is started or attached, the bootloader may only create the fresh run shell, write the active pointer/index, copy current runtime kit material, and start or attach the current background driver. It must not run startup packet work, role work, direct apply loops, or historical recovery.

After the background driver startup action succeeds, startup and Controller work belong to background driver status plus the Controller action ledger. Run direct router progress commands only for diagnostic, test, or explicit repair cases; ordinary progress comes from driver rows, Controller receipts, and the current lifecycle guard.

Common current-runtime commands:

```powershell
python skills\flowpilot\assets\flowpilot_new.py --root <project-root> --json status
python skills\flowpilot\assets\flowpilot_new.py --root <project-root> --json patrol --sleep-seconds 60
python skills\flowpilot\assets\flowpilot_new.py --root <project-root> --json final-preflight
python skills\flowpilot\assets\flowpilot_new.py --root <project-root> --json resume --reason manual_resume
python skills\flowpilot\assets\flowpilot_new.py --root <project-root> --json dispatch-current-role --packet-id <packet_id> --responsibility <role> --host-kind live --agent-id <role_surface_agent_id_if_requested>
python skills\flowpilot\assets\flowpilot_new.py --root <project-root> --json role-handoff --lease-id <lease_id> --packet-id <packet_id>
python skills\flowpilot\assets\flowpilot_new.py --root <project-root> --json ack --lease-id <lease_id> --packet-id <packet_id>
python skills\flowpilot\assets\flowpilot_new.py --root <project-root> --json open-packet --lease-id <lease_id> --packet-id <packet_id>
python skills\flowpilot\assets\flowpilot_new.py --root <project-root> --json submit-result --lease-id <lease_id> --packet-id <packet_id> --body <sealed_result_summary>
python skills\flowpilot\assets\flowpilot_new.py --root <project-root> --json repair-accepted-packet --packet-id <packet_id>
```

Copy exact fixed values from returned runtime output. If no listed value fits, stop and report the value-menu mismatch.

## Foreground Duty

Follow the returned `foreground_duty` until terminal return. The five actions are `process_next_action`, `wait_patrol`, `recover_or_reissue`, `control_plane_blocker`, and `terminal_return`.

If `foreground_duty.action=wait_patrol`, do not final-answer. Run the duty refresh command or `flowpilot_new.py patrol`, wait for output, and follow the returned foreground duty.

Runtime-ready state preempts foreground waits. Before waiting on role chat or a timer, refresh the current lifecycle guard through `flowpilot_new.py patrol` or the runtime-provided refresh command; if the guard exposes work, follow the returned foreground duty instead of continuing the wait.

Before any final answer, done claim, or Controller shutdown, run `flowpilot_new.py final-preflight`. Only a successful final-preflight with `foreground_duty.action=terminal_return` and `controller_stop_allowed=true` may end Controller work.

If public runtime output includes `progress_fraction.display`, Controller may relay that exact current expanded node fraction when a status update is useful. Do not calculate progress, convert it to a percent, read sealed bodies for progress, or treat the fraction as authority for completion, stop, gate, route advance, or final return. If absent, do not invent progress.

## Startup And Packet Work

Formal startup must use the interactive native startup intake UI result. Do not satisfy startup with headless auto-confirmation, scripted synthesis, chat-text substitution, direct JSON creation, or cancelled UI output.

For `open_startup_intake_ui`, after the UI closes, return through the current lifecycle guard and foreground duty, then use the Controller action ledger. The startup UI result is acknowledged by a Controller ledger row and a controller-receipt; it is not a direct pending action to apply in place.

When the runtime returns `dispatch_current_role`, create or attach only the requested responsibility through an available host-supported, addressable, isolated role surface when the dispatch result asks for one, continue through `flowpilot_new.py dispatch-current-role`, and relay only the runtime-generated `role_handoff_text`. Prefer durable, addressable role surfaces without practical parallel-count or model-capability limits when such surfaces are available.

All formal role work follows the same current path: issued packet -> current role dispatch -> ACK -> sealed result -> ledger side effect -> next packet. Missing payload fields return to the named role/user; Controller must not guess or repair them.

On manual resume, run `flowpilot_new.py resume --reason manual_resume` and then follow the returned `foreground_duty`. Treat `work_chain_status` as diagnostic only; never use stale role bindings, prior run state, chat history, or wait timeouts as authority.

## Runtime Kit

The active prompt content lives in the copied runtime kit and prompt manifest:

- `assets/flowpilot_new.py`
- `assets/card_runtime.py`
- `assets/runtime_kit/manifest.json`
- `assets/runtime_kit/cards/`
- `assets/packet_runtime.py`
- `assets/role_output_runtime.py`

Old long-form protocol material is source-history material only.
