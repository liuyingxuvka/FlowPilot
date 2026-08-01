## Context

See `proposal.md` for motivation. The public FlowPilot entry delegates current
runtime authority to `flowpilot_core_runtime`. Current node closure already
ends at a PM-disposition packet, but an ordinary `accept` immediately records
the node as accepted and selects the next node from the old route order.

The runtime already has one staged-effect chain for structural PM decisions:
the source result is held pending while FlowGuard reviews it, PM absorbs the
FlowGuard report, Reviewer independently challenges the absorbed result, system
validation closes, and only then is the effect committed. The design reuses
that chain rather than introducing a checkpoint subsystem.

## Goals / Non-Goals

**Goals:**

- Make the top-level milestone gate unconditional and topology-derived.
- Make the newly audited complete remaining plan the only continuation
  authority.
- Keep old and new plan equality legal while still requiring fresh review.
- Preserve accepted history and replace only unfinished work when the plan
  changes.
- Keep interrupted-run recovery on the same current gate.
- Reduce duplicated planning work after the new loop is proven.

**Non-Goals:**

- No L0-L4, risk score, heuristic gate selection, optional replanning, feature
  flag, A/B experiment, compatibility reader, or fallback continuation.
- No new role, checkpoint ledger, replan ledger, goal-gap ledger, or alternate
  display-plan authority.
- No mutable tag, moving release, publication before frozen validation, or
  release claim that conflates source, model, test, install, Git, and GitHub
  identities.

## Decisions

### 1. A major milestone is a top-level route node

The runtime derives the gate from `parent_node_id == ""`. A top-level leaf
triggers it directly; a top-level parent/module triggers it only after existing
child completion and backward-composition review.

This gives a hard, deterministic boundary without asking AI to classify work
size. Treating every nested leaf as a global gate was rejected because it would
turn local execution steps into repetitive whole-project planning and would
interfere with parent composition.

### 2. PM disposition remains the single commit owner

The existing `pm_disposition.node_pm_disposition` family gains a top-level
milestone branch. Its current fields remain, and top-level acceptance also
requires:

```json
{
  "milestone_audit": {
    "completed": [
      {
        "node_id": "<accepted top-level node id>",
        "outcome": "Current milestone outcome"
      }
    ],
    "deviations": [],
    "remaining": [
      {
        "obligation": "Remaining goal obligation",
        "gap": "What is not closed yet",
        "owner_node_ids": ["next-node-id"]
      }
    ],
    "prior_plan_assessment": "Why the old remaining plan is or is not still fit.",
    "replan_rationale": "Why this complete remaining plan follows from current state."
  },
  "remaining_route_plan": {
    "schema_version": "flowpilot.route_plan.v1",
    "nodes": []
  }
}
```

The milestone branch is projected from route topology into the existing packet
contract. Nested child dispositions do not require the global audit. A new
packet family was rejected because it would duplicate PM-disposition identity,
result repair, recovery, and closure mechanics.

### 3. One staged effect holds acceptance and route renewal

Top-level `accept` never calls frontier advance directly. It stages one
`commit_milestone_plan_renewal` effect bound to the current packet, result,
node, route version, plan fingerprint, and source generation. The result body
remains the sealed authority; staged state stores only commit material and
identity.

The existing structural chain performs FlowGuard review, PM absorption,
Reviewer review, and system validation. Reviewer is explicitly authorized to
read the source milestone result and absorbed FlowGuard result. A direct
Reviewer-only shortcut was rejected because route mutation remains a
process/state change that benefits from the current FlowGuard boundary.

### 4. Remaining-plan validation is suffix-aware

The initial strict route-plan parser remains non-empty. A dedicated remaining
plan parser reuses the same node normalization but permits `nodes: []` only for
the terminal milestone branch.

Coverage validation computes the acceptance items not already closed by
accepted history or the current proposed disposition. Every such item must
have an owner in the remaining plan. An empty plan also requires an empty audit
`remaining` list and zero current unclosed hard obligations.

The mechanical layer checks structure, identity, coverage, and freshness.
FlowGuard and Reviewer own the substantive questions: whether completed claims
are true, deviations are honest, the list of gaps is complete, the next
milestone is detailed enough, and the whole route reaches the final goal.

