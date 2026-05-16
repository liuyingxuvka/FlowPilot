## Why

A live startup showed that an assistant can see an existing `running`
FlowPilot pointer and accidentally continue that run when the user asked to
start FlowPilot. FlowPilot must support multiple independent runs, so
"start FlowPilot" cannot imply "resume the current pointer" or "attach to an
already running parallel run."

## What Changes

- Treat every fresh formal FlowPilot invocation as a request to create a new,
  independent run.
- Preserve existing and parallel `running` runs as independent background
  workflows; startup must not automatically attach, merge, stop, or supersede
  them.
- Require explicit resume intent before using `.flowpilot/current.json`,
  a run id, or another active run as the target for continuation.
- Make `.flowpilot/current.json` UI focus/default-target metadata only for
  fresh startup; it is not startup authority.
- Add focused FlowGuard and runtime test coverage for existing, stale, and
  multiple parallel `running` runs during fresh startup.

## Capabilities

### New Capabilities

- `flowpilot-invocation-intent-isolation`: fresh startup and explicit resume
  are separate invocation intents, and fresh startup always creates a new run
  even when other FlowPilot runs already exist.

### Modified Capabilities

None. `parallel-flowpilot-run-isolation` is a related completed change, but it
has not been archived into `openspec/specs/`; this change records the missing
invocation boundary as a new focused capability instead of a partial delta.

## Impact

- `skills/flowpilot/SKILL.md`
- `skills/flowpilot/assets/flowpilot_router.py`
- Startup/resume focused tests under `tests/`
- Focused FlowGuard startup or parallel-run model under `simulations/`
- Installed local FlowPilot skill copy after verification

Heavyweight Meta and Capability simulations are skipped for this change by
explicit user direction. Focused FlowGuard checks and targeted runtime tests
remain required.
