# Assets

Reusable assets for FlowPilot live here or in the repository-level
`templates/flowpilot/` directory:

- `flowpilot_router.py`, the prompt-isolated startup and Controller router;
- `runtime_kit/manifest.json`, the system-card manifest copied into each run;
- `runtime_kit/cards/`, role, phase, event, reviewer, and display cards;
- `packet_runtime.py`, the physical packet envelope/body runtime;
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

The repository-level reusable project-control template is still
`templates/flowpilot/`. The executable regression models are in `simulations/`.

Protected PM decisions must include `prior_path_context_review` after reading
the current route-memory files. The route memory is a Controller-generated
index only; it must not be treated as acceptance evidence or a reason for the
Controller to decide route direction.

When packaging this skill into a standalone distribution, copy the
`templates/flowpilot/` directory into this asset area or keep a clear relative
path from the skill to the repository template source.
