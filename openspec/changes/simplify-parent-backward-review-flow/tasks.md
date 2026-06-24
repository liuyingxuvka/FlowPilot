## 1. Contract And Runtime Shape

- [x] 1.1 Replace current positive `task.parent_backward_replay` family with `review.parent_backward_replay` in packet result contracts, minimal valid shapes, and family lookup.
- [x] 1.2 Update packet-stage evidence matrix rows, stage groups, allowed blockers, required fields, fake-AI success fields, and forbidden old-shape fields for parent backward review.
- [x] 1.3 Remove runtime dependence on raw replay plus independent review helpers; make parent backward review result itself the closure evidence.
- [x] 1.4 Change parent backward packet creation, packet family detection, result validation, closure recording, run-shell projection, and event labels to the single review path.
- [x] 1.5 Add runtime guards that block downstream sibling/ancestor/terminal/final progression until parent backward review passes and PM absorbs it.
- [x] 1.6 Add hard-block detection for impossible multiple unclosed parent/module backward review gaps or route advance past an unclosed parent gate.
- [x] 1.7 Reject `task.parent_backward_replay` and old two-step review evidence as unsupported current-contract shapes without migration, fallback, or translation.

## 2. Prompt, Policy, And Documentation Surfaces

- [x] 2.1 Update Reviewer parent backward replay card so the card is the review signature and no second review packet is expected.
- [x] 2.2 Update PM parent target, PM parent segment decision, terminal backward replay, PM closure, and controller break-glass cards to require one current parent backward review plus PM absorption.
- [x] 2.3 Update route action policy registry, protocol reference, failure modes, and current-contract guidance to remove the two-step parent replay review semantics.
- [x] 2.4 Search for positive old-shape language and classify every remaining `task.parent_backward_replay` or independent-review-over-replay hit as forbidden/deleted, negative test, historical label, or current valid reference.

## 3. FlowGuard Models And Cartesian Coverage

- [x] 3.1 Replace the sequential parent replay review model with a single parent backward review model covering legal V-shaped closure and corrupt multi-gap hard blockers.
- [x] 3.2 Add a fake-AI Cartesian parent backward review coverage universe with finite route-shape, payload-profile, timing, evidence-state, and expected-action axes.
- [x] 3.3 Ensure the Cartesian checker distinguishes legal runtime paths from injected impossible states and reports missing coverage cells/shards.
- [x] 3.4 Update current-contract Cartesian matrix, model-test alignment inputs, and generated result artifacts to include the new parent backward review family.

## 4. Runtime And Fake-AI Tests

- [x] 4.1 Update fake-E2E responder to return `review.parent_backward_replay` payloads and inject missing-field, wrong-shape, stale-evidence, old-shape, and conflicting-pass/blocker profiles.
- [x] 4.2 Update core runtime unit tests to assert parent backward review closes without a second review, PM absorption is required, downstream progression is blocked, and old task-shaped evidence is rejected.
- [x] 4.3 Update new-entrypoint fake E2E tests to assert exactly one parent backward review packet, no `review.any_current_subject` over it, and final evidence matrix coverage.
- [x] 4.4 Update router runtime common helpers and router quality/packet/route/terminal tests to follow the single review path and hard-block corrupt multi-gap states.
- [x] 4.5 Update synthetic trace, chaos replay, historical live-run replay, and route authority tests so positive fixtures use the new review family and old shapes remain negative-only.

## 5. TestMesh And Release Evidence

- [x] 5.1 Add acceptance TestMesh cells for parent backward review current contract, missing fields, wrong shape, old task rejection, no second review, downstream progression blocker, PM absorption, route mutation rerun, and corrupt multi-gap hard block.
- [x] 5.2 Run focused runtime, fake-AI Cartesian, FlowGuard model, and OpenSpec strict validation; fix all failures.
- [x] 5.3 Run router quality, packets, route, and terminal tiers with current background artifacts and confirm completed pass evidence, not progress-only output.
- [x] 5.4 Run model-test alignment, card instruction coverage, acceptance TestMesh, release tier background checks, topology build/check, and install sync audits.

## 6. Versioning, Records, And Final Audit

- [x] 6.1 Update VERSION, README, CHANGELOG, FlowGuard adoption logs, and OpenSpec task checkboxes with the final single-path parent backward review evidence.
- [x] 6.2 Sync the repository-owned installed FlowPilot skill and verify source/install freshness.
- [x] 6.3 Run final `git diff --check`, inspect status, create one local git commit, and leave unrelated peer changes untouched.
- [x] 6.4 Perform requirement-by-requirement completion audit against the user objective before marking the persistent goal complete.
