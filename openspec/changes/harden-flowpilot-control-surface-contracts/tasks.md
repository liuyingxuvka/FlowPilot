## 1. Model And Specification

- [x] 1.1 Add OpenSpec requirements for current-run resolution, safe evidence reads, and symmetric packet contracts.
- [x] 1.2 Add a focused FlowGuard model for the missed control-surface entrance layer.
- [x] 1.3 Add known-bad hazards for new current schema ignored, fallback-to-project-root, invalid UTF-8 crash, PM-only packet contracts, ACK/result/accepted conflation, accepted-packet reassignment, and stale generation acceptance.

## 2. Runtime And Audit Implementation

- [x] 2.1 Add shared current-run resolver and safe read helpers under the new runtime package.
- [x] 2.2 Update new runtime shell loading to use the shared resolver.
- [x] 2.3 Update live audit adapters that read the current run to use the shared resolver and safe read behavior.
- [x] 2.4 Add a lightweight packet/control-surface contract audit over the current-run ledger.

## 3. Tests And Validation

- [x] 3.1 Add unit tests for resolver compatibility and no project-root fallback.
- [x] 3.2 Add unit tests for invalid UTF-8/invalid JSON returning audit findings instead of exceptions.
- [x] 3.3 Add unit tests for symmetric packet contracts across PM, FlowGuard officer, reviewer, requested worker packets, and system validation/closure outcomes.
- [x] 3.4 Run focused FlowGuard/model checks and targeted runtime tests.
- [x] 3.5 Sync the local installed FlowPilot skill after validation and run install/audit checks.
- [x] 3.6 Inspect git status and commit only this scoped repair if validation is green.
