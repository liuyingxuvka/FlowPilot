## Why

Live FlowPilot runs can currently misread explanatory prose as a blocking
result and can keep old repaired blockers visible as current blockers after the
owning node has already been accepted. That makes the control plane report
semantic repair even when the current work is actually ready to continue.

## What Changes

- **BREAKING**: Stop deriving non-pass outcomes from arbitrary free-text prose.
  Packet results are judged by explicit outcome fields or explicit outcome
  declaration lines only.
- Preserve declared pass results even when the explanation mentions historical
  failures, failed checks, blockers, or function-block terminology.
- Treat active semantic blockers as an effective current view, not a raw history
  table. Blockers tied to accepted, waived, superseded, or repaired work are not
  projected as current blockers.
- Clear same-node repair blocker chains from the current same-gate pass, and
  keep stale failed packets as history instead of final-closure blockers.
- Extend FlowGuard and ordinary tests to cover prose-overread, stale blocker
  projection, and final ledger effective-view behavior.

## Capabilities

### New Capabilities

- `flowpilot-effective-outcome-authority`: Defines authoritative packet outcome
  parsing and current-effective blocker/final-ledger projection for the new
  FlowPilot runtime.

### Modified Capabilities

None.

## Impact

- Affected runtime: `skills/flowpilot/assets/flowpilot_core_runtime/runtime.py`
- Affected tests: focused core runtime, high-standard control-flow, and
  recursive route execution tests.
- Affected FlowGuard model: semantic gate outcome model and runner.
- No compatibility fields are added for old FlowPilot result formats.
