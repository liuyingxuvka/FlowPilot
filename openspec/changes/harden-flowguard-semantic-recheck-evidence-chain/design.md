# Design

## Current Path

FlowPilot already routes ordinary work through:

1. subject packet result
2. FlowGuard packet
3. FlowGuard result
4. FlowGuard work order
5. Reviewer packet with authorized FlowGuard evidence read

This change strengthens that path instead of adding a new one.

## Runtime Contract

When a FlowGuard result is submitted, `_flowguard_evidence_consistency_violation` must verify three things before acceptance:

- the report body is internally consistent;
- a formal `flowguard_evidence.json` exists for formal runs and its hard decision allows pass;
- if the packet is a repair-blocker recheck, the result includes `semantic_recheck` proof bound to the active blocker and authorized subject result.

When the artifact hard decision is blocked, stale, or `missing_code_contract`, the FlowGuard result must not reach Reviewer as pass evidence.

## Repair Blocker Continuity

The existing repair identity path remains authoritative:

- subject packet `repair_blocker_id`
- FlowGuard packet `repair_blocker_id`
- `semantic_recheck_contract.blocker_id`
- FlowGuard work order `blocker_id`
- Reviewer manifest `blocker_id`

The formal identity gate rejects prose-only or mismatched blocker identity.

## Prompt Boundary

The FlowGuard operator card must say that blocker-bound rechecks are not allowed to pass by checking only fields, shape, or current contract. The PM repair card must ask for blocker-bound FlowGuard recheck evidence when Reviewer requires it.

## Evidence

Coverage is split across:

- core runtime unit tests for hard artifact decisions and semantic recheck gates;
- fake e2e replay for fake AI "body pass, artifact block";
- historical SkillGuard replay for the exposed old-run shape;
- FlowGuard model-test alignment and synthetic-agent coverage matrix.
