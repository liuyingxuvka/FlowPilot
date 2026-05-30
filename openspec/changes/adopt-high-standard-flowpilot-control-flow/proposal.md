## Why

The new black-box FlowPilot runtime has restored route-node execution, but it
still lets PM planning happen before the runtime has a mandatory high-standard
contract, current material/skill discovery, node-entry acceptance plans, repair
classification, parent backward replay, and final requirement-evidence closure.
That leaves the rebuilt runtime cleaner than the old router, but not yet strong
enough to guarantee the user's expectation that FlowPilot work is completed to
the highest reasonable standard and checked all the way back to the request.

## What Changes

- Add a new high-standard control-flow layer to the new runtime:
  - PM must establish a highest-reasonable-outcome contract before route
    planning can close.
  - Current-run material discovery and local skill inventory must be reviewed
    before route planning closes.
  - Selected child/process skills must become explicit standard contracts with
    evidence obligations, not raw availability claims.
  - Every route node must receive a node acceptance plan before a node task
    packet is legal.
  - Node rejection defaults to same-node repair; route mutation is reserved for
    wrong node shape, missing work class, or stale/invalid route assumptions.
  - Parent/module nodes require backward replay before they can close when they
    have children.
  - Final closure must build a requirement-evidence matrix that links startup
    intent, PM high-standard requirements, child-skill obligations, route
    nodes, FlowGuard work, reviews, validation, and PM dispositions.
- Extend fake-host rehearsals and FlowGuard models so green checks prove these
  gates, not only the happy path of recursive route traversal.
- Keep the new runtime dynamic-agent design. Do not reintroduce old fixed crew
  topology, Cockpit UI requirements, old router authority, or compatibility
  surfaces.

## Capabilities

### New Capabilities
- `flowpilot-high-standard-control-flow`: Mandatory high-standard workflow
  gates for the new black-box FlowPilot runtime, covering PM high-standard
  contract, discovery, skill standards, node acceptance, repair decisions,
  parent backward replay, and final requirement-evidence closure.

### Modified Capabilities
- `flowpilot-closure-kernel`: Final closure now depends on the high-standard
  requirement-evidence matrix in addition to route-wide packet/node closure.
- `role-child-skill-use`: Selected child and process skills now feed the new
  runtime's skill standard contracts and node acceptance plans.
- `material-artifact-map`: New runtime material discovery is a mandatory
  pre-planning gate while still treating material metadata as navigation, not
  acceptance evidence.
- `recursive-route-parent-entry`: Parent/module replay is promoted into the new
  runtime's high-standard node closure rules.

## Impact

- Affected code:
  - `skills/flowpilot/assets/ai_project_runtime/runtime.py`
  - `skills/flowpilot/assets/ai_project_runtime/run_shell.py`
  - `skills/flowpilot/assets/flowpilot_new.py`
  - recursive runtime tests and fake-host rehearsals
  - FlowGuard recursive-route model checks
- Affected artifacts:
  - OpenSpec change files under this change directory
  - FlowGuard adoption notes/results when validation completes
  - local installed FlowPilot skill after implementation
- No new third-party dependencies are planned.
