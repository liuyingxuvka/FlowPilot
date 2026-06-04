## Design

### Contract Boundary

This change keeps the current FlowPilot runtime shape:

- No new packet kind.
- No old-router fallback.
- No `route_nodes` route-plan alias.
- No compatibility parser or missing-field default.
- No per-scenario candidate ledgers.

Runtime/router owns mechanical validity. FlowGuard and Reviewer own substantive
review of the real submitted artifact and evidence.

### Staged Effect Shape

A staged effect is a small record attached to an existing `result` or
`pm_decision_gate`. It represents the runtime side effect that may be committed
only after the gate sequence accepts the source result.

Minimum fields:

- `effect_kind`
- `source_packet_id`
- `source_result_id`
- `status`
- `target_node_id`, `blocker_id`, or `target_route_version` only when needed
- `created_at`
- `committed_at` only after commit

The staged effect must not copy sealed bodies, node-context payloads, route-plan
payloads, or reviewer/FlowGuard report bodies. Runtime reads the original
accepted result body only at the commit point.

### Node Acceptance Plan Flow

When PM submits a node acceptance plan result:

1. Runtime validates the current result mechanically.
2. Runtime records `staged_effect.effect_kind =
   "commit_node_acceptance_plan"` on the result.
3. Runtime keeps the route node without formal `node_acceptance_plan_id` or
   `node_context_package_id`.
4. FlowGuard and Reviewer inspect the real PM result and any cited evidence.
5. Runtime commits the staged effect during system closure by parsing the
   original result body and binding accepted node plan/context ids.

The FlowGuard packet for this review must cite the source result and staged
effect instead of requiring the accepted node fields before commit.

### Route Mutation Gate Flow

When PM records a high-risk `mutate_route` repair or disposition:

1. Runtime records the PM decision.
2. Runtime stages a PM decision gate with `staged_effect.effect_kind =
   "commit_route_mutation"`.
3. Runtime does not change `active_route_version` while the gate is pending.
4. FlowGuard and Reviewer inspect the decision, blocker context, route node, and
   staged effect as the real current artifact/effect to review.
5. Runtime commits the staged effect after gate closure and then applies the
   route mutation exactly once.

### Reissue Flow

`sender_reissue` and `collect_more_evidence` preserve the original packet kind
and route scope unless the original packet kind is unsupported. Repairing a
`pm_repair_decision` produces a new `pm_repair_decision` packet, not a generic
task packet.

### Stopped Blocker Flow

`stop_for_user` keeps the semantic blocker stopped until an explicit stopped
blocker command records the user/PM decision. Plain `resume` remains lifecycle
rehydration only and does not clear semantic blockers.

### FlowGuard Toolchain Failure

If real FlowGuard API or model execution fails, runtime records a toolchain
blocker and does not generate a manual fallback evaluation. This keeps
FlowGuard evidence honest and current-toolchain owned.

### Validation Strategy

Validation must include:

- Unit tests for strict mechanical submission and reissue type preservation.
- Runtime route tests for staged node plan and route mutation commit timing.
- CLI tests for stopped blocker resolution.
- Card instruction tests for runtime/mechanical vs FlowGuard/Reviewer
  substantive review boundaries.
- Focused FlowGuard models and known-bad scenarios for future-state assumptions,
  premature route mutation, reissue type loss, stopped blocker dead-end, and
  FlowGuard fallback.
- Serialized install sync/audit/check after repository validation.
