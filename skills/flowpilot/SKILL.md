---
name: flowpilot
description: Opt-in only. Use this skill only when the user explicitly asks to use FlowPilot or the flowpilot skill, for example "Use FlowPilot" or "使用 FlowPilot"; do not activate implicitly for large tasks, existing .flowpilot directories, UI redesigns, continuation requests, or repository work.
---

# FlowPilot

FlowPilot is a prompt-isolated router skill. This file is only a small launcher; the active run protocol lives in the copied runtime kit, cards, and Router output.

## Activation Boundary

Use FlowPilot only after an explicit user request in the current thread. If the user is editing, auditing, discussing, or repairing this skill, treat that as ordinary repository work unless they ask to run a formal FlowPilot route.

Do not infer activation from task size, repository type, UI work, continuation language, or .flowpilot/.

## Dependency Bootstrap

Before a formal FlowPilot run, verify the real `flowguard` package, the installed/readable `model-first-function-flow` skill, and this `flowpilot` skill.

If this skill was installed from the full repository, prefer:

```powershell
python scripts\install_flowpilot.py --install-missing --install-flowguard
```

If only the skill directory is available, read `DEPENDENCIES.md` and ask before making heavy/global environment changes.

## Required Launcher Behavior

The assistant is only the FlowPilot bootloader until the public `assets/flowpilot_new.py` launcher has created a fresh run. A user request to start or use FlowPilot is always a fresh formal invocation, even if project-local active-run metadata points at an old or still-running run.

Do not read FlowPilot reference files, prior run state, old screenshots, old UI assets, old prompt bodies, or runtime kit cards unless the Router action explicitly names them.

FlowPilot is new-only by default. Do not add or rely on compatibility shims, legacy field aliases, prose parsers, missing-field defaults, nested payload normalization, old-router alternate paths, newest-run alternate paths, or historical-artifact promotion. If a returned packet/result does not satisfy the current structured contract, block or reissue through the runtime command named by `foreground_duty`; do not translate the old shape into a valid current result.

Fresh formal invocation:

```powershell
python assets\flowpilot_new.py --root <project-root> --json start
```

The public formal-run control surface is `assets/flowpilot_new.py` only. The startup path uses the native startup intake UI; there is no requirement for a non-startup monitoring UI. The runtime-provided current-run ledger is authority; project-local active-run metadata is only UI focus/default-target metadata.

The internal router facade is retained for current tests and stateful runtime commands. Do not bypass `assets/flowpilot_new.py` during a new formal run.

Before the background driver is started or attached, the bootloader may only create the fresh run shell, write the active pointer/index, copy current runtime kit material, and start or attach the current background driver. It must not run startup packet work, role work, direct apply loops, or historical recovery.

After the background driver startup action succeeds, startup and Controller work belong to background driver status plus the Controller action ledger. Run direct router progress commands only for diagnostic, test, or explicit repair cases; ordinary progress comes from driver rows, Controller receipts, and the current lifecycle guard.

Common current-runtime commands are `status`, `patrol`, `final-preflight`, `resume --reason manual_resume`, `dispatch-current-role`, `role-handoff`, `ack`, `open-packet`, `submit-result`, and `repair-accepted-packet` through the `assets\flowpilot_new.py` launcher from this skill directory, passing `--root <project-root> --json ...`.

The compact command list is not an argument schema. Execute the exact command strings returned by the runtime, or inspect the command help for a diagnostic/manual repair case; do not reconstruct packet, lease, role, or result arguments from memory. Copy exact fixed values from returned runtime output. If no listed value fits, stop and report the value-menu mismatch.

## Foreground Duty

Follow the returned `foreground_duty` until terminal return. The five actions are `process_next_action`, `wait_patrol`, `recover_or_reissue`, `control_plane_blocker`, and `terminal_return`.

If `foreground_duty.action=wait_patrol`, do not final-answer. Run the duty refresh command or invoke `assets/flowpilot_new.py` with `patrol`, wait for output, and follow the returned foreground duty.

Runtime-ready state preempts foreground waits. Before waiting on role chat or a timer, refresh the current lifecycle guard with the runtime-returned command; its launcher action is `flowpilot_new.py patrol`. If the guard exposes work, follow the returned foreground duty instead of continuing the wait.

Before any final answer, done claim, or Controller shutdown, invoke `assets/flowpilot_new.py` with `final-preflight`. Only a successful final-preflight with `foreground_duty.action=terminal_return` and `controller_stop_allowed=true` may end Controller work.

If a user-facing status update is needed and public runtime output includes `progress_fraction.display`, Controller should normally relay that exact current expanded node fraction. A changed active node or changed runtime-owned expanded-node fraction can justify a short progress note, while quiet patrol, receipts, ACK bookkeeping, ledger cleanup, relay bookkeeping, and process-only asides remain silent by default. Do not calculate progress, convert it to a percent, read sealed bodies for progress, or treat the fraction as authority for completion, stop, gate, route advance, or final return. If absent, do not invent progress.

## Startup And Packet Work

