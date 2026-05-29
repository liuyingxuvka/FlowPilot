## Context

The repository now has a small AI project protocol kernel and a deterministic
stress layer. They answer "what must be true" but not yet "how the real clean
runtime moves." The old FlowPilot runtime contains useful lessons and assets,
but it also carries historical complexity: fixed startup roles, many
compatibility paths, and hard-to-explain state surfaces.

This change builds the clean runtime around one durable rule: the black-box
ledger is the authority. Every legal action is a state transition. Anything not
written to the ledger is context, not proof.

## Target Shape

The runtime has stable responsibilities, not permanent people:

- Router: selects the next legal action from the ledger.
- Planner: creates route versions and task packets.
- Worker: executes a scoped packet.
- Reviewer: independently checks packet results.
- FlowGuard operator: models a named risk and returns a scoped report.

Any responsibility may be served by a newly leased background agent. A lease is
a bounded permission to do one kind of work for one route scope. It may ACK,
report safe progress metadata, submit a typed result, time out, close, or be
superseded. Closed or stale leases cannot produce authoritative output.

## Runtime Components

### Ledger

The ledger stores the user goal, acceptance contract, route versions, active
route pointer, leases, packet envelopes and bodies, result envelopes and bodies,
review reports, FlowGuard work orders, validation evidence, and final closure.
It is serializable JSON so tests, consoles, and background checks can inspect
it without chat memory.

### Router

The router is deterministic. It does not do product work. It only returns a
next-action object such as `create_route`, `lease_agent`, `wait_for_ack`,
`wait_for_result`, `create_flowguard_order`, `review_result`, `repair_packet`,
`render_console`, or `close_project`.

### Packets

Packets physically separate envelope and body. The envelope is public routing
metadata: ids, route version, responsibility, lease, allowed tools, required
output type, hash, freshness generation, and review requirement. The body is
private task content for the addressed lease/responsibility. The public console
may show envelope status but not body text.

### FlowGuard Work Orders

Every non-trivial gate must say what is being modeled before it starts. The
runtime uses the protocol scheduler table to choose the FlowGuard skill from
`modeled_target`, not from the requesting role. A green report for the wrong
target is blocked.

### Review And Closure

Review requires an independent lease. It checks role origin, lease state,
packet id, route version, evidence freshness, result shape, FlowGuard target,
and body hash. Final closure walks backward from the user goal through the
active route, accepted packet results, review reports, FlowGuard reports, fresh
validation evidence, and explicit gaps.

### Console

The first UI surface is intentionally small: a startup record and a status
projection. It shows project id, route version, active packets, waiting leases,
FlowGuard work orders, blockers, and final gate state. It must never expose
sealed packet bodies or result bodies.

## Development Flow

The implementation itself is modeled as a FlowGuard development-process route:

1. OpenSpec locks the runtime contract.
2. FlowGuard development-process model checks the planned build order.
3. Runtime ledger, packet, lease, router, review, FlowGuard, closure, and
   console code are implemented.
4. Fake runtime scenarios exercise success, replacement, wrong target,
   self-review, stale route output, stale evidence, and console isolation.
5. TestMesh rows separate routine evidence from release evidence.
6. Install sync and local git closure happen only after evidence is current.

## Reuse Rules

Allowed reuse:

- old startup panel and icon assets;
- old packet envelope field names where they still match the clean protocol;
- old historical bad-case families;
- old install and background-check scripts.

Forbidden reuse:

- old `.flowpilot` runtime state as current proof;
- fixed six-agent startup as a new invariant;
- stale result artifacts as fresh evidence;
- chat or role memory as route authority.

## Validation

- `openspec validate build-black-box-flowpilot-runtime --strict`
- `python simulations/run_ai_project_runtime_development_checks.py`
- `python simulations/run_ai_project_runtime_checks.py`
- `python -m pytest tests/test_ai_project_runtime.py`
- Existing protocol and stress checks.
- Background Meta and Capability checks with inspected artifacts.
- Install sync, install audit, install check, and local git commit.
