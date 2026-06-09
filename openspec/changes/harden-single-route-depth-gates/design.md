## Context

FlowPilot already has strict route-plan JSON, route nodes with parent/child
links, node acceptance plans, pre-work FlowGuard gates, worker packets,
Reviewer gates, parent backward replay, route display projection, and final
ledger closure. Prior changes restored recursive route execution and hardened
shallow-completion checks.

The remaining risk is narrower: PM prompt text can still encourage one
high-level route while runtime and tests only prove that a small route can move
through the packet chain. For complex work, a broad leaf can be worker-assigned
even though the worker would have to decide the decomposition. The user also
explicitly rejected a schema-heavy repair. This change must keep one true route
tree and avoid adding route-node fields unless existing fields and gates cannot
enforce the behavior.

## Goals / Non-Goals

**Goals:**

- Make the canonical route tree the only PM-authored route plan.
- Keep display artifacts as Router-derived projections, not PM-authored
  alternate plans.
- Use existing fields first: `node_kind`, `parent_node_id`,
  `child_node_ids`, `acceptance_criteria`, `required_outputs`,
  `validation_checks`, `high_standard_requirement_ids`,
  `skill_standard_obligation_ids`, and `node_context_package`.
- Block parent/module and child-bearing nodes from worker task dispatch.
- Strengthen PM, FlowGuard operator, and Reviewer cards so route-depth
  adequacy is checked without adding a large persistent schema.
- Add focused bad-case tests showing broad routes and parent worker dispatch
  fail.

**Non-Goals:**

- Do not restore the old FlowPilot router or old route-state authority.
- Do not add PM-authored `display_plan` as a second plan.
- Do not add broad `why_*`, requirement-trace, process-trace, or simulation
  trace fields to every route node.
- Do not add compatibility aliases for old route shapes.
- Do not make simple or explicitly planning-only tasks artificially deep.

## Decisions

1. **One PM route, derived display.**

   PM route planning should describe one canonical executable tree. Any chat,
   Cockpit, or host-visible route display should be derived from that tree and
   the execution frontier. This preserves the simplified runtime while avoiding
   split authority.

   Alternative considered: keep `full_route_tree` plus PM-authored
   `display_plan`. Rejected because the user explicitly wants a simplified
   single-flow runtime and because dual PM plan artifacts create maintenance
   and divergence risk.

2. **Use existing route fields before adding schema.**

   Route depth can be enforced by existing `node_kind` and child-link fields.
   The PM can put rationale and proof expectations in existing
   `acceptance_criteria`, `required_outputs`, and `validation_checks`; node
   entry can put readiness detail in `node_context_package`. This avoids a
   new field mesh for every route node.

   Alternative considered: require fields such as `why_this_node_exists`,
   `why_not_merged`, `why_not_split`, `covers_requirement_ids`, and
   `process_simulation_trace` on every route node. Rejected as likely
   over-repair unless tests prove existing fields cannot carry the guarantee.

3. **Runtime owns mechanical dispatch refusal.**

   Runtime should reject worker packet creation for any node whose existing
   route shape says it is a parent/module or has children. This is a small
   mechanical check with one owner and no new state.

   Alternative considered: let PM and Reviewer prompts alone prevent direct
   parent dispatch. Rejected because the state-machine failure is mechanical:
   a parent-shaped node should not be dispatchable even if a prompt is missed.

4. **FlowGuard operator simulates route viability in report content, not a new
   ledger.**

   The route-process card should explicitly require the operator to check
   effective ordered traversal, broad leaves, parent replay, child-skill
   projection, and terminal closure. The hard runtime field remains the
   existing `process_viability_verdict`.

   Alternative considered: add a persistent `process_simulation_trace` schema.
   Rejected because the current issue can be modeled and tested without adding
   another route artifact family.

5. **Tests decide whether one small nested field is needed.**

   If bad-case tests still cannot distinguish a worker-ready leaf from a broad
   leaf using existing fields and the node acceptance package, then add only
   `node_context_package.leaf_readiness_gate` as a local node-entry field. It
   should not be promoted to route-node top-level state unless a later
   blocker proves that route-level persistence is required.

## Risks / Trade-offs

- Prompt-only language may still be ignored -> Mitigation: add runtime
  parent/child dispatch refusal and focused tests.
- Existing fields may be too weak for leaf readiness -> Mitigation: reserve a
  single nested `node_context_package.leaf_readiness_gate` fallback after tests.
- Display wording may remain confusing because existing files mention
  `display_plan` -> Mitigation: change card language to derived projection
  while keeping current display artifact compatibility as a projection cache.
- Parallel AI edits may change nearby files -> Mitigation: inspect git status
  before edits, keep patches narrow, and never reset or revert peer changes.
- Validation can become stale after install sync -> Mitigation: run source
  checks before sync and install audit/check after sync.

## Migration Plan

1. Update OpenSpec specs and tasks for the conservative route-depth gate.
2. Update route/process/reviewer cards to use one canonical route and derived
   display language.
3. Add runtime dispatch checks using existing node fields.
4. Add or update tests for parent/module dispatch refusal, child-bearing leaf
   refusal, route display derivation, and fake route depth rehearsal.
5. Run targeted unit and FlowGuard model checks.
6. Rebuild/check project topology if model/test/card surfaces changed.
7. Sync repository-owned skill files to the installed local FlowPilot skill.
8. Run install audit/check and record FlowGuard adoption evidence.

Rollback strategy: revert this OpenSpec change's focused card/runtime/test
edits only. Do not restore old route compatibility or old PM dual-plan
behavior.

## Open Questions

- Whether `node_context_package.leaf_readiness_gate` is necessary after the
  first test pass. The default answer is no unless a bad-case rehearsal remains
  green incorrectly.
