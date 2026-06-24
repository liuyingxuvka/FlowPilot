## Context

The current runtime has a declared `parent_backward_replay_review` review
window and a route-action policy row for parent replay review, but the
core-runtime special path for `task.parent_backward_replay` accepts and records
the parent replay after FlowGuard approval without opening the normal
independent Reviewer packet. Final closure then detects missing independent
reviews late, after child/module and top-level replay results may both be
accepted.

This change repairs the current-contract path only. Old runs and in-flight old
state are out of scope and must not be migrated, translated, or promoted into
current evidence.

## Goals / Non-Goals

**Goals:**

- Make parent/module/top-level replay closure a two-step current contract:
  replay task result accepted, then independent replay review accepted.
- Enforce route-topology ordering: child/module replay reviews close before
  parent/top-level replay can be issued or consumed.
- Make final-closure missing-review repair produce one real, routable Reviewer
  packet for the deepest unresolved dependency.
- Keep diagnostic blocker reporting broad while keeping actionable repair
  dependency-ordered and singular.
- Bind runtime, prompts, policy rows, fake-AI coverage, FlowGuard simulations,
  and install/version evidence to the same current path.

**Non-Goals:**

- No old-run migration.
- No compatibility shim, legacy field alias, prose parsing, or old-router
  fallback.
- No automatic repair of currently running old state.
- No new role, packet kind, ledger family, or parallel review system when the
  existing `review.any_current_subject` contract can express the repair.

## Decisions

### Decision: Add reviewed replay state without adding a new packet family

The runtime will keep `task.parent_backward_replay` as the replay task family
and use existing `review.any_current_subject` review packets for the
independent review. Helper functions will distinguish:

- raw replay accepted;
- replay review accepted;
- replay fully closeable for parent/topology progression.

Rationale: the review-window contract already declares
`parent_backward_replay_review`; adding another packet family would duplicate
existing current review machinery.

### Decision: Gate parent/top-level progression on reviewed child replay

Route traversal and parent replay packet issuance will use a topology-aware
predicate that requires every effective child node needing parent replay to have
raw replay and independent replay-review evidence before the parent/top-level
can progress.

Rationale: the user's desired mental model is dependency-ordered. A top-level
replay that is accepted while a child/module replay review is missing creates
false closure pressure and late final-closure blockers.

### Decision: Final closure reports all blockers but returns one actionable
repair

Closure blocker lists may still include all missing review ids for diagnostics.
The runtime next-action path will derive the deepest/earliest missing replay
review and issue or dispatch only that packet.

Rationale: broad diagnostics are useful, but simultaneous parent/child repair
actions obscure dependency ownership and can create non-routable late packets.

### Decision: No fallback and no old-state migration

If old or in-flight state violates the new current contract, it is not converted
inside this change. New formal FlowPilot invocations start fresh and must follow
the new contract. Historical runs can seed regression fixtures only.

Rationale: FlowPilot is maintained as a new-only current-contract runtime.
Compatibility translation would create long-lived maintenance debt and weaken
the single-path guarantee.

## Risks / Trade-offs

- **Risk: additional review packets increase route length** -> The extra packet
  is the declared independent-review gate; it replaces late break-glass
  recovery with normal runtime work.
- **Risk: existing tests expecting direct parent replay closure fail** -> Update
  those tests to assert the new two-step closure. Keep negative coverage that
  raw replay alone does not close parent evidence.
- **Risk: final closure could loop on a missing review** -> The actionable
  selector must be idempotent and must find existing open/assigned/accepted
  review packets before issuing a new one.
- **Risk: prompt cards diverge from runtime behavior** -> Card instruction
  coverage and model-test alignment must cover the new sequencing language and
  no-fallback boundary.
