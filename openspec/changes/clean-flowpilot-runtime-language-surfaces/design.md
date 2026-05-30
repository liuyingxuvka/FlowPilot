## Context

FlowPilot has already moved to `flowpilot_new.py`, native startup intake, a
runtime packet/control plane, and host-supported role bindings. The remaining
problem is not only visible copy: current authoritative surfaces still include
old terms and structures in prompts, runtime templates, CLI flags, state/model
names, checks, and result baselines. Prior cleanups intentionally left some
schema and model names stable; the new product direction is to remove those
unsupported historical surfaces rather than explain or preserve them.

The repository has a mature FlowGuard/OpenSpec/test topology. Changes that
touch prompt/card boundaries, model terms, test registries, install readiness,
or local install sync must update the owning checks and regenerate current
evidence before completion.

## Goals / Non-Goals

**Goals:**

- Make the active FlowPilot runtime describe role help only as
  runtime-requested responsibilities and host-supported role bindings.
- Remove current-authority uses of fixed crew, runtime-role, sidecar role,
  role-binding, unsupported historical alias, unsupported historical route, and FlowPilot runtime naming from
  prompts, templates, state/model terms, checks, and installed surfaces.
- Keep safety rejections for unsupported historical inputs without teaching
  those inputs as supported repair paths.
- Regenerate affected model/test evidence and sync the local installed
  FlowPilot copy.

**Non-Goals:**

- Do not preserve old field names as public unsupported historical aliases.
- Do not change the user's frozen acceptance standards or lower validation
  requirements.
- Do not push to GitHub or publish a release unless separately requested.
- Do not rewrite purely archived historical snapshots unless an active check or
  current install surface reads them as current authority.

## Decisions

1. Treat role-binding language as the single current vocabulary.
   - Chosen: `role_binding`, `role_binding_ledger`,
     `role_binding_memory`, `role_binding_recovery`, and
     `runtime_role_assistance`.
   - Rejected: "not six agents" or "not runtime role assistance" phrasing, because
     it keeps the old concept salient.

2. Migrate authoritative templates before model baselines.
   - Templates are the mold for future `.flowpilot` state. If they remain old,
     later model and test changes will regenerate old concepts.
   - Result baselines come after source/model changes and are not standalone
     evidence.

3. Rename active model concepts, not only prompt text.
   - Fixed `REQUIRED_ROLE_BINDING_COUNT = 6`, `runtime_role_bindings_*`, and `required_role_binding_*` checks must
     become requested-role-binding coverage checks where they are current model
     obligations.
   - The migration can keep scenario intent while changing labels and field
     names.

4. Rephrase safety guards as unsupported-input guards.
   - Runtime may still reject old channels, stale route state, or unsupported
     payloads.
   - User-facing and role-facing messages should not present unsupported channels
     as available repair workflows.

5. Validate in layers.
   - Focused prompt/template scans run first.
   - Unit/model checks that cover changed surfaces run next.
   - Heavy meta/capability regressions run through the repository background
     log contract when the broad model surface changed.
   - Install sync and audit happen after source validation so the installed copy
     matches a validated repository state.

## Risks / Trade-offs

- Broad rename risk -> Use mechanical scans, focused tests, and FlowGuard
  result regeneration instead of manual one-off edits.
- Hidden public API risk -> Keep current runtime behavior where users depend on
  it, but rename current-authority fields and update tests together.
- Historical evidence churn -> Do not edit archived snapshots unless active
  checks treat them as current output.
- Dirty worktree risk -> Stage and commit only files touched for this change;
  preserve pre-existing unrelated modifications.
- Long-check runtime risk -> Run heavyweight checks in the background log
  contract and inspect exit/meta artifacts before claiming completion.

## Migration Plan

1. Update OpenSpec requirements and tasks for the clean runtime-language pass.
2. Clean active skill entrypoint and runtime kit prompt/card wording.
3. Clean `templates/flowpilot` and install checks for role-binding vocabulary.
4. Rename current-authority runtime/model/test terms and update generated
   baselines.
5. Run focused prompt/install/model checks, then background meta/capability
   regressions if the parent models changed.
6. Rebuild/check project topology, sync the local installed skill, audit the
   install, and commit only the validated change files.
