## Why

FlowPilot's current-contract runtime is `flowpilot_new.py` plus the
run-scoped packet ledger, but active prompt and card surfaces still expose old
Router/runtime-kit commands and template language. Those remnants can teach
future agents to follow obsolete FlowPilot paths during new-runtime work.

## What Changes

- **BREAKING** Remove old FlowPilot role-output commands, Router daemon
  instructions, active-holder lease wording, and old runtime-kit submission
  paths from current prompt/card/skill/template surfaces.
- **BREAKING** Treat `flowpilot_new.py` packet lifecycle commands as the only
  formal role interaction path for current FlowPilot runs.
- **BREAKING** Remove or quarantine current-facing runtime-kit and template
  text that describes old Router/control-plane behavior as live startup or
  role-output authority.
- Add forbidden-surface validation so active prompt, card, install, and
  generated topology surfaces cannot reintroduce old commands or compatibility
  language.
- Synchronize the local installed FlowPilot skill from the repository and
  commit the validated local result without pushing, tagging, publishing, or
  releasing.

## Capabilities

### New Capabilities

- `flowpilot-current-prompt-surface`: current FlowPilot prompt surfaces expose
  only the new packet-ledger runtime contract and reject old prompt/control
  paths.

### Modified Capabilities

- `flowpilot-prompt-boundary-policy`: formal output prompt policy changes from
  generic Router-directed runtime output to the current `flowpilot_new.py`
  packet result path, with explicit forbidden legacy prompt surfaces.
- `repository-maintenance-guardrails`: maintenance completion must synchronize
  the local installed FlowPilot skill and local git state after prompt-surface
  cleanup.
- `tiered-flowpilot-test-validation`: validation must include a focused
  forbidden-surface scan for current prompt/card/install surfaces.

## Impact

- Affected surfaces include `skills/flowpilot/SKILL.md`,
  `skills/flowpilot/assets/runtime_kit/`, `templates/flowpilot/`,
  install-check scripts, prompt/card tests, generated topology, OpenSpec
  artifacts, and local installed skill sync.
- Historical backups under `backups/` remain preserved and are not used as
  current prompt authority.
- No remote push, tag, release, deploy, package publication, or destructive
  backup deletion is in scope.
