## 1. FlowGuard Field Lifecycle Model

- [x] 1.1 Extend the existing field mesh lifecycle vocabulary with transition semantics for terminal, pending, append-only, pointer, and derived projection fields.
- [x] 1.2 Add current field-contract rows and lifecycle chains for packet/result/frontier currentness fields without introducing compatibility aliases.
- [x] 1.3 Add field lifecycle projection evidence into model-test alignment for the currentness/projection field family.

## 2. Runtime Currentness Repair

- [x] 2.1 Make late results append audit evidence without reactivating packets in noncurrent terminal dispositions.
- [x] 2.2 Route compact status and final closure active-packet scans through the single currentness predicate.
- [x] 2.3 Ensure pending route mutation state is not left current after route/frontier commit paths.

## 3. Regression and Fake-Agent Coverage

- [x] 3.1 Add focused runtime tests for late results after accepted, quarantined, and superseded packet dispositions.
- [x] 3.2 Add projection tests for stale route-node and stale route-version active-packet filtering.
- [x] 3.3 Add FlowGuard/fake-agent coverage that proves the field lifecycle model and public current-contract path catch same-family misses.

## 4. Validation and Sync

- [x] 4.1 Run field mesh, field contract, model-test alignment, and focused runtime/fake-agent tests.
- [x] 4.2 Rebuild/check project topology if model/test/code ownership artifacts changed.
- [x] 4.3 Sync local install and run install/audit checks.
- [x] 4.4 Review peer-agent changes, commit the integrated work, and report validation evidence.
