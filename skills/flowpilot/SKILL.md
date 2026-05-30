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
- this `flowpilot` skill.

If this skill was installed from the full repository, prefer:

```powershell
python scripts\install_flowpilot.py --install-missing --install-flowguard
```

If only the skill directory is available, read `DEPENDENCIES.md` in this skill folder and ask before making heavy/global environment changes. Optional UI/design companions are not required for non-UI runs.

## Required Launcher Behavior

The assistant is only the FlowPilot bootloader until a new `flowpilot_new.py` run has been created. A user request to "start FlowPilot" or "use FlowPilot" is always a fresh formal invocation, even if `.flowpilot/current.json` points at an old or still-running run.

Do not read FlowPilot reference files, old route state, old screenshots, old UI assets, old prompt bodies, or runtime kit cards unless the router action explicitly names them.

Fresh formal invocation: `python skills\flowpilot\assets\flowpilot_new.py --root <project-root> --json start`. It reuses the native startup intake UI and records the result into the new current-run ledger. Legacy `flowpilot_router.py` commands are diagnostic/reference material unless the user explicitly asks to inspect or repair an old run.

Manual diagnostic/repair commands:

```powershell
python skills\flowpilot\assets\flowpilot_new.py --root <project-root> --json status
python skills\flowpilot\assets\flowpilot_new.py --root <project-root> --json patrol --sleep-seconds 60
python skills\flowpilot\assets\flowpilot_new.py --root <project-root> --json final-preflight
python skills\flowpilot\assets\flowpilot_new.py --root <project-root> --json resume --reason manual_resume
python skills\flowpilot\assets\flowpilot_new.py --root <project-root> --json lease-agent --packet-id <packet_id> --responsibility <role> --agent-id <agent_id> --host-kind live
python skills\flowpilot\assets\flowpilot_new.py --root <project-root> --json ack --lease-id <lease_id> --packet-id <packet_id>
python skills\flowpilot\assets\flowpilot_new.py --root <project-root> --json progress --lease-id <lease_id> --packet-id <packet_id> --status still_working
python skills\flowpilot\assets\flowpilot_new.py --root <project-root> --json submit-result --lease-id <lease_id> --packet-id <packet_id> --body <sealed_result_summary>
python skills\flowpilot\assets\flowpilot_new.py --root <project-root> --json repair-accepted-packet --packet-id <packet_id>
```

Copy exact fixed values from the returned `next_action`: `--host-kind` is `live`, `fake`, or `dry_run`; `--responsibility` is the exact packet role or node role returned by the runtime. If no listed value fits, stop and report the value-menu mismatch.

Formal startup creates the run shell, current pointer, run index, sealed startup-intake record, frozen contract, first route, first high-standard pre-planning packet, lifecycle guard, and foreground duty before returning a public next action. `.flowpilot/current.json` is UI focus/default-target metadata; `.flowpilot/runs/<run-id>/ledger.json` is authority. There is no requirement for a non-startup monitoring UI.

## Foreground Duty

The new runtime has five foreground duty actions:

- `process_next_action`: perform the returned runtime action.
- `wait_patrol`: waiting is an active duty; run patrol, wait the requested interval, then refresh guard and duty.
- `recover_or_reissue`: handle stale, inactive, overdue, or replacement conditions before waiting again.
- `control_plane_blocker`: report the blocker instead of silently waiting or claiming completion.
- `terminal_return`: final return is allowed only after terminal closure and final-return preflight pass.

Nonterminal status, patrol, resume, lease, ACK, result, and scoped-closure commands keep `controller_stop_allowed: false` and `final_return_preflight.allowed: false`. Knowing the next action is not completion. A packet, phase, or system-recorded scope closure may close a scope; it does not close the whole project unless the runtime returns `terminal_return`.

If `foreground_duty.action=wait_patrol`, do not final-answer. Run the duty's `refresh_command` or `python skills\flowpilot\assets\flowpilot_new.py --root <project-root> --json patrol --sleep-seconds 60`, wait for output, then follow the next `foreground_duty`. Starting one timer, seeing no new work, or observing a live role is not completion evidence.

Router-ready state preempts foreground waits. Before waiting on role chat or a
timer, scan daemon status and the Controller action; if Router has work ready,
use the returned action or `controller-standby` path instead of continuing the
foreground wait.

Before any final answer, done claim, or Controller shutdown for a new runtime run, run:

```powershell
python skills\flowpilot\assets\flowpilot_new.py --root <project-root> --json final-preflight
```

