## Context

FlowPilot already uses sealed packet/result bodies to preserve role
independence. That boundary is correct for normal work: a worker should not
complete its task by copying another role's body, and a reviewer should not
become the worker.

The observed failure is not that sealed bodies exist. The failure is that
repair context is assembled by multiple packet-family branches instead of one
current repair lineage owner. In the June 28 run, early worker repair packets
received no authorized reads, PM packets gradually accumulated only partial
blocker history, reviewer packets often received only the current PM
node-context plan, and the repair-loop counter excluded superseded blockers.
The system therefore kept creating repair nodes instead of either authorizing
the missing material, producing current evidence, or entering break-glass.

The repair must follow the repository's current-contract discipline:
single structured path, no fallback aliases, no broad compatibility surfaces,
and no historical body promotion to current evidence.

## Goals / Non-Goals

**Goals:**

- Keep normal sealed-body role isolation.
- Give PM, worker, reviewer, and FlowGuard enough shared repair-chain context
  to repair and recheck the same blocker lineage.
- Replace scattered repair-context inheritance with one runtime-owned repair
  dossier and one role-scoped authorization policy.
- Enforce fixed blocker-class next actions mechanically.
- Make five consecutive same-parent repair nodes without normal recovery enter
  Controller break-glass.
- Prove the behavior with a generated Cartesian TestMesh and observed-run
  replay, not a handful of hand-written examples.
- Sync and audit the installed local skill after source validation.

**Non-Goals:**

- No general "all bodies under parent are always open" rule.
- No compatibility path for older packet shapes, old repair fields, or old
  blocker counter semantics.
- No new role or repair decision family unless an existing packet/gate surface
  cannot express the current-contract repair.
- No claim that historical successful runs are current evidence.
- No final release/publish action.

## Decisions

### 1. Runtime owns one repair dossier per active repair lineage

The runtime will maintain a `repair_dossier` record keyed by the same active
repair lineage. A dossier is created when a substantive blocker opens a repair
lineage and is updated whenever Runtime issues a PM repair decision packet,
opens a repair packet, records a FlowGuard check, records a reviewer recheck,
supersedes a blocker by route mutation, or observes normal recovery.

Minimum dossier fields:

- `repair_dossier_id`
- `base_node_id`
- `root_parent_node_id`
- `current_repair_node_id`
- `repair_depth`
- `normal_recovery_seen`
- `blocker_ids`
- `blocked_packet_ids`
- `blocked_result_ids`
- `pm_repair_decision_ids`
- `repair_packet_ids`
- `flowguard_result_ids`
- `review_result_ids`
- `current_unresolved_obligations`
- `context_only_result_ids`
- `current_evidence_result_ids`
- `required_material_refs`
- `authorization_gap`

Rationale: one current dossier is simpler than adding more per-packet fallback
fields. It also gives tests one object to inspect for "what should each role
know now?"

Alternative rejected: open all parent bodies to all roles. That is too broad
and weakens the sealed-body independence principle.

### 2. One authorization function derives repair-context reads

Packet creation will call one policy surface:

`repair_context_authorized_result_reads(ledger, packet_role, route_node_id, packet_family, repair_dossier_id)`

Normal packets outside a dossier keep their existing minimal reads. Packets in
a dossier receive role-scoped reads:

- PM repair decision and PM repair planning: blocker reports, blocked target
  results, prior PM decisions, prior repair packets/results, reviewer recheck
  reports, FlowGuard summaries, repair depth, and authorization gaps.
- Worker repair packet: blocker report, PM decision, blocked target packet and
  result, current required material refs, previous repair failure reports, and
  relevant current-run evidence needed to produce fresh evidence.
- FlowGuard packet: current subject result, current evidence refs, repair
  obligations, blocker lineage summary, and prior FlowGuard/reviewer reports
  needed to model whether the current subject can progress.
- Reviewer packet: current subject result, matching FlowGuard result when
  required, current evidence refs, blocker lineage, prior reviewer blocker
  reports, and the PM decision that explains the repair target.

Rationale: a role-specific policy keeps sealed-body boundaries while avoiding
packet-family inheritance drift.

Alternative rejected: keep `_blocker_authorized_result_reads()` as the main
source. It recursively follows the current blocker body chain, but does not own
the full repair lineage or non-result material authorization.

### 3. Context-only bodies cannot close current evidence obligations or override the current review stage

Every inherited body in a dossier is classified as either `context_only` or
`current_evidence`. Context-only bodies may explain the failure and guide the
repair, but a worker, FlowGuard operator, reviewer, or PM cannot use them as
the current repair result.

Runtime and reviewer gates must reject:

