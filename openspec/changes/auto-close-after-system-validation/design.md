## Context

The current successful chain is:

`task -> flowguard_check -> review -> system_validation -> closure_packet`

The Closure Officer packet is no longer doing fresh judgement in the ordinary
path. It receives a subject that already has:

- an accepted result,
- matching FlowGuard evidence,
- accepted reviewer evidence,
- system validation evidence.

The useful work of closure is still real. It updates route state and accounting.
That work can be performed by the runtime immediately after system validation
passes.

## Goals / Non-Goals

**Goals:**

- Remove the ordinary Closure Officer packet hop.
- Remove validator and Closure Officer as dispatchable runtime roles.
- Keep closure as a mandatory system state transition.
- Keep the same closure side effects as before.
- Route system-validation failures back to PM repair.
- Keep PM high-risk decision gates intact; they apply only after system
  validation and system-owned closure.

**Non-Goals:**

- Do not remove final route-wide closure checks.
- Do not remove validation evidence.
- Do not remove reviewer or FlowGuard gates.
- Do not rewrite public UI or CLI behavior except where packet progression
  naturally changes.

## Decisions

### Decision: System validation pass triggers system closure

After reviewer pass, the runtime records system-owned validation evidence. If
that evidence passes, the runtime records a system closure row and runs closure
side effects for the subject packet. No Closure Officer work packet is issued on
that ordinary path.

### Decision: System validation failure becomes a PM repair blocker

If system validation finds missing review linkage, missing matching FlowGuard
evidence, stale decision-gate evidence, or another blocker, the runtime records
failed validation evidence, marks the subject blocked, records an active
`system_validation` blocker, and issues a PM repair decision packet.

### Decision: Closure side effects are subject-based

Closure side effects are keyed to the subject packet, not to a Closure Officer
packet. The runtime records a system closure row, then applies the same
subject-level state transition.

### Decision: Old validation and closure packets are removed

The clean new runtime does not issue, accept, or document validator packets or
Closure Officer packets. A fresh run can only dispatch PM, worker-class,
FlowGuard, reviewer, and specialized QA/research roles. Validation and closure
are ledger actions performed by the system.

## Risks / Trade-offs

- [Risk] A bug in system closure could advance without old packet evidence.
  -> Mitigation: add a dedicated `system_closures` ledger row, FlowGuard model
  obligations, focused tests, and fake AI rehearsal checks.
- [Risk] System validation failure could get stuck if it is not routed to PM.
  -> Mitigation: create a focused test and model hazard for failed system
  validation requiring PM repair.
- [Risk] Old local runs with validator or closure packets cannot continue.
  -> Mitigation: this is intentional for the clean rebuild. The next FlowPilot
  use starts from a fresh run rather than carrying old protocol state forward.

## Migration Plan

1. Add OpenSpec requirements and tasks.
2. Update the FlowGuard validation/PM-gate model from closure packet closure to
   system-owned closure.
3. Refactor runtime closure side effects into a subject-based helper.
4. Replace ordinary closure packet issuance with automatic system closure.
5. Route system validation failures to PM repair.
6. Update tests, runners, and fake AI rehearsal expectations.
7. Remove validator/closure role contract leftovers.
8. Run full validation and only then sync the local install and commit.