The completed audit is cumulative for the active top-level prefix. PM writes
each row's current top-level `node_id` and semantic outcome. At the staging and
commit boundary, the runtime binds every row to its complete runtime-issued
evidence set and binds the current frozen `contract_hash`; PM-supplied copies of
those machine fields are rejected. This prevents silent final-goal drift while
keeping semantic output small and avoiding a second ledger. Every non-empty
remaining gap names one or more `owner_node_ids`, and every named owner must
belong to the submitted remaining-plan node set. Every current hard obligation
must be covered, but helper nodes whose work is already covered by a parent
milestone do not need fabricated gap rows.

### 5. Equality renews evidence without route churn

The runtime canonicalizes the submitted remaining plan and the active
unfinished suffix. Exact equality still creates a new milestone audit,
FlowGuard result, PM absorption, review, validation, and disposition, but it
does not increment route version.

This treats “unchanged” as a legitimate reviewed conclusion. Requiring a
structural difference was rejected because it would reward artificial plan
churn rather than better judgment.

### 6. Changed plans replace only the unfinished suffix

For a changed plan, the runtime creates one new route version:

- accepted nodes and their evidence remain current and are carried into the
  new route membership;
- unchanged unfinished nodes may be carried forward with the same current
  identity;
- removed unfinished nodes and their open packets are superseded/quarantined;
- a changed node specification must use a fresh node identity;
- new nodes are materialized from the reviewed plan;
- the next node is selected only after the atomic commit.

Reusing full-route redesign was rejected because its existing repair semantics
supersede the whole route and can reset completed history.

### 7. Recovery stays at the staged gate

Routing reconciliation recognizes a submitted top-level milestone disposition
with an unapplied staged effect. It re-exposes the exact missing FlowGuard,
PM-absorption, Reviewer, validation, or commit obligation. It never calls the
old frontier advance path merely because the source result exists.

### 8. Node-entry planning is contracted only after parity evidence

The reviewed remaining plan must make its first node execution-ready. The
existing node-acceptance-plan gate remains during the first implementation
slice so the new behavior can be validated without silently deleting its
context-package and acceptance-projection duties.

After current model/test evidence shows those duties are fully present in the
reviewed remaining plan and handoff, a separate affected architecture-reduction
step may remove the redundant gate. It must be a direct current replacement,
not a second planning mode.

### 9. Keep the loop direct and lightweight

The runtime has one topology-derived milestone loop. It does not classify work
into L0-L4 levels, score tiers, optional replanning modes, or parallel route
authorities. The initial route may be coarse; the hard gate is the repeated
audit-and-rewrite point where new evidence makes the next route more detailed
without changing the final-goal contract.

### 10. Keep machine bindings runtime-owned

The milestone result contract may show a minimal shape, but the shape must be
derived from the current route binding. When the runtime supplies concrete
remaining owner node ids, the example nodes and their owner ids must agree;
the packet must never present a copyable shape that the current validator will
reject. Contract hash, completed-prefix evidence, route identity, and owner
bindings remain runtime-owned facts. PM supplies the semantic audit and the
complete route, not a second machine ledger.

### 11. Cover every real gap without manufacturing gaps

The renewal audit must cover the exact current hard-obligation projection,
including non-route hygiene, open-resource, residual-risk, and legacy-evidence
gaps when they are unresolved. Every real gap needs at least one submitted
owner, and every owner must belong to the submitted route. Nested implementation
nodes do not each need a fabricated user-goal gap; a top-level milestone must
be traceable to one or more real gaps. Existing obligation ids and projections
remain the authority; no second gap ledger is introduced.

### 12. Reuse the current route-mutation lifecycle

Changed-suffix renewal uses the existing route-mutation lifecycle for node
materialization, packet quarantine, evidence invalidation, route versioning,
and repair-blocker retirement. A new renewal-specific mutation helper may bind
the milestone decision, but it must delegate shared lifecycle effects to the
current primitive so an old open repair blocker cannot survive as a false
terminal blocker.

### 13. Formal review requires formal evidence access

