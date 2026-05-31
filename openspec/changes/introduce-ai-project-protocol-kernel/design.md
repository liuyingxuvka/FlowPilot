## Context

The old system proved several important ideas: model-first work helps, packet
boundaries help, reviewers need to be independent, and background checks need
durable evidence. It also accumulated weight: fixed role assumptions, route
compatibility paths, stale runtime evidence, and many places where a progress
signal could be mistaken for completion.

The clean protocol treats the old system as a reference library, not as the
foundation. The new foundation is a small contract:

`ProjectInput x ProjectState -> Set(ProjectOutput x ProjectState)`

Every actor, task packet, result packet, review, model check, and final claim
updates the project black box. Chat history, agent memory, and old run folders
are not source of truth.

## Plain Model

The target system has four stable responsibilities and a dynamic number of
agent instances:

1. Router: decides the next legal action from the ledger.
2. Planner: turns the user goal into route versions and task packets.
3. Worker: performs scoped work from a sealed task packet.
4. Reviewer and explicit FlowGuard operator responsibilities: check work, model
   risk, select FlowGuard routes, and block weak evidence.

These are responsibilities, not permanent people. The Agent Pool Manager may
lease one or many background agents for a responsibility and may close, replace,
or retry agents when they stop responding or produce invalid packets.

## Core Components

### Legacy Reference

Before implementation, the repository keeps a backup under
`backups/ai-project-protocol-legacy-snapshot-20260529/`. The backup is allowed
for asset reuse and historical failure-case mining. It is not allowed to supply
current route truth, current validation evidence, or fixed-agent requirements.

### Project Black Box

The black box is the authoritative ledger. It stores:

- user goal and acceptance contract;
- route versions and active route pointer;
- agent leases and heartbeats;
- task packet envelopes and bodies;
- result packet envelopes and bodies;
- review reports;
- FlowGuard model routes and evidence;
- final backward validation claims.

The router may read envelopes and ledger state. Workers may read only their own
packet body and approved reference material. Reviewers may read submitted
result bodies and required evidence. This is the isolation boundary.

### Dynamic Agent Pool

The Agent Pool Manager owns agent lifecycle:

- create lease;
- bind lease to one packet or review job;
- require ACK as liveness only;
- require typed result packet for completion;
- timeout stale leases;
- close failed leases;
- prevent closed leases from submitting new authoritative output;
- retry only through a new packet or new lease id.

ACK is never completion. Background progress is never completion. Completion
requires a typed result packet, evidence ids, and review acceptance.

### Sealed Packets

A task packet has an envelope and a body. The envelope contains routing fields:
packet id, route version, role responsibility, allowed tools, input evidence,
required output schema, timeout, and reviewer requirement. The body contains
the actual work instructions and may be hidden from other agents.

A result packet also has an envelope and a body. The envelope contains output
type, producer lease id, packet id, evidence ids, touched paths, status, and
freshness timestamp. The body contains the produced work and reasoning.

The router decides from envelopes and reviews; it does not need to read all
private work bodies.

### FlowGuard Route Scheduler

FlowGuard is used as a first-class operator, not as a final checklist. The
scheduler chooses the sub-skill by the risk being modeled:

- goal and behavior shape: `model-first-function-flow`;
- staged development order: `flowguard-development-process-flow`;
- UI interaction shape: `flowguard-ui-flow-structure`;
- code structure before implementation: `flowguard-code-structure-recommendation`;
- large structure split: `flowguard-structure-mesh`;
- test/evidence hierarchy: `flowguard-test-mesh`;
- model/test obligation comparison: `flowguard-model-test-alignment`;
- model hierarchy: `flowguard-model-mesh`;
- failure after a green model: `flowguard-model-miss-review`;
- simplification of overgrown paths: `flowguard-architecture-reduction`.

The scheduler itself is modeled and tested. A FlowGuard operator packet must
say which thing is being modeled: the target product, the development process,
the packet lifecycle, the dynamic agent lifecycle, the evidence lifecycle, or
the final closure claim.

### Final Backward Validation

Final closure starts from the user's original goal and walks backward:

1. What did the user ask for?
2. Which route version claims to satisfy it?
3. Which packets produced the deliverables?
4. Which reviews accepted those packets?
5. Which FlowGuard checks modeled the risks?
6. Which executable validations ran after the last relevant change?
7. Which gaps remain skipped, stale, blocked, or out of scope?

The system may only report complete when that backward chain is current and
unbroken.

## Failure Cases To Model First

- Agent gives ACK and then no output.
- Agent gives output in the wrong shape.
- Agent produces output after its lease is closed.
- Agent reports progress only and router treats it as done.
- Worker reviews itself.
- Reviewer passes without checking evidence.
- FlowGuard operator models the target product when the risk was the
  development process, or the reverse.
- Route changes while old packets remain open.
- Old route output is accepted into a new route version.
- Evidence from before the latest source change is reused as fresh.
- Final report claims completion without walking backward to the user goal.

## Implementation Placement

The first implementation is a protocol kernel, not a replacement runtime:

- `skills/flowpilot/assets/ai_project_protocol/` stores the readable protocol
  contract and schema examples.
- `simulations/ai_project_protocol_model.py` stores the executable model.
- `simulations/run_ai_project_protocol_checks.py` runs model scenarios and
  writes a result artifact.
- `tests/test_ai_project_protocol_kernel.py` checks the model and protocol
  assets.

Later work can wire this kernel into a new startup panel or a new router, but
this change intentionally stops at the verified protocol kernel.

## Validation

- `openspec validate introduce-ai-project-protocol-kernel --strict`
- `openspec validate --strict`
- `python simulations/run_ai_project_protocol_checks.py`
- `python -m pytest tests/test_ai_project_protocol_kernel.py`
- Background `python simulations/run_meta_checks.py` with inspected artifacts.
- Background `python simulations/run_capability_checks.py` with inspected
  artifacts.
- Install sync, install audit, install check, and local repository git commit.