Only a successful final-preflight with `foreground_duty.action=terminal_return` and `controller_stop_allowed=true` may end the Controller role. Status projection is display-only and never authorizes Controller stop. Legacy `flowpilot_router.py` daemon files, controller ledgers, patrol timers, monitor wording, and stale summaries are old-run diagnostics, not fresh-run authority.

## Startup And Packet Work

When `flowpilot_new.py start` opens the native startup intake UI, formal startup must use the interactive native UI result. Do not satisfy formal startup with headless auto-confirmation, scripted result synthesis, chat-text substitution, direct JSON creation, or cancelled UI output. The UI record is the authority for activation; the router seals the body behind a path/hash record.

After startup, the new runtime materializes the first PM-bound high-standard contract packet. PM route planning is not legal until the high-standard contract, current discovery, and selected skill standard gates are accepted.

When the new runtime returns `lease_agent`, create or attach only the requested responsibility through an available host-supported role mechanism, record the addressable host `agent_id` with `flowpilot_new.py lease-agent`, and then wait for ACK/result through runtime commands. Every opened role binding must be explicitly requested with the strongest available host model and highest available reasoning effort.

All new formal runtime roles are packet roles, but not every gate is a dispatched role. PM, FlowGuard operator, reviewer, and route-node workers follow the same lifecycle: issued packet -> lease -> ACK -> sealed result -> ledger side effect -> next packet. System validation and system closure are router-owned ledger facts after accepted review evidence; do not spawn validator or Closure Officer workers, and do not complete FlowGuard or review through side-command shortcuts.

After PM planning closes, the runtime materializes executable route nodes, requires accepted node acceptance plans, issues each node as its own packet chain, runs FlowGuard and review packets, records system validation and system closure, applies PM disposition per node, uses same-node repair for ordinary quality gaps, runs parent backward replay where needed, then builds a final route-wide gate ledger plus requirement-evidence matrix before terminal completion.

When the issued packet is a FlowGuard operator packet, write formal-run evidence under the packet's `evidence_output_policy.run_local_evidence_root`. For Meta or Capability runners, use the packet's `recommended_runner_commands` or the same `--json-out <run-local-path>` pattern. Do not write formal-run evidence to tracked `simulations/*_results.json` baselines unless the packet explicitly asks for a repository baseline update.

On heartbeat or manual mid-run wakeup, use `flowpilot_new.py resume --reason <reason>` and then follow the returned `foreground_duty`. Treat supplied `work_chain_status` as diagnostic only; never use `alive`, `active`, or a wait timeout to skip current-run ledger, lifecycle guard, and foreground duty rehydration.

When the router returns a `payload_contract`, satisfy it exactly or return to the named role/user for missing fields. Do not guess missing payload fields or repair a rejected payload in Controller.

## Controller Boundary

After FlowPilot starts, the main assistant is Controller only. For a fresh `flowpilot_new.py` run, Controller may check public packet envelopes, lease state, lifecycle guard, foreground duty, final-return preflight, and status projection. Controller follows `foreground_duty` until terminal return. Controller may call `flowpilot_router.py next/apply/run-until-wait` only for diagnostics, tests, or explicit old-run repair/recovery.

Controller must not implement product work, write project evidence for a worker node, approve gates, mark route nodes complete, mutate the route from its own judgement, read sealed packet/result bodies, or receive/submit formal role outputs. Role outputs go directly to Router through the runtime command named by the packet.

When the router returns a control blocker, Controller may deliver only the public blocker id plus sealed repair packet path/hash to the target role. When the user asks to stop or cancel the active run, record the requested terminal event and follow the lifecycle action; do not continue route work after that.

## Runtime Kit

The active prompt content lives in the copied runtime kit and prompt manifest, not in this file:

- `assets/flowpilot_router.py`
- `assets/flowpilot_new.py`
- `assets/flowpilot_runtime.py`
- `assets/card_runtime.py`
- `assets/runtime_kit/manifest.json`
- `assets/runtime_kit/cards/`
- `assets/packet_runtime.py`
- `assets/role_output_runtime.py`

Old long-form protocol material is source-history material only. Formal FlowPilot runs receive prompt content through the router and manifest.

## Mature FlowGuard Project Topology

When a formal FlowPilot run is operating inside a mature FlowGuard repository
and the router-delivered packet or card names `docs/flowguard_project_topology.md`,
roles may read that map as project background only. The topology can guide which
models, tests, code areas, evidence summaries, and known-bad signals to inspect
next, but it is not a FlowGuard Report, not validation evidence, and not
authority for Controller, PM, Officers, or Reviewer to approve gates, mutate
routes, close nodes, or claim completion.
