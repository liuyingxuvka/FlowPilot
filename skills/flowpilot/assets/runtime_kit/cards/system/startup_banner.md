<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: bootloader
recipient_identity: FlowPilot bootloader startup display recipient
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: System-card ACKs go through the current runtime card check-in command; this is the current-runtime return path for card ACKs. Current work-package ACKs and completion outputs go through the assigned current packet lease when present. For formal role outputs, write the body only to a run-scoped packet, result, report, decision, or blocker file, then submit it with `flowpilot_new.py submit-result --lease-id <lease-id> --packet-id <packet-id> --body-file <sealed_result_body_file>` so the current runtime ledger records the event and later exposes only controller-visible envelope metadata with status, paths, and hashes. A local file write is only local storage and must not be treated as wait completion until the current runtime records the packet result. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
post_ack: ACK is receipt only; ACK is not completion. This is a work item when it asks for an output, report, decision, result, or blocker. After work-card ACK, do not stop or wait for another prompt; immediately continue the assigned work and submit the formal output or blocker through the current runtime path. The task remains unfinished until the current runtime receives that output or blocker.
work_authority: Identity/system cards may ACK or explain routing, but they do not by themselves authorize formal report work. Any card that asks a role to produce a formal output must carry current runtime wait authority, PM role-work packet/result contract, or current packet lease; otherwise stop and return a protocol blocker.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. System-card ACKs, current work-package outputs, and formal role-output submissions go directly through the current runtime commands. Controller must follow the `flowpilot_new.py` lifecycle guard and foreground duty; no unsupported command text, stale runtime state, chat history, or historical artifact authorizes current-run progress.
runtime_context: Treat the runtime delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; submit a protocol blocker through the current runtime path.
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
