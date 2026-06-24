## 1. Runtime Sequencing

- [x] 1.1 Add helpers that distinguish raw parent replay acceptance from reviewed parent replay closure.
- [x] 1.2 Add a topology-ordered selector for the deepest/earliest accepted parent replay result missing independent review.
- [x] 1.3 Ensure accepted parent replay task results issue/reuse normal independent review packets instead of closing the node directly.
- [x] 1.4 Gate parent/top-level replay issuance and consumption on reviewed child/module replay evidence.
- [x] 1.5 Gate terminal backward replay on reviewed parent/module/top-level replay evidence.
- [x] 1.6 Make final-closure missing-review repair produce a real current Reviewer packet action, not a generic `final_closure` repair pseudo-packet.

## 2. Prompt, Policy, and Contract Surfaces

- [x] 2.1 Update PM parent backward target guidance to require reviewed parent replay before closure.
- [x] 2.2 Update Reviewer parent backward replay guidance to distinguish replay execution from independent replay review.
- [x] 2.3 Update PM parent segment decision guidance so `continue` requires reviewed parent replay evidence.
- [x] 2.4 Update terminal Reviewer and PM closure guidance so terminal replay cannot substitute for missing parent replay review.
- [x] 2.5 Update Controller break-glass guidance so missing parent replay review maps to routable current review packets without fallback.
- [x] 2.6 Update route action policy and evidence matrices to name reviewed parent replay as the parent-segment precondition.

## 3. FlowGuard and Test Coverage

- [x] 3.1 Add focused FlowGuard model/check coverage for sequential parent replay review ordering and no-fallback old-state rejection.
- [x] 3.2 Update fake-AI E2E coverage for raw parent replay pass, independent replay review, simultaneous child/top missing reviews, duplicate patrol, and terminal replay gating.
- [x] 3.3 Update core runtime unit tests for the new two-step parent replay closure.
- [x] 3.4 Update route-tier or router-runtime tests that currently expect direct parent replay closure.
- [x] 3.5 Add negative tests proving reviewer-owned `task.parent_backward_replay` execution does not count as independent review.

## 4. Validation, Install Sync, and Release Prep

- [x] 4.1 Run focused runtime, route, fake-E2E, and new FlowGuard checks.
- [x] 4.2 Rebuild/check FlowGuard project topology after model/test/prompt changes.
- [x] 4.3 Run install self-check and local install sync audit.
- [x] 4.4 Bump version and update changelog with the no-fallback sequential parent replay review fix.
- [x] 4.5 Sync the repository-owned installed FlowPilot skill and verify installed/source freshness.
- [x] 4.6 Run final git/status audit and leave unrelated peer changes untouched.