Formal startup must use the interactive native startup intake UI result. Do not satisfy startup with headless auto-confirmation, scripted synthesis, chat-text substitution, direct JSON creation, or cancelled UI output.

For `open_startup_intake_ui`, after the UI closes, return through the current lifecycle guard and foreground duty, then use the Controller action ledger. The startup UI result is acknowledged by a Controller ledger row and a controller-receipt; it is not a direct pending action to apply in place.

When the runtime returns `dispatch_current_role`, execute only the runtime's current role-assignment disposition. For `reuse_existing_role`, deliver the runtime-generated `role_handoff_text` to the existing host-supported isolated addressable AI execution surface named by `effective_agent_id`; do not open a fresh AI surface for that assignment. For `create_new_role` with `role_surface_required=true`, open one host-supported isolated addressable AI execution surface for the requested responsibility, then continue through the runtime-provided `flowpilot_new.py dispatch-current-role` command with that surface id. For `blocked`, follow the blocker or recovery path; do not open a surface, reuse a different surface, or perform role work in the Controller foreground. On each dispatch, create or attach only the requested responsibility through an available host-supported, addressable, isolated role surface. Valid host surfaces may be background agents, separate threads, new conversations, workers, independent AI sessions, or equivalent host-supported mechanisms. Prefer durable, addressable role surfaces without practical parallel-count or model-capability limits when such surfaces are available.

All formal role work follows the same current path: issued packet -> current role dispatch -> ACK -> sealed result -> ledger side effect -> next packet. PM, reviewer, worker, FlowGuard operator, and equivalent role ACK/open/submit commands run inside the addressed isolated AI execution surface, not in the Controller foreground. Missing payload fields return to the named role/user; Controller must not open role-only packets, read sealed bodies, guess, repair, or submit role results.

On manual resume, invoke `assets/flowpilot_new.py` with `resume --reason manual_resume` and then follow the returned `foreground_duty`. Treat `work_chain_status` as diagnostic only; never use stale role bindings, prior run state, chat history, or wait timeouts as authority.

## Runtime Kit

The active prompt content lives in the copied runtime kit and prompt manifest:

- `assets/flowpilot_new.py`
- `assets/card_runtime.py`
- `assets/runtime_kit/manifest.json`
- `assets/runtime_kit/cards/`
- `assets/packet_runtime.py`
- internal role-output contract helper modules

Old long-form protocol material is source-history material only.

<!-- BEGIN SKILLGUARD CONTRACT LAYER -->
## Purpose
Bind each flowpilot run to the declared integration mode, evidence, blockers, residual_risk, and claim_boundary.
## Entrypoint Scope
Covers flowpilot plus explicitly routed local materials; no unrelated repos, private files, external services, publication, or release claims unless requested and routed.
## Local Material Routing
Use workspace, skill directory, user files, or configured project paths; keep private machine paths local and public instructions portable.
## Entrypoint Acceptance Map
Use SkillGuard as the declarative contract layer attached to the native route/check owner: the FlowPilot `assets/flowpilot_new.py` launcher, Router/Controller runtime, and FlowPilot regression checks. Every declared FlowPilot route and check must have one explicit native binding to its existing owner source; an empty, missing, extra, or duplicate binding blocks global selection. The native FlowPilot owner executes work and produces evidence; SkillGuard compiles, checks, and consumes that declared evidence without becoming a second role-work runtime. Duplicate SkillGuard-owned execution paths are invalid. Declared gates/routes: opt in gate, route plan, execution checks, closure.
## Use When
Use when the request matches flowpilot and needs this governed workflow, materials, checks, or handoff behavior.
## Do Not Use When
Do not use outside the domain, without required materials, when a more specific skill owns the work, or for tiny direct answers.
## Required Workflow
Select the target-owned native route/check surface, compile or check the current declarative contract, let the native FlowPilot owner execute the workflow, collect its evidence, consume the current receipts, fix affected failures, then report.
## Hard Gates
Do not skip phases, do not replace required evidence with prose, do not treat stale reports as current, do not weaken validation to pass, and do not claim completion when blockers remain.
## Output Requirements
Report evidence, failures, blockers, skipped_checks with reasons, residual_risk, and claim_boundary; distinguish checked, unchecked, blocked, and uncertain.
## SkillGuard Maintenance
Keep exactly one current V2 authority trio under `.skillguard`: `contract-source.json`, `compiled-contract.json`, and `check-manifest.json`. Keep `native_route_bindings` exactly equal to the four compiled FlowPilot routes and `native_check_bindings` exactly equal to the declared checks; omission is a blocker, not a fallback to prose routing. Use the public SkillGuard compiler/checkers; do not regenerate former V1 files or call private compiler helpers. Reuse a current receipt only when its execution identity and precise inputs still match. A final receipt check is a read-only consumer and must not use `--background` or `--resume`. Contract-depth mapping is not execution-depth proof. After an entrypoint, route, evidence, or closure change, run only the affected SkillGuard checks. Run full or release validation only for a stable integration snapshot or an explicit release.
<!-- END SKILLGUARD CONTRACT LAYER -->
