## Context

FlowPilot already has the right high-level repair direction: no same-node
repair-in-place, one current PM repair menu, append-only history, replacement
route scopes, fresh packets, and parent backward replay for module nodes. The
current incident shows a narrower gap inside that existing path. Parent-scope
repair can replace a parent and descendants with a new parent repair node, but
the replacement parent can be empty, while PM prose and later node acceptance
plans can imply child work that is not present in route-node fields.

The user preference is a single current-contract path with no compatibility
surface, no package-outside side channel, no field guessing, and no patch stack.
The repair therefore extends existing `repair_parent_scope` mechanics instead
of adding a new PM decision, a new repair ledger, or a per-child disposition
workflow.

## Goals / Non-Goals

**Goals:**

- Keep the existing five PM repair decisions. `repair_parent_scope` remains the
  parent/module repair entry.
- Make replacement parent repair nodes nonempty by construction.
- Preserve old child nodes and accepted child results as inherited read-only
  history/context.
- Make new PM-declared repair child specs the only active child subtree under
  the replacement parent.
- Reject prose-only child routing and empty parent/module repair nodes before
  parent backward replay can loop.
- Make FlowGuard evidence acceptance subject-bound: the result must inspect
  the actual parent repair contract, route node, child ids, acceptance plan, and
  replay inputs.
- Make break-glass count repeated repair chains by lineage root so no-in-place
  repair does not hide repeated same-problem attempts.
- Cover the observed June 14 empty-parent loop and same-class bad cases with
  model, runtime, fake AI, and install-sync evidence.

**Non-Goals:**

- Do not restore same-node repair-in-place.
- Do not add a sixth PM repair decision.
- Do not add compatibility aliases or translate old field names.
- Do not introduce a full child disposition table for every old child.
- Do not let inherited child nodes regain current routing authority.
- Do not treat fake AI rehearsal as proof of every live AI semantic quality
  failure.
- Do not continue or complete the unrelated active `.flowpilot/current.json`
  run in this maintenance task.

## Decisions

### Parent repair creates a replacement parent plus active repair children

When PM chooses `repair_parent_scope`, Runtime still supersedes the nearest
explicit parent and descendants as current authority. It then creates a
replacement parent repair node. That replacement parent must have at least one
active repair child derived from PM repair child specs.

The replacement parent route shape is:

```json
{
  "node_id": "package-repair-v2",
  "node_kind": "module",
  "child_node_ids": ["package-repair-v2-child-001"],
  "inherited_child_node_ids": ["pyproject", "schemas", "cli"],
  "inherited_accepted_result_ids": ["result-001", "result-002"]
}
```

`child_node_ids` means current executable repair children. `inherited_*` means
historical context only.

Alternative rejected: blindly copy old child ids into `child_node_ids`. That
would make superseded children current again and break the current-authority
rule.

Alternative rejected: require PM to disposition every old child. That is more
complex than necessary for this failure class and creates a new planning
surface where the runtime can derive the old-child inheritance automatically.

### PM supplies only the new repair child specs

PM output for parent repair must include a structured parent repair contract.
Runtime derives inherited old children and accepted result refs from the
current ledger; PM does not hand-copy them. PM only supplies one or more new
repair child specs with purpose and required evidence.

The minimum contract shape is:

```json
{
  "repair_parent_scope_contract": {
    "source_parent_node_id": "package",
    "inherit_existing_children": true,
    "repair_child_specs": [
      {
        "node_id": "package-repair-v2-child-001",
        "purpose": "repair parent replay input wiring",
        "required_evidence": [
          "current repair child result",
          "parent replay authorization proof"
        ]
      }
    ]
  }
}
```

Alternative rejected: let PM describe children in prose. Prose cannot be used
by Runtime, Reviewer, or FlowGuard as current routing authority.

### Runtime owns mechanical rejection

Runtime rejects:

- parent repair contracts with missing or empty `repair_child_specs`;
- replacement parent/module repair nodes with empty active `child_node_ids`;
- node acceptance plans that claim child routing while the route node has no
  active child ids;
- parent backward replay attempts that have inherited evidence but no current
  repair child result;
- FlowGuard pass envelopes whose evidence artifacts contain blocker findings,
  `missing_code_contract`, missing obligations, stale evidence, or progress-only
  status.

Reviewer and FlowGuard cards still inspect semantics, but Runtime must not wait
for them to catch mechanical absence of child nodes.

### FlowGuard reports must be evidence-consistent and subject-bound

FlowGuard work orders for this path must name the exact subject artifacts:

- PM repair decision and parent repair contract;
- replacement route mutation/node record;
- inherited child/result references;
- active repair child ids;
- PM node acceptance plan;
- parent backward replay inputs and outputs.

A FlowGuard report cannot pass this gate by checking only top-level
`passed:true`, result shape, current-contract fields, or source existence. If
any referenced evidence artifact reports a hard blocker or missing contract,
Runtime must treat the FlowGuard gate as failed.

### Break-glass counts repair lineage, not only physical node id

The existing no-in-place repair policy deliberately creates new physical node
ids. Break-glass therefore must normalize the repair lineage root and include
superseded repair-chain evidence in the threshold calculation when the same
problem identity repeats through the replacement chain.

This does not make similar problems across unrelated nodes global break-glass.
The count stays scoped to the same lineage root plus blocker class, gate kind,
and required recheck role.

## Risks / Trade-offs

- Old accepted child results may be stale after a broad parent repair -> the
  replacement parent treats them as context only. Current completion still
  requires new repair child results and parent replay.
- Some PM outputs that previously passed by prose will now block earlier ->
  this is intended because they could not be executed deterministically.
- Additional route-node fields increase schema surface -> field count is kept
  minimal and one-owner: Runtime writes inherited fields, PM writes repair
  child specs, route node `child_node_ids` remains the active child authority.
- Break-glass may trigger sooner for a repair chain than before -> the scope is
  constrained to same lineage and same problem identity to avoid global
  over-triggering.

## Migration Plan

1. Add OpenSpec requirements and tasks for the parent repair inheritance
   contract.
2. Update the focused FlowGuard repair model first so the old empty-parent and
   contradictory FlowGuard pass cases fail.
3. Add runtime validation and route materialization support for inherited
   history plus active repair children.
4. Update PM, Reviewer, and FlowGuard cards to require structured parent repair
   contracts and block prose-only child routing.
5. Add unit tests and fake AI rehearsals for bad and good parent repair cases.
6. Rerun focused FlowGuard checks, affected router/runtime tests, card coverage,
   model-test alignment, topology build/check, install check, and local install
   sync audit.
7. Sync the repository-owned FlowPilot skill into the local installed skill.
8. Commit the scoped FlowPilot repository changes after validation.

Rollback is ordinary git revert of this change. There is no runtime migration
for old in-flight PM packets because the project policy forbids compatibility
translation; malformed or old-shape packets must be rejected and reissued under
the current contract.
