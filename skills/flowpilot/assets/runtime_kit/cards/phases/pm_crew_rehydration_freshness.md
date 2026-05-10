<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Write any role-output body only to a run-scoped packet, result, report, or decision file, then return to Controller only a controller-visible envelope with ids, paths, hashes, from/to roles, next holder, event name, and body visibility. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
runtime_context: Treat the router delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; return a protocol blocker through Controller.
-->
# PM Crew Rehydration Freshness

## Role Capability Reminder

- If a PM-owned decision still lacks evidence, modeling, research, review, or implementation support, register a bounded `pm_registers_role_work_request` only when the router's current `allowed_external_events` includes that event; otherwise record the limitation or blocker instead of emitting it.
- Treat the router's current `allowed_external_events` as the active authority for what this card may return.
- For a blocked PM-owned decision, choose the smallest valid path among repair, sender reissue, route mutation, evidence quarantine, or user stop; do not skip required recheck.
- Put reviewer, worker, and officer advice that needs PM disposition into the PM suggestion/blocker ledger instead of leaving it only in prose.


Before resume or startup activation, decide whether the six role slots are
fresh for the current formal task.

Accept only:

- live roles spawned for this run after the current startup answers;
- live continuity confirmed by a host liveness preflight for the current run;
- same-task role memory packets rehydrated into replacement roles;
- explicit user-approved single-agent six-role fallback.

For any live background role agent, whether it is first spawned, restored,
rehydrated, or replaced during heartbeat/manual resume, require an explicit
strongest-available host model request and highest-available reasoning-effort
request. Foreground/Controller model inheritance is not sufficient background
role setup.

Prior-run `agent_id` values are audit history only. If any required role is
missing, stale, cross-run, or unverifiable, block route work until PM records a
replacement or fallback decision.

`wait_agent` timeout is not freshness proof. Treat it as `timeout_unknown`;
Controller must not continue waiting on that old role unless a later bounded
host liveness check confirms the role is active.
