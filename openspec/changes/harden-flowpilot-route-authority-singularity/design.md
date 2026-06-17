## Context

FlowPilot currently has a route action policy registry, legal-next-action model, control transaction registry, and router tests for no-legal-next-action blockers. Those surfaces are necessary but not sufficient for route-authority confidence because they do not jointly prove that each current state has one owner, role submissions are rejected when outside the current legal set, wrong-path feedback is actionable, and old aliases/fallback shapes cannot advance the route.

The repository contract is new-only. This change must reject unsupported old shapes instead of translating them into current actions. The active live FlowPilot run is not the target of this work; this change only repairs the FlowPilot skill/runtime/model/test surfaces.

## Goals / Non-Goals

**Goals:**
- Make route authority explicit at the router boundary: current owner, current state family, legal next actions, forbidden actions, route/frontier snapshot, and repair command.
- Detect and reject wrong-path role submissions before they can become route, frontier, packet, blocker, or status writes.
- Ensure wrong-path rejection feedback is structured enough that the next AI packet can change behavior instead of repeating the same invalid packet.
- Add FlowGuard, synthetic fake-AI, router runtime, ModelMesh, and model-test alignment coverage for owner conflicts, wrong role actions, stale legal snapshots, old aliases, and fallback/prose attempts.
- Keep local install and topology evidence current after implementation.

**Non-Goals:**
- Do not continue, repair, or complete the existing live `.flowpilot` run.
- Do not add compatibility, alias translation, prose guessing, legacy fallback, or dual-authority paths.
- Do not change WorldGuard, SkillGuard, or any non-FlowPilot system.
- Do not publish, push, release, or archive unless explicitly requested after local completion.

## Decisions

### Authority Snapshot At Router Boundary

Add a compact route-authority snapshot helper rather than scattering new fields across each provider. The snapshot is derived from current run state, route/frontier/ledger facts, `route_action_policy_registry.json`, event capability rows, and control transaction rows.

The snapshot shape is:

```json
{
  "schema_version": "flowpilot.route_authority_snapshot.v1",
  "current_owner": "project_manager",
  "current_state_family": "parent_backward_replay_passed",
  "legal_next_actions": ["record_parent_segment_decision"],
  "forbidden_actions": ["complete_parent_node", "mutate_route", "terminal_closure"],
  "required_repair_command": "submit_pm_parent_segment_decision",
  "route_version": 3,
  "frontier_version": 8
}
```

Alternative considered: add ad hoc fields to each card and blocker. Rejected because the same authority data would drift across providers and tests.

### Reject Rather Than Translate Unsupported Paths

Unsupported action ids, legacy aliases, wrapper/prose shapes, and role-overreach events will produce structured wrong-path blockers or hard router errors. They will not be normalized into current route actions.

Alternative considered: accept common old names and map them to current action ids. Rejected because it directly violates the repository's new-only rule and recreates fallback maintenance surfaces.

### Reuse Existing Legal-Action Policy, Extend Its Contract

`route_action_policy_registry.json` remains the policy source. This change extends how it is consumed and tested; it does not introduce a second route-action registry.

Alternative considered: create a new authority table. Rejected because it would duplicate policy ownership and create exactly the dual-authority surface this change is meant to remove.

### Evidence Through Multiple Layers

The new model is a focused child model. Parent confidence is updated through ModelMesh and model-test alignment instead of claiming that the child model alone proves the full runtime.

Evidence layers:
- FlowGuard route-authority singularity model.
- Router/runtime unit tests for concrete boundaries.
- Synthetic fake-AI matrix and trace replay for wrong-path/no-delta/corrected retry behavior.
- ModelMesh hazard rows so the parent cannot green-light when authority evidence is missing.
- Model-test alignment family rows binding obligations to tests.

## Risks / Trade-offs

- **Risk: snapshot fields drift from registry semantics.** Mitigation: derive fields from registry/helper output and add registry consistency tests.
- **Risk: wrong-path rejection blocks a path that used to proceed by accident.** Mitigation: this is intended; tests must prove the corrected current action proceeds.
- **Risk: broad router test suites become slow.** Mitigation: keep targeted unit tests in the main validation set and run broad/meta/capability regressions through background artifacts when needed.
- **Risk: peer-agent writes stale evidence while this work runs.** Mitigation: inspect git status before editing, keep diffs scoped, rerun affected validation after final edits, and never revert unrelated changes.
- **Risk: adding fields to prompt/card payloads becomes compatibility-like expansion.** Mitigation: only add current-contract fields with one owner and one repair command; old fields remain rejected.

## Migration Plan

1. Upgrade FlowGuard project record to match installed FlowGuard and audit the project record.
2. Add OpenSpec requirements for route-authority singularity and affected synthetic/alignment coverage.
3. Add the FlowGuard model and runner, then bind it to ModelMesh and model-test alignment.
4. Implement the route-authority snapshot/rejection helpers and route them into wrong-path/no-legal-action blockers and relevant card/payload contexts.
5. Add targeted router/runtime tests and fake-AI replay coverage.
6. Run OpenSpec, FlowGuard model checks, targeted unit tests, ModelMesh, model-test alignment, topology build/check, install sync, and install audit.
7. Record FlowGuard evidence and commit local git changes.

Rollback is normal git revert of this change before release. Runtime data migration is not required because the change rejects unsupported future inputs and updates generated test/model artifacts.

## Open Questions

- None blocking. If implementation reveals an existing provider that already owns a portion of the authority snapshot, the helper should reuse that provider rather than introduce a parallel owner.
