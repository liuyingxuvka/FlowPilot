## 1. Model And Prompt Contract

- [x] 1.1 Add FlowGuard coverage for Controller user-report leakage and compact progress-fact status summaries.
- [x] 1.2 Add the plain-language user-report rule to the Controller core card.
- [x] 1.3 Add the common Router action user-reporting reminder.

## 2. Status Summary Implementation

- [x] 2.1 Add `progress_summary` construction from public route/frontier/run state.
- [x] 2.2 Keep existing status summary fields and sealed-body exclusion guarantees intact.

## 3. Validation And Sync

- [x] 3.1 Add or update focused tests for Controller action policy metadata and `progress_summary`.
- [x] 3.2 Run focused FlowGuard checks and unit tests; launch heavyweight meta/capability regressions in background if needed.
- [x] 3.3 Sync the local installed FlowPilot skill and run install/audit checks.
