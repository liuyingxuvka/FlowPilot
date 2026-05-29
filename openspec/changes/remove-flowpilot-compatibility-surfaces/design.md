## Context

The current repository intentionally preserved several classes of compatibility
behavior while FlowPilot moved from older protocol shapes to the current
FlowGuard-backed control plane. The preserved surfaces now conflict with the
new product direction: a FlowPilot invocation should use the current workflow
directly, and old fields, aliases, prompts, migrations, and compatibility
facades should no longer be accepted as active runtime behavior.

The compatibility inventory spans:

- startup command aliases and legacy startup payload reconciliation;
- legacy Router, Product Officer, Process Officer, and Reviewer event aliases;
- runtime schema aliases, deprecated transaction names, and compatibility
  report artifacts;
- old layout and material packet migration helpers;
- prompt/card instructions that still describe compatibility-only paths;
- install checks and test tiers that require historical equivalence evidence;
- public facade exports that exist only to preserve old module boundaries.

## Goals / Non-Goals

**Goals:**

- Make the current FlowPilot workflow the only active runtime contract.
- Reject old runtime inputs explicitly instead of migrating or canonicalizing
  them into current state.
- Remove active prompt, card, schema, install, and test guidance that teaches
  old compatibility routes.
- Preserve safety invariants by renaming or reframing prior/superseded authority
  state instead of deleting quarantine protection.
- Use FlowGuard model boundaries, StructureMesh, and Model-Test Alignment to
  keep the removal staged and evidence-backed.
- Sync the repository-owned installed FlowPilot skill and commit the final local
  git result after validation.

**Non-Goals:**

- No tag, push, GitHub release, deployment, or binary packaging.
- No destructive deletion of historical run data under `.flowpilot/runs`.
- No weakening of current quarantine, stale-evidence, active-writer, or
  authority-supersession safety checks.
- No broad UI or product redesign beyond removing compatibility affordances.

## Decisions

### Decision: Old runtime inputs become unsupported, not migrated

Old command aliases, old event aliases, legacy startup payloads, legacy repair
transactions, and old layout artifacts will fail with explicit unsupported or
unknown-input outcomes. This is stricter than preserving silent migration and
matches the new FlowPilot-only direction.

Alternative considered: keep migration helpers but hide them from prompts. That
would leave old behavior reachable and would keep tests/install gates coupled to
compatibility semantics.

### Decision: Safety quarantine semantics are preserved under current names

Fields that only express prior/superseded authority quarantine are not treated
as old compatibility contracts. Where naming is misleading, they are renamed or
documented as current safety state.

Alternative considered: delete every `old_*` field. That would remove the
record that previous agents, evidence, or closures cannot regain authority.

### Decision: Prompt cleanup precedes runtime facade contraction

Prompts and runtime contracts will be cleaned before the larger public facade
contraction. This prevents roles from emitting old shapes while code structure
is being reduced.

Alternative considered: remove facades first. That risks breaking validation
and installed skill sync before the behavior contract is clear.

### Decision: Public facade contraction is StructureMesh-governed

Compatibility-only public exports will be removed only after owner modules and
tests no longer import them. The target public API is a current owner API, not a
compatibility-preserving export table.

Alternative considered: delete facade modules in one pass. The existing model
inventory counted more than one hundred compatibility facade surfaces, so a
single ungoverned deletion would make failures difficult to triage.

### Decision: Historical equivalence becomes archived evidence only

Legacy-to-router, barrier-equivalence, legacy-prompt, and legacy-full checks are
not current release gates after this change. New validation proves new-only
runtime behavior and rejection of old inputs.

Alternative considered: keep historical checks as mandatory install gates. That
would continue making old compatibility a required system surface.

## Risks / Trade-offs

- Breaking old automations -> Mitigate by documenting `start` as the only fresh
  invocation path and making old aliases fail clearly.
- Hidden imports through facade modules -> Mitigate with repository-wide import
  scans before removing each facade and with StructureMesh parity checks.
- False confidence from scoped tests -> Mitigate by recording model regression
  logs as proof artifacts and reporting any background check that is still
  running or failed.
- Safety regression from deleting prior-authority fields -> Mitigate by
  preserving quarantine invariants while changing names or documentation.
- Installed skill drift -> Mitigate by serializing install sync, install check,
  and freshness audit after source validation, not in parallel.

## Migration Plan

1. Add OpenSpec contracts and FlowGuard new-only runtime model.
2. Clean startup commands and prompt/card surfaces so no role is instructed to
   emit old inputs.
3. Remove runtime schema aliases, event aliases, and transaction aliases.
4. Remove legacy migration/recovery helpers and old layout fallback behavior.
5. Remove legacy equivalence docs from install requirements and retire
   legacy-full test tiers.
6. Contract compatibility facade exports through StructureMesh.
7. Run focused tests and background full model regressions.
8. Sync the repository-owned installed FlowPilot skill.
9. Run install freshness audit and commit the final local result.

Rollback is a git revert of the local commit. Runtime data under `.flowpilot` is
not destructively migrated by this change.

## Open Questions

- Whether historical compatibility documentation should remain in an archive
  folder or be deleted entirely from the repository can be decided during the
  docs cleanup phase. The runtime/install contract does not depend on either
  choice.
