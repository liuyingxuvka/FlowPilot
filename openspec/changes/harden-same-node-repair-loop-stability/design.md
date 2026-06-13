## Context

FlowPilot already records semantic blockers with `route_node_id`, `blocker_class`, `gate_kind`, and `required_recheck_role`. It also has a repair-loop break-glass review and a current-effective blocker predicate. The observed problem is not missing infrastructure; it is that the hard loop gate needs a narrower ownership boundary and the current-status projection must stay clean while preserving historical evidence.

## Goals / Non-Goals

**Goals:**

- Trigger break-glass only when the same route node has more than five consecutive attempts for the same problem identity.
- Let Reviewers/FlowGuard Operators preserve the existing `blocker_class` for a repeated same-node problem without introducing new persistent state.
- Keep cross-node similar failures in the ordinary PM/reviewer repair path.
- Keep stale repair rows out of current status and final-preflight blockers without deleting ledger history.
- Make ledger read/write robust against transient partial reads during active writes.

**Non-Goals:**

- No semantic classifier for material/read/authorization themes.
- No cross-node same-problem global break-glass counter.
- No new packet kind, role, long-lived field family, compatibility alias, or old-protocol fallback.
- No Controller authority to approve project work, route mutation, or terminal closure from break-glass.

## Decisions

1. Same-node consecutive threshold remains runtime-owned.

   The runtime will compute repair-loop evidence from existing blocker metadata. A row counts only when it belongs to the same current route-node subject, same `blocker_class`, same `gate_kind`, and same `required_recheck_role`. The counted chain must remain consecutive for that same node/problem identity; a pass, current node transition, or different problem identity breaks the chain.

   Alternative rejected: a cross-node semantic family counter. It can confuse normal repeated AI mistakes across different nodes with a broken control lane.

2. Reviewers preserve problem identity; they do not decide break-glass.

   Cards will instruct Reviewers and FlowGuard Operators to reuse the same `blocker_class` when the same node repeats the same defect. The runtime still owns threshold evaluation.

   Alternative rejected: adding a new `problem_family_id` field. Existing blocker metadata is enough for this observed case.

3. Current status uses current-effective blockers; history remains append-only.

   Noncurrent repair rows stay in the ledger for audit and, when still part of the current same-node consecutive chain, loop analysis. Status and final-preflight surfaces must not present obsolete rows as current blockers.

4. Ledger persistence uses atomic replace plus bounded read retry.

   Runtime ledger writes should write a complete temporary document in the same directory and atomically replace the target. Reads that encounter empty or incomplete JSON retry briefly before surfacing a clear runtime error.

## Risks / Trade-offs

- A repeated issue renamed by a Reviewer will not accumulate. Mitigation: card guidance and tests require same-node same-problem reports to reuse `blocker_class`.
- A true control-plane issue spread across different nodes will not automatically break-glass. Mitigation: this is intentional; it avoids over-triggering and leaves ordinary PM/reviewer repair available.
- Retrying incomplete ledger reads can hide real corruption briefly. Mitigation: retry is bounded and final failure remains explicit.
