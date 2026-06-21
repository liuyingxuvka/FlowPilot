## 1. OpenSpec And Model Grounding

- [x] 1.1 Record the producer-before-consumer route-order requirement in OpenSpec.
- [x] 1.2 Identify the existing FlowGuard/prompt/test owners for route-process ordering.

## 2. Prompt/Card Updates

- [x] 2.1 Update PM route skeleton guidance to require dependency-order self-checks without adding route fields.
- [x] 2.2 Update FlowGuard operator route-process guidance to check producer-before-consumer ordering as route viability.
- [x] 2.3 Update Reviewer route challenge guidance to independently challenge inverted route dependencies.
- [x] 2.4 Update PM and Reviewer node-acceptance guidance so node entry blocks future-node dependencies without demanding future-stage evidence.

## 3. Regression Coverage

- [x] 3.1 Add card instruction coverage for producer-before-consumer wording in the affected cards.
- [x] 3.2 Add focused model/test coverage for an inverted future-node dependency that must fail.
- [x] 3.3 Add focused model/test coverage for a correctly ordered producer-before-consumer route that must pass.

## 4. Validation And Sync

- [x] 4.1 Run focused card/model/unit tests for the changed surfaces.
- [x] 4.2 Run affected FlowGuard/meta/capability checks and inspect final artifacts.
- [x] 4.3 Rebuild/check FlowGuard project topology after prompt/test/model changes.
- [x] 4.4 Sync the local installed FlowPilot skill and verify install freshness.
- [x] 4.5 Update local version/git evidence and mark tasks complete only after evidence exists.