- PM plan text submitted as repaired worker evidence or repair closure
  evidence.
- FlowGuard reports over PM plan text used as evidence for a worker repair.
- Reviewer passes that do not cite the current subject result and required
  current evidence refs.
- Historical blocked results treated as closure.

The dossier does not decide what the current packet must deliver. For reviewer
packets, `review_window` and the subject stage evidence matrix decide the
current subject lifecycle stage, required current fields, and forbidden
future-stage demands. A PM node-acceptance plan inside a repair dossier is
still a plan-stage subject unless that PM result claims already-produced
worker evidence or is submitted as repair closure evidence.

Rationale: this is the safety valve that lets roles read repair history without
letting them replace their current responsibility with someone else's work.

### 4. Fixed blocker next actions become hard gates

The stage evidence matrix already maps blocker classes to next actions. That
mapping must be enforced at PM repair decision and repair packet opening time.

Important current actions:

- `missing_required_information`: reissue the same packet with authorized
  material when runtime can authorize it; otherwise stop/control-block. It is
  not an ordinary route repair.
- `missing_matching_flowguard_report`: issue the matching FlowGuard packet for
  the current subject instead of writing another PM plan.
- `evidence_gap`: open the current evidence-producing repair path; PM
  node-context text does not close the gap.

Rationale: the observed run proved that advisory next-action rows are not
enough.

### 5. Glass-break counts same-parent repair nodes, not same text strings

The liveness rule is:

If the same repair dossier advances through five consecutive same-parent
repair nodes without recovery to a normal non-repair business node, Runtime
must expose Controller break-glass and must not issue another ordinary PM
repair packet for that dossier.

This count includes blockers marked `superseded_by_route_mutation` because
they remain part of the unresolved repair lineage until normal recovery or
explicit dossier closure.

Rationale: the user-visible failure is repeated repair without recovery, not
whether blocker text normalized to the same root cause string.

### 6. Tests are generated from a TestMesh matrix

The validation surface is a parent TestMesh with child suites:

- repair dossier creation and update
- role-scoped authorization
- normal-path privacy
- blocker next-action routing
- context-only evidence rejection
- reviewer subject alignment
- FlowGuard subject alignment
- glass-break depth
- observed-run replay
- install sync and audit

The generated matrix dimensions are:

- role
- packet family
- subject family and lifecycle stage
- blocker class
- repair depth
- authorization state
- evidence state
- subject completion-claim state
- recovery state

The parent gate passes only when required cells have current child evidence.
Skipped, stale, progress-only, background-running, or release-only evidence
does not satisfy the parent.

## Risks / Trade-offs

- Broad context can tempt AI roles to copy prior work -> mark prior bodies
  context-only and add negative tests proving old bodies cannot close current
  obligations.
- A new dossier object can become another ledger if overgrown -> keep it
  strictly repair-lineage scoped and generated from existing packet/result/
  blocker records where possible.
- Tests can become too slow -> use child suites and generated focused unit
  cases for routine confidence; keep release-required broader runs visible.
- Existing dirty work may already touch runtime/tests -> integrate by reading
  current diffs and avoid reverting or overwriting unrelated changes.
- Installed skill can be stale even when install check says OK -> serialize
  sync, audit, and check; do not run install audit in parallel with sync.

## Migration Plan

1. Add OpenSpec specs and verification contract for the new repair dossier and
   TestMesh behavior.
2. Add or update FlowGuard simulation/model evidence for the repair
   information-flow and TestMesh boundary.
3. Implement runtime dossier creation/update and role-scoped authorization.
4. Enforce blocker next-action hard gates.
5. Replace the semantic blocker threshold with same-dossier repair-node
   liveness for break-glass.
6. Update role cards to describe the current contract and context-only rule.
7. Add generated matrix tests and observed-run replay fixtures.
8. Run focused tests and FlowGuard model checks; fix failures.
9. Rebuild/check topology if model/test/card boundaries changed.
10. Sync repository-owned FlowPilot files to the installed skill, then audit
    installed content and run install checks.

Rollback is ordinary git rollback of this change set before install sync. After
install sync, rollback requires restoring the repository source and syncing the
installed copy again.

## Open Questions

- Whether to name the runtime record `repair_dossier` or reuse an existing
  `repair_transaction` table with a current-dossier projection. Default:
  create the smallest `repair_dossier` surface only if existing tables cannot
  express the role authorization policy cleanly.
- Whether observed-run replay should use the full June 28 ledger as a fixture
  or a minimized synthetic ledger preserving the same failure chain. Default:
  use a minimized fixture for routine tests and keep full-run replay as a
  release-scope validation.
