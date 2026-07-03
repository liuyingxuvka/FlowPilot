## Context

`progress_fraction` is a public runtime projection, not a completion gate. The original capability said every currently expanded work node counts equally. A later repair narrowed the calculation to active route `node_order` plus an initial planning node. That removed packet fallback, but it also made progress vulnerable to route-list overwrite: a run with seventeen earlier nodes and one supplemental materialized node can display `1/2` even though the older nodes still exist and have no formal removal disposition.

FlowGuard route models separate two concepts:

- node lifecycle: pending, running, awaiting PM disposition, accepted, waived, blocked, stopped, superseded;
- route structure changes: planning rewrite, normal node addition, parallel node addition, child-node expansion, node-internal replan, repair node, return-to-original repair, supersede-original replacement, branch-then-continue, sibling-branch replacement, and full route rewrite.

The progress projection must respect both. It may shrink when a formal route/node disposition removes obligations, but it must not shrink merely because a list projection was overwritten.

## Goals / Non-Goals

**Goals:**

- Count the no-node case as `0/1` from the display-only initial planning node.
- Count all current-run expanded work nodes that still have no formal removal disposition.
- Count ended nodes using existing terminal-effective statuses: accepted, waived, blocked, stopped.
- Treat parent, module, leaf, and repair nodes equally.
- Preserve active-subject projection and sealed-body boundaries.
- Keep denominator reduction possible only when route/node lifecycle evidence, such as `superseded`, makes the old node non-effective.

**Non-Goals:**

- No percent progress.
- No Controller-side counting.
- No new workflow, role, packet family, or ledger table.
- No sealed body inspection.
- No compatibility layer for old progress outputs.

## Decisions

### Decision: Use route_nodes as the expanded-node source

The runtime-owned `route_nodes` table is the stable record of materialized work nodes. It preserves parent/module/leaf/repair nodes even when `node_order` is rewritten. Counting from `route_nodes` matches the original "expanded work nodes" contract better than active `node_order`.

Alternative considered: keep active `node_order` and patch only the duplicate materialization case. Rejected because it would still miss branch-then-continue, sibling replacement, and node-entry child expansion cases where effective work exists outside a short current frontier list.

### Decision: Let formal node status drive numerator and denominator removal

Statuses already encode lifecycle disposition. `accepted`, `waived`, `blocked`, and `stopped` are ended for progress display. `pending`, `running`, and `awaiting_pm_disposition` are not ended. `superseded` is stronger than ended: it is formal evidence that the old node is no longer an effective obligation, so it can leave the denominator rather than remaining as a pending or completed unit. This preserves the distinction between "ended for progress", "removed by formal supersession", and "authorized completion".

Alternative considered: count only accepted/waived nodes as ended. Rejected because the existing public fraction intentionally records stopped/blocked/superseded nodes as no longer active progress obligations without turning them into completion evidence.

### Decision: Do not remove a node from denominator without formal evidence

If a later materialization overwrites `node_order` but old nodes remain in `route_nodes`, those nodes remain counted unless a formal route mutation or node lifecycle disposition proves they are no longer effective. A shorter `node_order` alone is display/current-frontier information, not removal authority.

Alternative considered: infer removal from absence in active `node_order`. Rejected because the observed failure was exactly an unintended absence after supplemental materialization.

### Decision: Keep initial planning node as display-only

Before any route node exists, progress remains `0/1`. Once route nodes exist, the initial planning node contributes one ended unit so the public denominator grows from the same vocabulary rather than switching to packet counts.

## Risks / Trade-offs

- Denominator may include parent and child nodes, making ratios larger than a shallow route sign. Mitigation: this is already the original equal-node contract; route signs can remain shallow while progress is expanded-node progress.
- Historical nodes that should have been formally removed but were left without disposition will remain counted. Mitigation: this is desirable because it exposes missing route mutation/disposition evidence instead of silently hiding obligations.
- Route replacement scenarios need tests to ensure formally superseded nodes leave the denominator, not remain pending. Mitigation: add focused unit cases for supplemental materialization, formal supersession, branch-then-continue, and active-route node_order shrink.
