## Why

Native FlowPilot startup can create a control-plane blocker after the startup
intake UI completes when the live daemon projects `record_startup_answers` as a
Controller-receipt action but Router can only satisfy that postcondition through
the bootloader apply path. The failure was observed in
`run-20260520-170452` and shows that startup answer settlement still lacks a
single owner and idempotent replay contract.

## What Changes

- Treat the confirmed startup intake result as the single authoritative owner
  for recording startup answers and deterministic startup seed artifacts.
- Reconcile live-daemon startup receipts so completed intake side effects do
  not reissue `record_startup_answers` or seed-owned deterministic setup rows.
- Make `record_startup_answers` idempotent when durable startup answers already
  satisfy the same postcondition.
- Keep unsupported or genuinely incomplete startup receipts on the existing
  blocker path.
- Add regression coverage for the live-daemon receipt/apply interleaving that
  triggered the observed blocker.

## Capabilities

### New Capabilities

- `startup-answer-reconciliation`: startup answer settlement, replay, and
  control-plane blocker prevention for native intake and daemon bootloader
  reconciliation.

### Modified Capabilities

- `startup-settlement-ownership`: clarify that startup answers and deterministic
  seed side effects have one authoritative owner and must be replay-safe.
- `deterministic-startup-bootstrap`: clarify that completed seed evidence
  prevents later deterministic setup rows from being scheduled as Controller
  work.

## Impact

- Startup bootloader receipt reconciliation and daemon projection logic.
- Runtime tests covering startup bootstrap and Controller action reconciliation.
- FlowGuard-focused regression evidence for the observed model miss.
- Local install sync and audit after the source fix passes validation.
