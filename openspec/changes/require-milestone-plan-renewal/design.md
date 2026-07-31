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
- No release, tag, or publication work in this change.

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
    "contract_hash": "<current frozen final-goal contract hash>",
    "completed": [
      {
        "node_id": "<accepted top-level node id>",
        "outcome": "Current milestone outcome",
        "evidence_refs": ["current-evidence-id", "current-review-id"]
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

The completed audit is cumulative for the active top-level prefix. Each row is
bound to one current top-level `node_id` and its complete runtime-issued
evidence set; the current frozen `contract_hash` is repeated in the audit so a
renewal cannot silently drift to another final goal. Every non-empty remaining
gap names one or more `owner_node_ids`, and the owner set must equal the
submitted remaining-plan node set. These are extensions of the existing PM
disposition contract, not a new ledger or packet family.

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
