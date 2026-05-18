# Assets

Reusable assets for FlowPilot live here or in the repository-level
`templates/flowpilot/` directory:

- `flowpilot_router.py`, the prompt-isolated startup and Controller router;
- `flowpilot_router_facade_export_manifest.py`, the router facade export
  manifest used to keep the public router surface explicit during owner-module
  maintenance;
- `runtime_kit/manifest.json`, the system-card manifest copied into each run;
- `runtime_kit/cards/`, role, phase, event, reviewer, and display cards;
- `runtime_kit/prompts/`, hash-manifested prompt assets loaded by
  `flowpilot_prompt_store.py`, including packet prompt fragments under
  `runtime_kit/prompts/packets/`;
- `packet_runtime.py`, the physical packet envelope/body runtime facade backed
  by focused progress, creation, result, audit, and CLI helpers;
- `card_runtime.py`, the system-card runtime facade backed by focused IO,
  ledger, envelope, ACK, and bundle helpers;
- `flowpilot_user_flow_diagram.py`, the user-flow diagram compatibility
  entrypoint backed by source, tree, stage, Mermaid, and Markdown helpers;
- `packet_control_plane_model.py`, the packet control-plane model facade backed
  by focused state, transition, and invariant helpers;
- `packet_control_plane_model_transitions.py`, the transition facade backed by
  issue/resume, packet relay, dispatch/result relay, and reviewer/PM outcome
  transition owners;
- `flowpilot_router_action_factory.py`, the action-factory facade backed by
  reconciliation, dispatch-gate, and action-envelope helpers;
- `flowpilot_router_work_packets_pm_role.py`, the PM role-work facade backed by
  gate, write, lifecycle, and next-action helpers;
- `flowpilot_router_terminal_ledger.py`, the terminal-ledger facade backed by
  summary, traceability, closure/replay, and recovery helpers;
- `flowpilot_router_controller_scheduler_receipts.py`, the Controller receipt
  facade backed by write, receipt-effect, pending, and scheduled
  reconciliation helpers;
- `flowpilot_router_facade_export_manifest.py`, the export-manifest aggregator
  backed by action, controller, route, startup, and terminal/work-packet
  manifest shards;
- `route_memory/` files generated inside each run by `flowpilot_router.py`:
  `route_history_index.json` and `pm_prior_path_context.json`;
- `.flowpilot/` template files;
- route templates;
- heartbeat templates;
- capability evidence templates;
- research package, worker report, and reviewer report templates;
- experiment templates;
- `templates/startup_banner.md` for the first visible chat launch marker;
- minimal FlowGuard model templates.

For the prompt-isolated runtime, `SKILL.md` stays a small launcher. It must not
become the place where the full PM, Controller, Reviewer, Officer, or Worker
protocol is loaded into the main assistant. Put role and phase instructions in
`runtime_kit/cards/` and list them in `runtime_kit/manifest.json`.
Put prompt-like reusable text in `runtime_kit/prompts/` and list it in
`runtime_kit/prompts/manifest.json`; prompt assets are contract inputs, not
optional inline fallbacks.

During the 0.9.12 owner-module polish pass, touched modules were scanned for
prompt-like text. The remaining matches are runtime schema fields, ledger
payloads, dispatch policies, or calls into the existing PromptStore path rather
than stable reusable prompt assets, so no new prompt asset was added in that
pass. Existing PromptStore assets remain hash-managed.

The repository-level reusable project-control template is still
`templates/flowpilot/`. The executable regression models are in `simulations/`.

Protected PM decisions must include `prior_path_context_review` after reading
the current route-memory files. The route memory is a Controller-generated
index only; it must not be treated as acceptance evidence or a reason for the
Controller to decide route direction.

When packaging this skill into a standalone distribution, copy the
`templates/flowpilot/` directory into this asset area or keep a clear relative
path from the skill to the repository template source.
