# Design

## Context

Existing FlowPilot rules already require current-contract repair, parent repair
inheritance, and same-family break-glass. The missing piece is mechanical
resolution of a parent's child references after a child node has been replaced.

In plain terms: if `longform-intake-ledger` is replaced by
`longform-intake-ledger-repair-v2`, the parent must see the repair node as the
current child. If the replacement chain cannot be resolved, parent replay must
block. It must not silently keep using the old node.

## Single Runtime Path

Runtime owns a single strict resolver:

1. Start from each declared child node id.
2. Follow `superseded_by` through route-node replacements.
3. Stop only on a non-superseded active terminal node.
4. Reject missing nodes, cycles, terminal superseded nodes, and non-route
   replacement targets.
5. Return both active child ids and lineage rows showing original -> active.

There is no compatibility mode and no historical fallback. Old ids may appear
only as the `original_child_node_id` in lineage metadata.

## Parent Repair And Replay

When a route node is replaced for `repair_current_scope`, its copied child list
is resolved through the active child lineage resolver before the replacement is
written. Parent backward replay uses the same resolver when creating the review
packet, then fetches accepted result ids from the resolved active child ids.

If any active child lacks accepted result evidence where parent replay requires
it, parent replay blocks with a current mechanical error instead of opening
another same-shape ordinary repair loop.

## Break-Glass Counting

The repair-loop counter must not drop same-root blockers merely because a
repair outcome marked an older blocker `cleared_by_outcome_id`. A blocker stays
countable when it has a `root_cause_loop_key` and no current
`lineage_verified_closed_by` evidence.

Only a current verifier pass that proves active child lineage, active accepted
child results, and absence of superseded child references closes that root
cause for counting.

## Prompt And Contract Boundary

Cards and contracts should tighten existing rules, not add a parallel workflow:

- PM may choose ordinary repair only while runtime says threshold is not
  exceeded.
- Reviewer parent backward replay rejects superseded child ids and requires
  active child lineage.
- FlowGuard checks route/replay execution effects, not just PM text or result
  shape.
- Controller treats unresolved cleared same-root blockers as still countable
  for break-glass.

## Verification Boundary

The core test matrix must cover the Cartesian product of child lineage state,
repair path, blocker history, attempt count, reviewer behavior, and FlowGuard
evidence binding. This can be implemented as generated focused unit/model cases
rather than a huge end-to-end run for every cell.
