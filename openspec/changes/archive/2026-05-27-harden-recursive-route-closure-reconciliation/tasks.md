## 1. Baseline And Specification

- [x] 1.1 Confirm repository, KB, OpenSpec, FlowGuard, and coordination baseline.
- [x] 1.2 Create and strictly validate this OpenSpec change.

## 2. FlowGuard Model

- [x] 2.1 Add focused FlowGuard coverage for recursive parent/module traversal
  and terminal closure reconciliation.
- [x] 2.2 Run the focused model and inspect hazards before runtime edits.

## 3. Runtime Implementation

- [x] 3.1 Make recursive route traversal enter sibling parent/module nodes before
  descendants.
- [x] 3.2 Add defect ledger reconciliation status helpers.
- [x] 3.3 Add role memory reconciliation status helpers.
- [x] 3.4 Add continuation quarantine/imported-artifact reconciliation helpers.
- [x] 3.5 Record and enforce the reconciliation statuses in final ledger and
  terminal closure.

## 4. Tests, Templates, Docs, And Version

- [x] 4.1 Add or update focused runtime tests for sibling parent entry.
- [x] 4.2 Add or update focused runtime tests for terminal closure blocking and
  reporting of reconciliation results.
- [x] 4.3 Update templates, install checks, README/HANDOFF/CHANGELOG, and version
  metadata.

## 5. Verification, Sync, And Git

- [x] 5.1 Run focused unit tests and focused FlowGuard checks.
- [x] 5.2 Launch and inspect background Meta and Capability regressions through
  the repository artifact contract.
- [x] 5.3 Run install checks, sync the local installed FlowPilot skill, and audit
  installed freshness.
- [x] 5.4 Run KB postflight, review the diff, stage, and create a local commit
  without pushing, tagging, or publishing.
