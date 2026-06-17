# Harden FlowGuard Semantic Recheck Evidence Chain

## Why

The SkillGuard run exposed a FlowPilot control-plane gap: a FlowGuard result body could claim `passed=true` while the formal FlowGuard evidence artifact for the same packet still reported a hard blocker such as `missing_code_contract`. The Reviewer then saw a superficially valid FlowGuard pass instead of a hard evidence failure.

The fix must stay on the existing single packet/review path. It must not introduce a SkillGuard-only flow, compatibility mode, fallback evaluator, or parent repair-node inheritance policy.

## What Changes

- Require FlowGuard packet-result acceptance to compare the result body with the packet-owned run-local `flowguard_evidence.json`.
- Require blocker-bound FlowGuard rechecks to carry `repair_blocker_id`, consume the authorized subject result, and prove subject-bound semantic coverage instead of shape-only/current-contract-only coverage.
- Prevent non-pass hard-evidence decisions from producing Reviewer-visible pass evidence.
- Add fake AI and historical SkillGuard-style replay coverage for "body passes, artifact blocks".
- Register the new checks in FlowGuard model-test alignment and synthetic-agent coverage.

## Out Of Scope

- Parent repair-node inheritance and repair-child generation.
- Route redesign semantics.
- New SkillGuard-specific control flow.
