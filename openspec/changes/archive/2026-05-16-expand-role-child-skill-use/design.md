## Context

FlowPilot already has a child-skill pipeline: material scan inventories local skills as candidate-only resources, PM selects skills, PM extracts skill standards, worker packets inherit bindings, workers return `Child Skill Use Evidence`, and reviewers check direct use. The gap is scope clarity. Current prompts can imply child skills are mainly selected for delivered product work and mainly executed by workers.

The intended model is broader: a selected child skill can support planning, specification, route design, validation, review, modeling, or execution. PM, reviewer, process FlowGuard officer, product FlowGuard officer, worker A, and worker B can each be valid skill users when the route assigns that role a skill-use duty.

## Goals / Non-Goals

**Goals:**

- Make PM evaluate process-support skills in addition to deliverable-support skills.
- Represent role-scoped skill-use bindings in existing child-skill artifacts.
- Require evidence when a selected skill materially affects a role's formal output or approval.
- Let reviewer checks cover PM/officer/reviewer skill use where assigned, not only worker use.
- Preserve current raw-inventory and PM-selection authority boundaries.

**Non-Goals:**

- No automatic invocation of locally available skills.
- No new package manager or broad skill taxonomy.
- No weakening of existing worker `Child Skill Use Evidence`.
- No Controller authority to approve, use, or self-attest selected skills.
- No remote release, push, or publication.

## Decisions

### Decision 1: Extend the existing child-skill contract instead of creating a parallel process

Add role-skill bindings to the existing selection, manifest, node plan, packet, and result surfaces. This keeps the feature under the current PM-selection and reviewer-check model rather than inventing a second "process skill" pipeline.

Alternative considered: create a new top-level "process skills" manifest. That would make process skills visible, but it would duplicate child-skill gate logic and create more route-state surfaces to reconcile.

### Decision 2: Model the skill user explicitly

Each meaningful selected skill-use must name `used_by_role`, `use_context`, `why_needed`, source paths, evidence requirements, and reviewer/check authority. This lets a PM use a planning skill, a reviewer use an audit skill, or an officer use a modeling-support skill without pretending the worker used it.

Alternative considered: keep role use implicit in prose. That preserves flexibility but makes reviewer verification unreliable.

### Decision 3: Evidence is role-general, worker evidence remains worker-specific

Keep the existing `Child Skill Use Evidence` worker table. Add a `Role Skill Use Evidence` concept for PM, reviewer, officer, and any worker skill use that affects planning, approval, modeling, validation, or review outside the existing worker execution path.

Alternative considered: rename all child-skill evidence to one generic table. That would risk breaking existing worker packet/result checks.

### Decision 4: Use prompt/template/test coverage first, then model runtime enforcement narrowly

This change can be safely introduced by strengthening cards and templates, then adding tests and FlowGuard hazards for missing process-support consideration and missing role-skill evidence. Router changes should remain minimal unless validation shows a mechanical field needs preservation.

Alternative considered: immediately make the router enforce every new field. That is heavier and risks colliding with active router-control changes in the current worktree.

## Risks / Trade-offs

- Extra process complexity -> Mitigation: PM must still apply minimum sufficient complexity; rejected/deferred skills remain valid decisions with reasons.
- Self-attested PM skill use -> Mitigation: role-skill bindings name evidence and reviewer/check authority; PM cannot pass its own hard gate from prose alone.
- Reviewer overreach -> Mitigation: reviewer checks assigned evidence and hard gate obligations, while nonessential improvements remain PM decision-support.
- Existing worker evidence regressions -> Mitigation: preserve `Child Skill Use Evidence` and add role-general evidence alongside it.
- Current dirty worktree collisions -> Mitigation: avoid router-heavy changes and keep edits scoped to previously clean prompt/template/test/model files where possible.

## Migration Plan

1. Add OpenSpec requirement and implementation tasks.
2. Update prompt cards and templates to include deliverable-support and process-support child skills plus role-skill bindings.
3. Add planning/output contract tests for required wording and evidence sections.
4. Add focused FlowGuard coverage or strengthen capability/meta model hazards for process-support skills and role-skill evidence.
5. Run focused tests, then the required FlowPilot checks.
6. Sync the repo-owned installed FlowPilot skill and audit local install freshness.
7. Stage and commit only the files belonging to this change.
