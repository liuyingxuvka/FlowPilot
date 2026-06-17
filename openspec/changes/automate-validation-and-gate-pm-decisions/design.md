## Context

The fresh runtime currently has a symmetric packet lifecycle for every backend
role. The ordinary success path is:

`task -> flowguard_check -> review -> validation -> closure`

That symmetry made missing-role and side-command bugs easier to catch, but the
validator packet is now doing mostly mechanical evidence confirmation that
Router already knows how to enforce. In contrast, PM continue-repair decisions
can change control state or release repair work after PM submission.

## Goals / Non-Goals

**Goals:**

- Remove the validator AI hop from the ordinary success path.
- Keep validation evidence as a first-class ledger artifact.
- Let Router/system code create validation evidence only after the matching
  FlowGuard and reviewer gates pass.
- Keep legacy validation packets readable and enforceable for old runs and
  repair paths.
- Gate PM continue-repair decisions before they change control state or open
  resulting repair work.

**Non-Goals:**

- Do not remove FlowGuard or reviewer gates from ordinary work.
- Do not remove final closure.
- Do not rewrite legacy router/card surfaces in this change.

## Decisions

### Decision: Replace ordinary validator packets with system validation evidence

After a reviewer pass, the runtime records a system-owned validation evidence
row for the subject packet. The evidence row references the subject packet,
reviewer packet/result, accepted review id, current source generation, and
matching FlowGuard report status. Only then does the runtime issue a closure
packet.

The legacy `validation` packet kind remains supported. Existing runs or repair
paths that already contain validator packets still parse pass/fail outcomes,
record failed evidence when needed, and require same-class recheck.

### Decision: Closure still owns final release

Closure remains a packet role. It consumes validation evidence, active blocker
state, accepted packet state, reviewer state, and matching FlowGuard state.
System validation is not terminal completion; it is the evidence row that makes
closure eligible to run.

### Decision: PM continue-repair decisions are staged before side effects

PM repair decisions that continue repair work are staged:

- `repair_current_scope`
- `repair_parent_scope`
- `redesign_route`

Terminal PM dispositions remain terminal:

- `waive_with_authority`
- `stop_for_user`

Route-mutating PM disposition decisions are also staged before they change the
route. PM disposition `accept` after a fully closed node is not a continue
repair decision.

The staged decision creates a PM decision gate record and issues a FlowGuard
packet. FlowGuard pass issues a reviewer packet. Reviewer pass records system
validation evidence and issues closure. Closure applies the staged PM decision.

### Decision: PM cannot clear or mutate through review prose

FlowGuard and reviewer gates inspect whether the PM decision is safe to apply,
but they do not apply it themselves. The runtime applies the staged decision
only after the gate closure packet is accepted.

## Risks / Trade-offs

- [Risk] Removing validator AI could hide a real human-quality review gap.
  -> Mitigation: reviewer remains the human-quality/adversarial gate, and
  system validation records evidence freshness and blocker state before
  closure.
- [Risk] Staging PM continue-repair decisions adds packets to repair branches.
  -> Mitigation: the repair path is uniform and the evidence prevents direct
  repair side effects from bypassing FlowGuard, PM absorption, Reviewer, and
  system closure.
- [Risk] Existing validation-packet tests and rehearsals may assume the old
  happy path.
  -> Mitigation: update focused tests and runner evidence while leaving legacy
  validation packet handling in place.
- [Risk] PM decision gate closure could accidentally trigger ordinary node
  closure side effects.
  -> Mitigation: closure side effects check staged PM decision gates before
  route-node closure handling.

## Migration Plan

1. Add OpenSpec requirements and tasks.
2. Add a focused FlowGuard model for automated validation and PM decision gates.
3. Add runtime ledger fields and helpers for system validation evidence and PM
   decision gates.
4. Change reviewer-pass progression to create system validation evidence and
   issue closure directly.
5. Stage PM continue-repair and route-mutating disposition decisions until
   FlowGuard, reviewer, system validation, and closure pass.
6. Update focused tests and runtime check runners.
7. Run OpenSpec, FlowGuard, targeted pytest, install sync/audit/check, and
   background meta/capability checks before local git commit.

Rollback strategy: restore reviewer pass to issue validator packets and apply
PM decisions directly, but keep any new validation/PM gate records as ignored
ledger metadata for compatibility.
