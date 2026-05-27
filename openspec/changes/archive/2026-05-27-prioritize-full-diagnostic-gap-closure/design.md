## Context

The current model-test alignment checker already produces a full diagnostic
inventory that compares FlowPilot model obligations, code surfaces, and tests.
That inventory is intentionally broad, but the first version is mostly a gap
enumerator: it does not yet rank findings, group duplicate repairs, or make
background evidence states explicit enough for release-level maintenance.

This change is a focused hardening pass. It must preserve existing FlowPilot
runtime behavior and public APIs while improving diagnostic output, external
contract tests, CLI evidence, and structure-split repair planning. The
repository may be worked on by parallel agents, so broad structure rewrites are
allowed only when they are clearly safe and isolated.

## Goals / Non-Goals

**Goals:**

- Make each full diagnostic finding actionable by adding severity, ownership,
  release relevance, repair type, dedupe key, and a prioritized repair list.
- Add source-contract tests for the highest-risk facade and owner-module
  boundaries so the diagnostic can distinguish external-contract evidence from
  internal-only implementation tests.
- Add fast public CLI tests for installer/sync/release/test-tier and
  packet/output/lifecycle script entrypoints.
- Classify background validation evidence as pass, failed, running,
  incomplete, stale, progress-only, or local-only release proof based on final
  artifacts, not progress text.
- Record structure split candidates as repair work, and defer only when a safe
  immediate split cannot be made without colliding with fresh owner-module
  polish.

**Non-Goals:**

- Do not change FlowPilot's public runtime protocol, route semantics, or
  installer layout unless a test exposes a concrete defect.
- Do not publish, push tags, or change protected release state.
- Do not run broad source formatting, dependency upgrades, or unrelated cleanup.

## Decisions

1. **Diagnostic metadata is computed in the checker, not handwritten in docs.**
   The JSON output remains the source of truth, while docs summarize the fields
   and repair workflow. This keeps downstream checks reproducible.

2. **External-contract evidence is test-backed.** Facades and script entrypoints
   are covered by tests that assert observable imports, JSON shapes, CLI exit
   behavior, and final artifact classification. Internal helper tests do not
   count as full external-contract coverage unless they bind an owner surface's
   public input/output contract.

3. **Background evidence is conservative.** Progress logs are liveness only.
   A pass requires final meta/exit artifacts. Release checks run with
   `--skip-url-check` are marked as local-only proof instead of public release
   proof.

4. **Structure splitting is repair-planned before broad edits.** If a candidate
   is already split or safe to refine locally, do it. If the candidate requires
   cross-cutting churn or overlaps recent owner-module polish, the diagnostic
   records a deferred split with concrete owner/reason metadata.

## Risks / Trade-offs

- [Risk] Diagnostic ranking could imply false release confidence.
  → Mitigation: release relevance and local-only proof are explicit fields, and
  coverage gaps keep `full_coverage_ok` false.
- [Risk] CLI tests become slow or flaky.
  → Mitigation: tests use help/list/dry-run/check modes and avoid starting long
  background suites unless validating classification helpers.
- [Risk] Structure split work collides with peer agents.
  → Mitigation: keep broad split candidates as deferred repair items unless the
  worktree and ownership boundary are clean.
- [Risk] Metadata fields drift from docs.
  → Mitigation: tests assert the output schema and representative known-bad
  diagnostic classifications.
