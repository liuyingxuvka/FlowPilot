<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: bootloader
recipient_identity: FlowPilot bootloader startup display recipient
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: System-card ACKs go directly to Router through the card check-in command; this is the router-directed return path for card ACKs. Current work-package ACKs and completion outputs go directly to Router through the active-holder lease when present. For formal role outputs, write the body only to a run-scoped packet, result, report, or decision file, then submit it with `flowpilot_runtime.py submit-output-to-router` so Router records the event and later exposes only controller-visible envelope metadata with status, paths, and hashes. If an output contract has a fixed Router event, a local receipt or `submit-output` record is only local storage and must not be treated as wait completion until `submit-output-to-router` records the Router event. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
post_ack: ACK is receipt only; ACK is not completion. This is a work item when it asks for an output, report, decision, result, or blocker. After work-card ACK, do not stop or wait for another prompt; immediately continue the work assigned by this card and submit the formal output or blocker through the Router-directed runtime path. The task remains unfinished until Router receives that output or blocker.
work_authority: Identity/system cards may ACK or explain routing, but they do not by themselves authorize formal report work. Any card that asks a role to produce a formal output must carry current Router wait authority, PM role-work packet/result contract, or active-holder lease; otherwise stop and return a protocol blocker.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. System-card ACKs, current work-package outputs, and formal role-output submissions go directly through the current runtime commands. Controller must follow the `flowpilot_new.py` lifecycle guard and foreground duty; old `flowpilot_router.py` commands are old-run diagnostics or explicit unsupported-run repair tools only.
runtime_context: Treat the runtime delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; submit a protocol blocker through the Router-directed runtime path.
flowguard_decision_core: FlowPilot keeps Router, packets, role authority, ledgers, and install/runtime boundaries as the shell. Non-trivial product, process, route, node, repair, validation, evidence-freshness, resume, or closure judgement must use a run-scoped FlowGuard Work Order and FlowGuard Report, or a scoped flowguard_not_required_reason.
-->
```text
✦━━━━━━━━━━━━━━━━━━━━✦
⚑ FlowPilot ⚑
✦━━━━━━━━━━━━━━━━━━━━✦

- Developer: Yingxu Liu
- Repository: https://github.com/liuyingxuvka/FlowPilot
- Buy the developer a coffee: https://paypal.me/Yingxuliu

✦━━━━━━━━━━━━━━━━━━━━✦
```
