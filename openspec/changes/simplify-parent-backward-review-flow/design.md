## Context

FlowPilot currently has a repair that treats `task.parent_backward_replay` as a
raw replay result and then opens a separate `review.any_current_subject` packet
to review that replay result. That repair prevents late final-closure
glassbreaks, but it makes the V-shaped closure path longer than the product
model requires: the reviewer who performs parent/module backward replay should
be the closure reviewer for that parent/module gate.

The project constraints are strict:

- one current structured path per behavior;
- no fallback, legacy alias, old-state migration, prose parsing, or historical
  artifact promotion;
- downstream route progression must not open while the current parent/module
  closure review is incomplete;
- fake-AI Cartesian coverage and TestMesh ownership must cover the same
  current contract.

## Goals / Non-Goals

**Goals:**

- Replace the two-step parent replay + independent review path with one
  current parent backward Reviewer packet.
- Retire positive runtime authority for `task.parent_backward_replay`.
- Make parent/module closure review a frontier gate: one active obligation,
  current node only, no downstream route advance before PM absorption.
- Treat multiple unclosed parent/module review gaps as injected corrupt state
  or control-plane damage, not a normal repair queue.
- Bind the runtime, prompt cards, contract matrices, fake-AI responder,
  FlowGuard model, Cartesian test matrix, router tiers, acceptance TestMesh,
  topology, install sync, version, and changelog to the same semantics.

**Non-Goals:**

- No compatibility support for existing old/in-flight runs.
- No automatic translation from `task.parent_backward_replay` into the new
  review family.
- No second reviewer packet for the parent backward review result.
- No broad route refactor beyond the parent backward closure boundary.

## Decisions

### Decision: Use a first-class parent backward review family

The current positive family becomes `review.parent_backward_replay` with
`packet_kind=review` and `route_scope=parent_backward_replay`. The route scope
can keep the parent backward replay name because it names the route phase; the
family id and packet kind carry the review semantics.

Alternatives considered:

- Keep `task.parent_backward_replay` and add a flag such as
  `reviewed_by_role`: rejected because it preserves a task-shaped positive
  path and makes it easy to accidentally accept old task evidence.
- Keep the previous two-step repair: rejected because it over-designs the V
  closure path and creates an avoidable second review obligation.

### Decision: Parent backward review result is the closure evidence

A passing parent backward review closes the parent replay obligation after
runtime mechanical validation and FlowGuard/system validation for the packet.
The closure record stores the source review packet/result, reviewer role,
parent node, child nodes, child evidence refs, blockers, and current repair
child result ids. It does not store a separate review id over the result.

### Decision: PM absorption remains required

The reviewer closes the quality/process review gate; PM still owns route
progression. After a passing parent backward review, the runtime opens or
reuses the PM parent segment decision. Only PM `continue` may close the
parent/module frontier and permit sibling/downstream/ancestor progression.

### Decision: Impossible multi-gap states hard-block

Normal runtime cannot legally advance beyond an unabsorbed parent backward
review. Therefore a state containing multiple unclosed parent/module review
gaps is not a normal "choose deepest" scheduling case. It is reported as a
control-plane corruption/blocker. Tests may inject such states, but the oracle
must expect hard block, not compatibility repair.

### Decision: Cartesian coverage is model-scoped and TestMesh-owned

The fake-AI Cartesian matrix declares finite axes for route shape, payload
profile, timing, evidence state, and expected runtime action. Legal
combinations are executed through fake-AI payloads where possible. Impossible
combinations are retained as negative injected-state cases with an explicit
oracle. Acceptance TestMesh gains cells that own these shards and prevents
release confidence when cells are missing.

## Risks / Trade-offs

- **Risk: lingering positive `task.parent_backward_replay` references** ->
  Mitigate with deleted-field/current-contract searches and negative tests that
  reject task-shaped parent replay evidence.
- **Risk: parent closure advances without PM absorption** -> Mitigate with
  runtime gating tests, router-route tests, and terminal/final-preflight
  blockers.
- **Risk: fake-AI matrix becomes broad but not authoritative** -> Mitigate by
  making the matrix emit required shard/cell ids consumed by TestMesh and model
  test alignment.
- **Risk: old two-step tests keep the wrong behavior alive** -> Mitigate by
  renaming/reversing tests that currently expect an independent second review
  and adding negative assertions that no such packet is issued.
