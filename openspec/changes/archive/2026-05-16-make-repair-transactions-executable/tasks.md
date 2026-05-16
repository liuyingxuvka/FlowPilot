## 1. FlowGuard Model

- [x] 1.1 Add repair-transaction model coverage for executable plan kinds and dead-wait rejection.
- [x] 1.2 Run the focused repair-transaction FlowGuard check and inspect stable background artifacts.

## 2. Router Runtime

- [x] 2.1 Add executable repair plan-kind constants, normalization, and plan-specific validation helpers.
- [x] 2.2 Update PM repair decision handling so committed repair transactions require a queued action, existing event producer, Router handler result, or terminal stop.
- [x] 2.3 Preserve existing `packet_reissue` behavior and strict compatibility for legacy `event_replay`.

## 3. Cards And Contracts

- [x] 3.1 Update the PM repair contract allowed plan kinds and required plan fields.
- [x] 3.2 Update PM role and repair phase guidance with plan-kind selection rules.
- [x] 3.3 Update Controller guidance for bounded `controller_repair_work_packet` execution.

## 4. Tests And Verification

- [x] 4.1 Add focused router tests for dead-wait rejection, executable existing-event wait, operation replay validation, and bounded Controller repair packets.
- [x] 4.2 Run focused router tests and OpenSpec validation.
- [x] 4.3 Synchronize the installed local FlowPilot skill and verify local repository/git status including parallel-agent changes.
