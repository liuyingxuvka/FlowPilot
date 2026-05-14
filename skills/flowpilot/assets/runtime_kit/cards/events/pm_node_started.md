<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: System-card ACKs go directly to Router through the card check-in command; this is the router-directed return path for card ACKs. Current work-package ACKs and completion outputs go directly to Router through the active-holder lease when present. For formal role outputs, write the body only to a run-scoped packet, result, report, or decision file, then submit it with `flowpilot_runtime.py submit-output-to-router` so Router records the event and later exposes only controller-visible envelope metadata with status, paths, and hashes. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
post_ack: ACK is receipt only; ACK is not completion. After event-card ACK, process this event card only through its paired PM card path or an explicitly Router-authorized output event; if no authorized path exists, return a protocol blocker.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. System-card ACKs, current work-package outputs, and formal role-output submissions go directly to Router through their runtime commands. Controller must follow Router daemon status and the Controller action ledger; flowpilot_router.py next/run-until-wait are diagnostic or explicit repair tools only.
runtime_context: Treat the router delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; submit a protocol blocker through the Router-directed runtime path.
-->
# PM Event: Node Started

## Role Capability Reminder

- If a PM-owned decision still lacks evidence, modeling, research, review, or implementation support, register a bounded `pm_registers_role_work_request` only when the router's current `allowed_external_events` includes that event; otherwise record the limitation or blocker instead of emitting it.
- Treat the router's current `allowed_external_events` as the active authority for what this card may return.
- For a blocked PM-owned decision, choose the smallest valid path among repair, sender reissue, route mutation, evidence quarantine, or user stop; do not skip required recheck.
- Put reviewer, worker, and officer advice that needs PM disposition into the PM suggestion/blocker ledger instead of leaving it only in prose.


A current route node has started.

PM must issue only packets scoped to the current node. Include node id,
objective, allowed reads/writes, forbidden actions, acceptance slice, required
verification, and expected result recipient.

The packet must include the registry `output_contract`
`flowpilot.output_contract.worker_current_node_result.v1` in both the packet
envelope and packet body's `Output Contract` section, and the contract must
match the current node and target worker role.

Do not include downstream route work unless the current node explicitly owns it.
