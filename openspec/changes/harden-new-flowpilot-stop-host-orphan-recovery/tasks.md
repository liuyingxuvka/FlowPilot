## 1. Model And Contract Setup

- [x] 1.1 Validate the new OpenSpec change and record the selected scope.
- [x] 1.2 Add a focused FlowGuard model/check for stop, host-liveness, no-output, and orphan-evidence recovery.

## 2. Runtime Implementation

- [x] 2.1 Add new-runtime stop/cancel lifecycle helpers and `flowpilot_new.py` commands.
- [x] 2.2 Add host-liveness report persistence and public CLI command.
- [x] 2.3 Extend wait recovery to prefer latest host liveness over stale progress.
- [x] 2.4 Add narrow FlowGuard/mechanical orphan evidence detection and recovery-duty classification.

## 3. Tests And Rehearsal

- [x] 3.1 Add focused lifecycle tests for stop/cancel and final-preflight behavior.
- [x] 3.2 Add focused host-liveness and no-output tests covering progress followed by host loss.
- [x] 3.3 Add focused orphan-evidence tests proving recovery duty without packet acceptance.
- [x] 3.4 Extend public fake AI rehearsal for stop, host loss, and orphan evidence.

## 4. Validation, Install, And Git

- [x] 4.1 Run OpenSpec validation for this change.
- [x] 4.2 Run focused pytest and FlowGuard checks affected by this change.
- [x] 4.3 Run broader relevant new-runtime/fake-rehearsal regression.
- [x] 4.4 Sync and audit the local installed `flowpilot` skill.
- [x] 4.5 Commit the validated integrated local git version; the interdependent system-owned closure peer change was included after validation because it touched the same runtime path.
