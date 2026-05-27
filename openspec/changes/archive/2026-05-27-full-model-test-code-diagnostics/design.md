## Context

FlowPilot already has StructureMesh, TestMesh, ModelMesh, and a
model-test-alignment gate, but those gates were introduced in layers and do not
yet produce one repository-wide diagnostic view. The current alignment gate can
prove selected model obligations have source-level code and test evidence, but
it does not inventory every owner module, compatibility facade, script
entrypoint, or test tier before reporting what is missing, extra, stale, or too
broad.

The repository is also being edited by parallel agents. This change must keep
edits scoped to diagnostic artifacts unless a low-risk bug is directly exposed
by the diagnostic and can be fixed without conflicting with active owner-module
polish work.

## Goals / Non-Goals

**Goals:**

- Produce a full diagnostic inventory across owner modules, facades, script
  entrypoints, and test tiers.
- Bind each diagnostic surface to model obligations, code contracts, and test
  evidence where available.
- Emit explicit gap classifications instead of treating an uncovered surface as
  invisible.
- Add known-bad cases for common false-confidence hazards.
- Run focused and background validations with complete artifact evidence.

**Non-Goals:**

- No GitHub push, tag, or release publication.
- No broad router refactor as part of the diagnostic itself.
- No repo-wide formatter, dependency change, or generated churn outside the
  diagnostic evidence boundary.
- No claim that the first full diagnostic pass proves all runtime behavior; it
  proves coverage accounting and reports remaining gaps.

## Decisions

1. Extend the existing model-test-alignment runner rather than introducing a
   separate diagnostic framework.

   Rationale: the existing runner already imports FlowGuard alignment helpers,
   known-bad sanity checks, and result JSON generation. Extending it keeps the
   artifact spine familiar and avoids a second source of truth.

   Alternative considered: create a standalone inventory script. Rejected
   because it would risk drifting away from the model-test-alignment gate.

2. Treat diagnostic surfaces as inventory rows with coverage dimensions.

   Each row records surface kind, path, symbol or command, owning family,
   expected model obligation, expected code contract, expected test evidence,
   and diagnostic classifications. This supports both machine checks and a
   human gap table.

   Alternative considered: only add more `ModelObligation` rows. Rejected
   because missing extra-code and needs-split findings require seeing code that
   is not yet modeled.

3. Keep source-contract checks conservative.

   The checker should use AST-supported facts for symbol existence and test
   assertions, and plain repository inventory for broad module/script/tier
   accounting. It should not infer deep semantic correctness from naming alone.

   Alternative considered: require every function to have a precise external
   contract immediately. Rejected because the current repository has many
   compatibility facades and generated-like runtime helpers; a forced full
   contract map would create noisy false positives.

4. Separate diagnostic findings from immediate repairs.

   The diagnostic should repair low-risk stale evidence rows or test/assertion
   gaps when the fix is local. Structure split recommendations should be
   reported unless a small split is clearly isolated and unclaimed.

   Alternative considered: automatically split every broad module flagged by
   the diagnostic. Rejected because parallel agents are already working on
   owner-module polish and broad refactors need explicit ownership.

## Risks / Trade-offs

- Diagnostic inventory can become noisy as files move during parallel work ->
  keep findings path-specific, rerun before finalizing, and mark evidence stale
  when files change.
- AST checks can miss semantic bugs inside a function -> report this as a
  coverage accounting diagnostic, not a full behavioral proof.
- Background router tests can produce stale/incomplete artifacts -> inspect
  exit/meta artifacts and rerun exact focused tests in foreground when needed.
- Broad module split recommendations may overlap peer-agent work -> report
  split candidates separately from files edited by this change.

## Migration Plan

1. Add diagnostic inventory and gap classifications to the existing alignment
   runner.
2. Add tests for report schema, inventory coverage, and known-bad hazards.
3. Generate the current full diagnostic JSON and documentation summary.
4. Run focused alignment/unit checks and background model regressions with
   complete artifact evidence.
5. Sync the locally installed FlowPilot skill only if repo-owned skill files are
   changed or install freshness is part of the validation boundary.

## Open Questions

- How much of the currently active `final-owner-module-polish` untracked work
  should be included in the final committed diagnostic baseline? Default: read
  and report it as current workspace state, but do not stage those files unless
  they are clearly owned by this change.
