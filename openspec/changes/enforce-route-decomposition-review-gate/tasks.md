## 1. OpenSpec And FlowGuard Boundary

- [x] 1.1 Validate OpenSpec artifacts before implementation.
- [x] 1.2 Inspect current planning, FlowGuard, Reviewer, and PM repair flow for overlap with peer edits.
- [x] 1.3 Record the FlowGuard route decision and validation plan.

## 2. Prompt And Card Updates

- [x] 2.1 Add route decomposition quality criteria to the PM planning packet without adding route-node schema fields.
- [x] 2.2 Update PM route skeleton guidance so broad stage names must normally become parents/modules with smaller leaves.
- [x] 2.3 Update FlowGuard Operator route-process guidance to block worker-decision leakage.
- [x] 2.4 Update Reviewer route guidance so Reviewer blocks under-decomposed leaves and returns PM-readable split advice.
- [x] 2.5 Update node acceptance plan guidance so node-entry splitting is a fallback gate before Worker dispatch.

## 3. Runtime And Tests

- [x] 3.1 Add focused runtime test coverage for Reviewer-blocked planning staying unmaterialized.
- [x] 3.2 Add focused runtime test coverage for PM repair/recheck after planning decomposition block.
- [x] 3.3 Add card/instruction coverage tests for PM, FlowGuard Operator, Reviewer, and node-entry fallback language.
- [x] 3.4 Keep route-node schema unchanged unless a validation failure proves a minimal field is required.

## 4. Verification And Sync

- [x] 4.1 Run OpenSpec strict validation.
- [x] 4.2 Run targeted FlowPilot unit tests.
- [x] 4.3 Run relevant FlowGuard model/test-alignment checks and topology checks.
- [x] 4.4 Sync repository-owned FlowPilot files to the installed local skill.
- [x] 4.5 Verify the installed local FlowPilot version after sync.
- [x] 4.6 Review git status and preserve peer-agent changes.
- [x] 4.7 Perform KB postflight and record any reusable lesson.
