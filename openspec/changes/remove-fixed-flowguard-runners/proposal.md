## Why

FlowPilot currently issues FlowGuard operator packets with hard-coded
`recommended_runner_commands` for repository-specific Meta and Capability
runners. That works only in repositories that already contain those exact
scripts. In a fresh or unrelated FlowPilot target project, the packet can make
FlowGuard treat missing optional runners as the main blocker instead of
selecting or creating suitable run-local FlowGuard evidence.

The same incident also exposed an outcome parser mismatch: a FlowGuard result
can declare `verdict: blocked` or include `flowguard_report.ok=false`, while
the runtime records the outer outcome as pass because it only recognizes a
narrow set of outcome field names.

## What Changes

- Remove fixed Meta/Capability runner recommendations from runtime-issued
  FlowGuard operator packets.
- Keep only the run-local evidence root and baseline-protection policy in the
  packet, so the FlowGuard operator chooses existing models, existing scripts,
  or new run-local evidence appropriate to the target project.
- Update FlowPilot skill guidance so operators are not instructed to look for
  `recommended_runner_commands`.
- Treat structured `verdict` fields and failing nested `flowguard_report`
  summaries as explicit blocking outcomes.
- Add focused regression tests for packet contents and the blocked-result
  parser paths.
- Sync the installed FlowPilot skill after source validation.

## Impact

- Affected runtime: `skills/flowpilot/assets/flowpilot_core_runtime/runtime.py`.
- Affected user-facing FlowPilot guidance: `skills/flowpilot/SKILL.md`.
- Affected tests: FlowPilot new-entrypoint and core-runtime semantic outcome
  tests.
- Affected installed copy: `%USERPROFILE%/.codex/skills/flowpilot` after sync.
