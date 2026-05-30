## Context

The fresh runtime currently has a symmetric packet lifecycle for every backend
role. The ordinary success path is:

`task -> flowguard_check -> review -> validation -> closure`

That symmetry made missing-role and side-command bugs easier to catch, but the
validator packet is now doing mostly mechanical evidence confirmation that
Router already knows how to enforce. In contrast, PM repair and disposition
packets can apply route mutation or waiver decisions immediately after PM
submission.

## Goals / Non-Goals

**Goals:**

- Remove the validator AI hop from the ordinary success path.
- Keep validation evidence as a first-class ledger artifact.
- Let Router/system code create validation evidence only after the matching
  FlowGuard and reviewer gates pass.
- Keep legacy validation packets readable and enforceable for old runs and
  repair paths.
- Gate high-risk PM decisions before they mutate route state or waive blockers.

**Non-Goals:**

- Do not remove FlowGuard or reviewer gates from ordinary work.
- Do not remove final closure.
- Do not make low-risk repair slower when it only reissues work or asks for
  more evidence.
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

### Decision: PM high-risk decisions are staged before side effects

PM repair and PM disposition packets are split into low-risk and high-risk
decisions.

Low-risk decisions can apply directly:

- `same_node_repair`
- `sender_reissue`
- `collect_more_evidence`
- `rerun_validation`
- `quarantine_evidence`
- `stop_for_user`
- PM disposition `accept`, `repair`, `block`, or `stop`

High-risk decisions are staged:

- PM repair `mutate_route`
- PM repair `waive_with_authority`
- PM disposition `mutate_route`

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
- [Risk] Staging PM decisions adds packets on rare high-risk branches.
  -> Mitigation: only route mutation and waiver-class decisions pay the extra
  cost; ordinary reissue/repair stays direct.
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
2. Add a focused FlowGuard model for automated validation and PM risk gates.
3. Add runtime ledger fields and helpers for system validation evidence and PM
   decision gates.
4. Change reviewer-pass progression to create system validation evidence and
   issue closure directly.
5. Stage high-risk PM repair/disposition decisions until FlowGuard, reviewer,
   system validation, and closure pass.
6. Update focused tests and runtime check runners.
7. Run OpenSpec, FlowGuard, targeted pytest, install sync/audit/check, and
   background meta/capability checks before local git commit.

Rollback strategy: restore reviewer pass to issue validator packets and apply
PM decisions directly, but keep any new validation/PM gate records as ignored
ledger metadata for compatibility.
