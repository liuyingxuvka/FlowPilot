## Context

FlowPilot already has several deterministic package layers: synthetic trace
replay, hard-gate red-team packages, full-flow E2E chaos, control-plane
canaries, real-Router dry-run rehearsal, and installed shadow launcher chaos.
Those layers improved the normal flow and many single-error cases, but the
remaining high-risk gap is closer to what happened during live use: historical
state residue, stale background proof, controller done receipts that do not
match Router state, host role lifecycle interruptions, installed-source drift,
parallel agent contention, and display projections that look current but are
not authoritative.

This work must reuse the real Router, packet runtime, role-output runtime,
background artifact classifier, existing TestMesh tier, and FlowGuard
Model-Test Alignment. It must not create a parallel fake control plane.

## Goals / Non-Goals

**Goals:**

- Convert recent real-run failure families into named, finite fake AI package
  rows with required entrypoints, expected standard states, protected
  invariants, evidence tests, and explicit confidence boundaries.
- Exercise selected rows through real runtime APIs rather than matrix-only
  declarations.
- Include combination failures, not just one clean bad case per test.
- Register the new evidence in the fast tier, Model-Test Alignment, and
  generated coverage artifacts.
- Run final validation after all writes, sync the installed FlowPilot skill,
  and commit locally.

**Non-Goals:**

- No live AI model calls are required.
- No promise is made that every future AI semantic mistake is impossible.
- No release, tag, push, deploy, or OpenSpec archive is included.
- No broad Router refactor is intended unless tests expose a root-cause bug.

## Decisions

- Use a matrix plus focused runtime tests. The matrix is the finite coverage
  contract; the tests prove representative rows through real code and reject
  known-bad overclaims.
- Treat historical real-run records as replay packages, not as authority by
  themselves. A row must say whether a production replay adapter is required;
  if no adapter exists, the confidence boundary must disclose that limitation.
- Treat progress logs, stale peer proof, and exit/meta mismatches as evidence
  states, not as pass evidence. Final artifacts and current-run binding remain
  mandatory.
- Use real resume and packet/runtime helpers for role lifecycle and relay
  mechanics. Package-level semantic validators may be test helpers, but they
  can only express package acceptance gates and cannot replace real runtime
  evidence.
- Add the new suite to fast tier because it targets user-observed control-plane
  bugs. Broader fast/meta/capability regressions still run after focused tests.

## Risks / Trade-offs

- Runtime tests can become too slow -> keep the new suite focused and leave
  broad stress to the fast background run.
- Package matrices can overclaim -> every row carries `confidence_boundary`,
  `live_ai_semantic_quality_proven: false`, and current primary evidence.
- Production replay adapter coverage can be incomplete -> rows must explicitly
  say whether they used an adapter or only a fixture snapshot.
- Parallel work can stale evidence -> final validation is run after all writes,
  and background artifacts are inspected for final exit/meta status.
- Installed skill sync can lag source -> install sync and install audit run
  after validation and before local commit.
