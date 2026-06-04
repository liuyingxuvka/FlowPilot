## 1. OpenSpec And FlowGuard Grounding

- [x] 1.1 Create the new-only control-plane OpenSpec proposal, design, spec, and tasks.
- [x] 1.2 Verify the real FlowGuard package/schema/project audit before code edits.
- [x] 1.3 Ground implementation in the existing control-plane friction model.

## 2. Runtime New-Only Control Plane

- [x] 2.1 Make packet outcome parsing reject missing, unknown, alias, or prose decisions instead of defaulting to pass.
- [x] 2.2 Make PM repair decision parsing accept only the current top-level JSON contract.
- [x] 2.3 Retire older same-family active/awaiting-recheck blockers when a newer repair or recheck path becomes current.
- [x] 2.4 Ensure accepted-result plus superseded-packet state is historical only and not a current target.
- [x] 2.5 Make final preflight ignore retired history but reject any stale live blocker/gate/reference that remains active.

## 3. Formal Entry Surface

- [x] 3.1 Remove formal old-router compatibility wording and CLI exposure from the FlowPilot entrypoint.
- [x] 3.2 Keep any rehearsal-only helper clearly internal and outside the formal runtime path.

## 4. FlowGuard Models And Tests

- [x] 4.1 Extend the existing control-plane friction model for long repair-chain blocker convergence.
- [x] 4.2 Add focused runtime tests for strict parsing, blocker retirement, final preflight, and accepted/superseded current-target state.
- [x] 4.3 Add or update entrypoint/install checks for old compatibility surface absence.

## 5. Validation, Sync, And Git

- [x] 5.1 Run focused pytest/runtime checks and focused FlowGuard model checks.
- [x] 5.2 Run long meta/capability regressions in background and inspect artifacts.
- [x] 5.3 Sync the installed FlowPilot skill and run install sync audit/checks.
- [x] 5.4 Commit the synchronized local git version after validation.
- [x] 5.5 Perform KB postflight and record any reusable route lesson.
