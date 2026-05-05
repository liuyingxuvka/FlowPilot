---
name: flowpilot
description: Opt-in only. Use this skill only when the user explicitly asks to use FlowPilot or the flowpilot skill, for example "Use FlowPilot" or "使用 FlowPilot"; do not activate implicitly for large tasks, existing .flowpilot directories, UI redesigns, heartbeat requests, or repository work.
---

# FlowPilot

FlowPilot is a prompt-isolated router skill. This file stays small so activation does not load the full project-management protocol into main context.

## Activation Boundary

Use FlowPilot only after an explicit user request in the current thread. If the user is editing, auditing, discussing, or repairing this skill, treat that as ordinary repository work unless they ask to run a formal FlowPilot route.

Do not infer activation from task size, repository type, UI work, heartbeat language, or `.flowpilot/`.

## Required Launcher Behavior

On activation, the assistant is only the FlowPilot bootloader until the router
hands control to Controller.

The bootloader must:

1. Run the router and read only its JSON action envelope.
2. Execute exactly the pending action returned by the router.
3. Record the action result through the router.
4. Return to the router for the next action.

Do not read FlowPilot reference files, old route state, old screenshots, old UI
assets, old prompt bodies, or runtime kit cards unless the router action
explicitly names them.

The first router call for a new formal FlowPilot invocation is:

```powershell
python skills\flowpilot\assets\flowpilot_router.py --root <project-root> --json next --new-invocation
```

After that first fresh-start call, continue the same router loop with:

```powershell
python skills\flowpilot\assets\flowpilot_router.py --root <project-root> --json next
```

Apply a pending action with:

```powershell
python skills\flowpilot\assets\flowpilot_router.py --root <project-root> --json apply --action-type <action_type>
```

When the router returns the startup-question action, ask the three questions
from the JSON envelope, apply that pending action so the router records the
waiting/stop boundary, and stop immediately. Do not show the banner, create a
run, start agents, check heartbeat, open Cockpit, inspect files, plan work, or
continue the route in the same response.

After the later user reply explicitly answers all three startup questions, pass
those answers back to the pending router action using the router's exact enum
values plus `provenance: explicit_user_reply`. Do not infer, summarize, or
default the answers yourself. The router, not this skill file, decides the next
action.

The startup banner and FlowPilot Route Sign are user-facing display text. When
the router returns `display_text` for either one, paste that exact text into the
chat before applying the action or continuing. Generated files, paths, flags,
and state records do not count.

When the router returns `record_user_request`, pass the exact current formal
FlowPilot task text as `payload.user_request.text` with
`provenance: explicit_user_request`. Do not summarize the task, derive it from
old route state, or turn Controller's expectations into user intent. If the
exact current task text is not available, ask the user for the task and stop.
Do not show project-specific plans until the PM receives this router-owned
`user_intake` packet and later writes the route.

When the router returns `start_role_slots` with `requires_host_spawn: true`,
spawn all six requested role agents before applying the action. Apply the
action only after the payload contains one current `agent_id` per requested
role, `spawn_result: spawned_fresh_for_task`,
`spawned_after_startup_answers: true`, and the current `spawned_for_run_id`.
Do not treat empty role slots, prior-route agent IDs, or on-demand later
subagents as successful startup.

When the router returns `rehydrate_role_agents` with `requires_host_spawn: true`, restore or spawn all six role agents before applying it. Give each role its listed core prompt and current-run memory/context; PM must receive the PM resume context. Echo memory/core hashes and resume tick in `rehydrated_role_agents`.

## Controller Boundary

After the router loads Controller core, the main assistant is Controller only.
Controller may call the router, check the prompt manifest, check the packet
ledger, deliver system cards, relay packet envelopes, update status, and ask
roles for decisions.

Controller must not:

- implement product work;
- write project evidence for a worker node;
- approve gates;
- mark route nodes complete;
- mutate the route from its own judgement;
- read, summarize, execute, edit, or repair sealed packet/result bodies.

All system cards are `from: system`, `issued_by: router`, and
`delivered_by: controller`. Role-to-role work uses packet/mail ledgers, not
shared prompt context.

## Runtime Kit

The active prompt content lives in the copied runtime kit and prompt manifest,
not in this file:

- `assets/flowpilot_router.py`
- `assets/runtime_kit/manifest.json`
- `assets/runtime_kit/cards/`
- `assets/packet_runtime.py`

Old long-form protocol material is legacy source material only. It may be used
to author new cards during FlowPilot skill development, but a formal FlowPilot
run must receive prompt content through the router and manifest.
