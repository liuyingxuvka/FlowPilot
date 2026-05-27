## 1. Scope And Guardrails

- [x] 1.1 Run predictive KB preflight, repository coordination checks, real
  FlowGuard import preflight, OpenSpec strict validation, maintenance map,
  validation-artifact audit, and runtime-retention report.
- [x] 1.2 Validate this OpenSpec change strictly before production edits.

## 2. OpenSpec Archive Convergence

- [x] 2.1 Archive completed active OpenSpec changes that have strict validation
  evidence while preserving tracked files under `openspec/changes/archive/`.
- [x] 2.2 Re-run OpenSpec validation after archive movement and record any
  intentionally active or failed changes.

## 3. Report-First Cleanup Evidence

- [x] 3.1 Record duplicate validation artifact audit evidence without deleting,
  moving, or rewriting result files.
- [x] 3.2 Record `.flowpilot` runtime retention evidence without deleting the
  current run, run index, or runtime directories.

## 4. FlowGuard Hotspot Contraction

- [x] 4.1 Split only proven runtime-owner hotspots into child modules with
  original imports retained as compatibility facades.
- [x] 4.2 Keep public router exports, runtime data contracts, prompt text, CLI
  behavior, and event/ledger shapes unchanged.

## 5. Verification And Sync

- [x] 5.1 Run focused syntax, router, StructureMesh, model-test alignment, and
  maintenance diagnostics for touched code.
- [x] 5.2 Launch background Meta and Capability regressions, then inspect final
  stdout, stderr, combined, exit, and meta artifacts before claiming pass.
- [x] 5.3 Update version/changelog/handoff or maintenance notes with exact
  evidence and skipped boundaries.
- [x] 5.4 Sync the repo-owned FlowPilot installed skill and run install freshness
  audit/checks.

## 6. Finalization

- [x] 6.1 Run final OpenSpec strict validation and git scope review.
- [x] 6.2 Run KB postflight and record a reusable lesson if this pass exposes
  one.
- [x] 6.3 Stage intended files only and create a local git commit without
  pushing, tagging, deploying, or publishing.
