## Context

FlowPilot has already gone through several structure-reduction passes. The
largest remaining code surface is `flowpilot_router.py`, and the largest
remaining validation surfaces are long-running router runtime suites and
layered Meta/Capability checks. FlowGuard now provides StructureMesh and
TestMesh APIs that can review parent/child ownership and evidence contracts
before the refactor moves code.

This change is a maintenance change. It preserves public runtime behavior and
does not introduce a release, deployment, public API change, or new dependency.

## Goals / Non-Goals

**Goals:**

- Make StructureMesh the preflight and completion gate for the next large
  router/module split.
- Keep the router facade as the owner of root state coordination and public
  entrypoints while child modules own focused record families.
- Add TestMesh evidence so slow router suites and background artifacts cannot
  be reported as passed from progress output alone.
- Add Model-Test Alignment evidence using FlowGuard's
  `ModelObligation`, `TestEvidence`, and `review_model_test_alignment()` API so
  each required model obligation is tied to ordinary test evidence or an
  explicit gap.
- Split remaining large model and test-helper files only where an executable
  focused check proves parity.
- Keep Meta and Capability parent checks on the new layered full path.

**Non-Goals:**

- No behavior change to event names, persisted JSON shapes, CLI commands,
  public imports, packet authority, wait semantics, role authority, or terminal
  completion rules.
- No legacy full Meta/Capability regression unless explicitly requested.
- No remote push, tag, release, deployment, or package publication.
- No broad formatter or unrelated cleanup.

## Decisions

1. **Use StructureMesh before moving router code.**
   - Rationale: a naive split can assign the same root route state to several
     children. StructureMesh catches this as a duplicate owner before code is
     moved.
   - Alternative considered: split by line count first and test afterward.
     This is rejected because event intake, daemon state, bootloader state, and
     terminal ledgers share durable state and side effects.

2. **Keep `flowpilot_router.py` as compatibility facade and root coordinator.**
   - Rationale: public imports and CLI behavior remain stable while child
     modules can own event-family, daemon, bootloader, PM role-work, terminal,
     and blocker repair responsibilities.
   - Alternative considered: move root state writes into child modules. This
     is rejected because it creates duplicate state ownership.

3. **Use child modules that own record families, not the entire run state.**
   - Rationale: child modules can own `event_log`, `daemon_status_record`,
     `bootloader_rows`, PM role-work records, terminal ledger records, and
     control-blocker records while the facade remains responsible for final
     orchestration and public entrypoints.

4. **Use TestMesh for validation hierarchy.**
   - Rationale: router runtime tests are slow enough that progress output,
     timeout, or skipped suites can be mistaken for completion. TestMesh keeps
     child suite ownership and final background artifacts explicit.

5. **Use Model-Test Alignment before adding or trusting more tests.**
   - Rationale: FlowPilot already has many FlowGuard models and many ordinary
     tests. The next confidence gap is not raw count; it is whether each model
     obligation has the right kind of ordinary test evidence.
   - Alternative considered: maintain a hand-written prose matrix only. This is
     rejected because FlowGuard already provides an executable alignment review
     with missing, stale, duplicate, orphan, and overclaim findings.

6. **Use focused model splits before parent regressions.**
   - Rationale: persistent daemon, prompt isolation, and cross-plane friction
     should be split behind their focused runners first. Meta/Capability parent
     checks remain release evidence after child checks are current.

## Risks / Trade-offs

- **Shared state gets duplicated across child modules** -> Mitigate by keeping
  root state ownership in the facade and requiring StructureMesh release scope
  before completion.
- **Facade becomes a hidden second implementation** -> Mitigate by moving
  bodies behind helpers while keeping the facade as a thin public entrypoint.
- **Background checks are overclaimed** -> Mitigate by requiring `.out.txt`,
  `.err.txt`, `.combined.txt`, `.exit.txt`, and `.meta.json` artifacts before a
  long check counts as complete.
- **Model pass is confused with ordinary test coverage** -> Mitigate by running
  FlowGuard Model-Test Alignment and blocking broad coverage claims when a
  required obligation lacks current passing test evidence.
- **Generated proof/result timestamps create noisy diffs** -> Mitigate by
  inspecting generated artifacts and committing only meaningful source/result
  updates.
- **Model split changes an invariant accidentally** -> Mitigate with focused
  child model runners plus hierarchy and layered parent checks.

## Migration Plan

1. Create a backup of the current `main` state.
2. Add executable FlowGuard StructureMesh/TestMesh artifacts and verify their
   known-bad hazards.
3. Add executable FlowGuard Model-Test Alignment evidence and use it to decide
   which tests or model obligations need follow-up.
4. Move router responsibilities in small facade-preserving clusters.
5. Split slow router test-tier commands into smaller child suites with
   TestMesh ownership.
6. Split model/test helper hotspots with focused checks after each boundary.
7. Run focused checks, background router suites, layered Meta/Capability, and
   install/public-readiness checks.
8. Synchronize the local installed FlowPilot skill from repo-owned source.
9. Commit locally on `main` after validation.

Rollback uses the backup directory and local Git commit history. No remote or
release-side rollback is required because this change does not push or publish.

## Open Questions

- None requiring user decision before implementation. If a candidate split
  fails StructureMesh release scope or focused parity checks, that candidate
  will be deferred and reported rather than forced.