Milestone summaries and evidence ids are navigation only. The PM renewal
packet receives the minimum current authorized result reads needed to inspect
completed milestone evidence and current deviations, and submission requires
the corresponding read receipts. No summary may substitute for a sealed result
body, and no broad unrestricted evidence channel is added.

### 14. Route topology remains mechanical, route quality remains reviewed

`parent_node_id == ""` remains the only runtime definition of a global renewal
boundary. Initial-route and renewal review additionally challenge whether each
top-level node is an independently acceptable phase outcome, whether one
parent swallows the entire project, or whether the route is fragmented into
trivial gates. This is a Reviewer quality check, not a new level, score, or
runtime feature flag.

### 15. Budget the loop without adding a second control system

The direct loop has one audit/remaining-plan pair per top-level milestone and
keeps machine bindings in the runtime projection. The normal gate consists of
four AI submissions (PM audit, FlowGuard challenge, PM absorption, and
Reviewer challenge) plus two local system steps (mechanical validation and
atomic commit). `docs/flowpilot_milestone_renewal_budget.md` records full
packet/context growth, authorized evidence reads, retries, and stage/total
latency separately from minimal serialized result shape. These are review and
observability limits, not L0-L4 modes, scores, or alternate authorities.

### 16. Separate structural unit proof from live closure evidence

The existing TestMesh/MTA tier remains the owner of exact test evidence, and
the exact PPA maintenance unit stays in the all-tier supplement so the frozen
bundle is complete. Its contract-shape unit tests use an explicit,
repository-relative `ProofArtifactRef` marked `structural_shape_only` for the
contract-matrix paths; that proof is limited to the unit's own assertions and
does not stand in for a live matrix result. The closure runner remains the
sole owner of live PPA evidence and reads the current matrix and MTA results
after their producer stages complete. This keeps the existing tier structure,
avoids a producer/consumer cycle, and preserves fail-closed currentness.

## Risks / Trade-offs

- **More review work at major milestones** → The gate applies only to
  top-level nodes and reuses one existing challenge chain; nested execution
  remains local.
- **Plan equality may be sensitive to normalization details** → Compare one
  canonical current node representation and test omitted-default equivalence.
- **Changed suffix may contain partially active work** → Quarantine every
  affected unfinished packet and preserve its history; never silently reuse its
  evidence.
- **Terminal empty-plan overclaim** → Require zero current obligation gaps plus
  current FlowGuard, Reviewer, and system-validation evidence.
- **Existing recovery assumes ordinary PM disposition applies immediately** →
  Add exact staged-gate recovery profiles and negative tests for old automatic
  continuation.
- **Contract examples can drift from current route bindings** → Build the
  example from the same runtime owner projection and test a real multi-node
  packet shape through the validator.
- **Gap ownership can become formalism or omit non-route gaps** → Bind exact
  current obligation ids, require real-gap coverage, and do not require every
  nested helper node to invent a gap.
- **Renewal-specific route mutation can strand old blockers** → Delegate common
  retirement and quarantine to the existing route-mutation primitive and test
  an active blocker on the replaced suffix.
- **Repeated cumulative evidence transport can grow quadratically** → Give PM
  bounded reads for the current milestone delta and the immediately previous
  accepted milestone audit, while the runtime-owned accepted-prefix projection
  supplies exact historical bindings at commit.

## Migration Plan

1. Add the model and executable failure profiles before runtime changes.
2. Extend the current PM-disposition contract and review-window projection.
3. Stage top-level acceptance and implement equality-aware suffix renewal.
4. Add focused current-contract, review, recovery, route, and terminal tests.
5. Refresh FlowGuard authority, topology, SkillGuard contracts, and the clean
   installed projection only after source behavior is frozen and validated.
6. Rollback, if required before release, removes the new source changes and
   restores the prior installed projection; no persisted run is translated or
   accepted through a compatibility path.
7. Close the post-implementation correctness findings, refresh current model
   authority and TestMesh/MTA/PPA/BCL evidence, then run one real longitudinal
   multi-milestone rehearsal before enabling the final consumer projection.
8. After one frozen final validation and consumer-install currentness pass,
   update the immutable release version and notes, commit only owned integrated
   paths, push the current branch and `main`, create a new annotated tag and
   GitHub Release, and verify all remote identities without rerunning producers.
