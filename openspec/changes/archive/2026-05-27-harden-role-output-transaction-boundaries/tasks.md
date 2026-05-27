## 1. Model and Contract Grounding

- [x] 1.1 Extend the role-output runtime FlowGuard/source check to cover PM package disposition contracts, fixed Router events, allowed role, and envelope-only body references.
- [x] 1.2 Extend the control transaction registry model/source check to cover PM package disposition as result absorption with PM producer role, PM output contract, packet authority, and full commit targets.
- [x] 1.3 Extend the PM package absorption model/check to cover interrupted disposition replay, hash verification, and quarantine/blocker behavior for half-written artifacts.
- [x] 1.4 Extend control-plane friction or identity checks so blocker-related `await_role_decision` actions with different blocker identity cannot share ids.

## 2. Runtime Implementation

- [x] 2.1 Add PM package disposition contract binding metadata to the runtime contract registry and role-output runtime schema specs.
- [x] 2.2 Update PM package disposition wait/action payloads so Router supplies the expected output contract and output type.
- [x] 2.3 Update Router event handling so PM package disposition accepts only the registry-backed role-output envelope path for formal submissions.
- [x] 2.4 Route PM package disposition writes through the control transaction registry and make replay of already-written disposition artifacts verify required targets before completion.
- [x] 2.5 Generalize control-blocker identity extras to all blocker-related actions that carry blocker identity.
- [x] 2.6 Correct blocker outcome/status wording so logs use structured producer/event/outcome fields instead of hard-coded reviewer wording.

## 3. Tests and Validation

- [x] 3.1 Add focused runtime tests for valid PM package disposition role-output submission and manual-envelope rejection.
- [x] 3.2 Add focused runtime tests for interrupted PM disposition replay and transaction-target mismatch blocking.
- [x] 3.3 Add focused runtime tests for distinct blocker-related `await_role_decision` identities.
- [x] 3.4 Run focused FlowGuard checks, focused runtime/unit tests, and install checks; triage any failure before continuing.
- [x] 3.5 Run heavy Meta and Capability checks in the documented background artifact contract and inspect completion artifacts before claiming pass.

## 4. Sync and Local Git

- [x] 4.1 Sync the validated repository-owned FlowPilot skill into the local installed version.
- [x] 4.2 Run local install audit/check and smoke validation after sync.
- [x] 4.3 Inspect final git status, stage only this change's files, and create a local commit if validation is current and peer-agent changes remain isolated.
