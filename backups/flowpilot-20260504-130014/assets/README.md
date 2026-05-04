# Assets

Reusable assets for FlowPilot live here or in the repository-level
`templates/flowpilot/` directory:

- `.flowpilot/` template files;
- route templates;
- heartbeat templates;
- capability evidence templates;
- research package, worker report, and reviewer report templates;
- experiment templates;
- `templates/startup_banner.md` for the first visible chat launch marker;
- minimal FlowGuard model templates.

For v1, the canonical reusable project-control template is
`templates/flowpilot/`. The executable regression models are in
`simulations/`.

When packaging this skill into a standalone distribution, copy the
`templates/flowpilot/` directory into this asset area or keep a clear relative
path from the skill to the repository template source.
