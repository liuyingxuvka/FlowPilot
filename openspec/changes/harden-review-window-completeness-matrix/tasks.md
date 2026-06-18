## 1. Matrix Declaration

- [x] 1.1 Add a review-window completeness declaration surface with stable `review_flow_id` rows for every current runtime-issued Reviewer flow.
- [x] 1.2 Generate required path and mutation cells from the completeness rows, including subject, stage, window path, material authorization, future-stage boundary, and PM repair return mutations.
- [x] 1.3 Add orphan-flow and row-shape guards so runtime-issued review flows cannot exist without exactly one completeness row.

## 2. Fake AI Responder Coverage

- [x] 2.1 Extend the existing contract-driven fake AI responder with review-window-aware behavior profiles.
- [x] 2.2 Generate Cartesian fake-AI cells across review flow, material state, behavior profile, and retry-count class.
- [x] 2.3 Add expected oracle reactions for shallow pass, skipped read, future-stage demand, unauthorized body request, invented scope, self-repair, PM bypass, corrected retry, and threshold failure.

## 3. Runtime And Prompt Alignment

- [x] 3.1 Ensure emitted Reviewer packets expose the completeness row identity and all required structured window fields in envelope and body handoff contract.
- [x] 3.2 Keep Reviewer and PM cards aligned with the structured window and single PM repair/recheck path without adding a second reviewer framework.
- [x] 3.3 Ensure review-window contract failures produce precise field/material paths and repairable guidance in tests or runtime feedback.

## 4. Focused Tests And FlowGuard Models

- [x] 4.1 Add focused tests for every declared review flow proving envelope/body window equality and required field/material coverage.
- [x] 4.2 Add negative tests for missing, wrong, stale, mismatched, and prose-only review-window material.
- [x] 4.3 Add fake-AI responder tests for all new review-window profiles and retry threshold classes.
- [x] 4.4 Update contract-exhaustion/current-contract/model-test-alignment checks so generated cells have current evidence owners.

## 5. Validation, Sync, And Release

- [x] 5.1 Run focused unit tests and FlowGuard model checks affected by review-window completeness and fake-AI coverage.
- [x] 5.2 Rebuild/check topology and run install/local sync checks after model/test changes.
- [x] 5.3 Update version/release notes and local git state; defer GitHub push and public release per user instruction.
