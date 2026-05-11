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

On activation, the assistant is only the FlowPilot bootloader until the router hands control to Controller. The bootloader must run the router, read only its JSON action envelope, execute exactly that pending action, record the result through the router, and return to the router for the next action.

Do not read FlowPilot reference files, old route state, old screenshots, old UI assets, old prompt bodies, or runtime kit cards unless the router action explicitly names them.

Fresh formal invocation:

```powershell
python skills\flowpilot\assets\flowpilot_router.py --root <project-root> --json run-until-wait --new-invocation
```

Continue/apply:

```powershell
python skills\flowpilot\assets\flowpilot_router.py --root <project-root> --json next
python skills\flowpilot\assets\flowpilot_router.py --root <project-root> --json apply --action-type <action_type>
python skills\flowpilot\assets\flowpilot_router.py --root <project-root> --json run-until-wait
```

After applying a wait-boundary action, prefer `run-until-wait`. It may apply only replay-proven safe internal router actions and must stop again before user, host, role, payload, card, packet, ledger, and final-replay boundaries.

When the router returns startup questions, ask the three questions, apply that pending action so the router records the waiting/stop boundary, and stop immediately. Do not show the banner, create a run, start agents, check heartbeat, open Cockpit, inspect files, plan work, or continue the route in the same response.

After the later user reply answers the questions, pass canonical router enum fields. Exact enum replies use `provenance: explicit_user_reply`. Natural-language replies may be interpreted only with `provenance: ai_interpreted_from_explicit_user_reply` plus a `startup_answer_interpretation` receipt preserving the raw reply and `ambiguity_status: none`. If ambiguous, ask the user. The router-owned startup task contract is the authority for activation; reviewer checks only independently observable startup facts requested by the router, not private chat authenticity.

The startup banner and FlowPilot Route Sign are user-facing display text. When the router returns `display_text`, paste that exact text into chat before applying. Do not add display-gate, evidence, source-health, confirmation, or controller/audit metadata to the user-visible body; those details belong in packets, ledgers, and action payloads. Generated files, paths, flags, and state records do not count.

When no Cockpit/UI surface is open, show the router's public route sign together with the current status summary. Use only `current_status_summary.json` and public route-display text for that summary; do not show evidence tables, source fields, hashes, or sealed packet/result body details. When the Cockpit/UI surface is open, let the UI render the same status summary and keep chat updates short.

When the router returns `record_user_request`, pass the exact current formal FlowPilot task text as `payload.user_request.text` with `provenance: explicit_user_request`. Do not summarize, derive it from old route state, or turn Controller expectations into user intent. If the exact text is unavailable, ask the user and stop.

When the router returns `start_role_slots` with `requires_host_spawn: true`, spawn all six requested role agents before applying. Every background role agent must be explicitly requested with the strongest available host model and the highest available reasoning effort; do not rely on inheriting the foreground/Controller model. Apply only with one current `agent_id` per requested role, `model_policy: strongest_available`, `reasoning_effort_policy: highest_available`, `spawn_result: spawned_fresh_for_task`, `spawned_after_startup_answers: true`, and current `spawned_for_run_id`. Do not treat empty role slots, prior-route agent IDs, or later on-demand subagents as startup success.

When a heartbeat or manual mid-run wakeup occurs, always record `heartbeat_or_manual_resume_requested` and return to the router. Treat any supplied `work_chain_status` as diagnostic only; never use `alive`, `active`, or a `wait_agent` timeout to skip `load_resume_state`.

When the router returns `rehydrate_role_agents` with `requires_host_spawn: true`, perform the six-role liveness preflight named by the action, then restore or spawn all six role agents before applying it. Every restored or replacement background role agent must be explicitly requested with the strongest available host model and the highest available reasoning effort; do not rely on inheriting the foreground/Controller model during heartbeat, manual resume, liveness recovery, or missing-agent replacement. Give each role its listed core prompt and current-run memory/context; PM must receive the PM resume context. Echo `model_policy: strongest_available`, `reasoning_effort_policy: highest_available`, memory/core hashes, resume tick, host liveness status, liveness decision, bounded wait result, and the timeout-not-active receipt in `rehydrated_role_agents`. If an agent is missing, cancelled, unknown, or `timeout_unknown`, spawn a replacement from current-run memory instead of continuing to wait on that old agent.

When the router returns `create_heartbeat_automation`, create the requested Codex heartbeat with the router-provided name, prompt, schedule, and thread destination before applying it. Apply only with the real `host_automation_id`, `host_automation_verified: true`, `route_heartbeat_interval_minutes: 1`, and a `host_automation_proof` receipt bound to the current `run_id`; never mark scheduled continuation active from a file, name guess, or self-attested status.

When the router returns a `payload_contract`, satisfy it exactly or return to the named role/user for missing fields. Do not guess missing payload fields or repair a rejected payload in Controller.

## Controller Boundary

After the router loads Controller core, the main assistant is Controller only. Controller may call the router, check the prompt manifest, check the packet ledger, deliver system cards, relay Router-authorized packet/result/role-output envelope metadata, update status, and wait for router next-action notices.

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

All system cards are `from: system`, `issued_by: router`, and `delivered_by: controller`. Their ACKs go directly from the addressed role to Router through the card check-in command; Controller does not receive or relay those ACKs. Current packet completions go directly to Router through the active-holder lease, and formal file-backed role outputs go through `flowpilot_runtime.py submit-output-to-router`. Controller waits for Router status or next-action notices, then relays only Router-authorized metadata. Role-to-role work uses packet/mail ledgers, not shared prompt context.

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
