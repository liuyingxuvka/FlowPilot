## 1. OpenSpec And FlowGuard

- [x] 1.1 Add OpenSpec proposal, design, specs, and tasks for the control-plane contract kernel.
- [x] 1.2 Extend the existing control-plane FlowGuard model with signed-artifact, action-identity, stateful-blocker-receipt, self-check grammar, and formal-package hazards.
- [x] 1.3 Validate the OpenSpec change strictly and run the focused FlowGuard check.

## 2. Runtime Contracts

- [x] 2.1 Add the shared control-plane contract helper module.
- [x] 2.2 Include control-blocker identity fields in Router scheduler and Controller action identity.
- [x] 2.3 Prevent closed Controller action rows from being overwritten by a different identity.
- [x] 2.4 Make `handle_control_blocker` a stateful Controller receipt with a replayable delivery postcondition.
- [x] 2.5 Keep signed material packet envelopes immutable during legacy migration and write migration sidecars instead.
- [x] 2.6 Align self-check parser grammar with existing Worker body vocabulary.
- [x] 2.7 Require absorbed PM package dispositions to reference a reviewer-readable formal gate package path and hash.

## 3. Verification

- [x] 3.1 Add focused unit/runtime coverage for the five known failures.
- [x] 3.2 Run compile checks for touched runtime/model files.
- [x] 3.3 Run focused Python tests for contracts, packets, controller scheduler identity, and PM package release.
- [x] 3.4 Run background meta/capability model regressions and inspect artifact-contract evidence.

## 4. Sync And Git

- [x] 4.1 Sync repo-owned FlowPilot assets to the local installed skill.
- [x] 4.2 Run install audit/check and source freshness verification.
- [ ] 4.3 Preserve unrelated peer edits and create the requested local git version.
