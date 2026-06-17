## Why

FlowPilot now has release-grade guard-family evidence, but the audit exposed a claim-boundary gap: the final-confidence gate can be green while the formal FlowPilot run still blocks final return at startup intake. Broad completion reporting needs a hard distinction between repository evidence confidence and Controller exit authority.

## What Changes

- Require final-confidence aggregation to expose a terminal-return evidence row when the claim scope includes formal FlowPilot exit or Controller shutdown.
- Treat `final-preflight.allowed=false`, non-`terminal_return` foreground duty, `controller_stop_allowed=false`, and `open_startup_intake` as blockers for exit-authority claims.
- Keep existing control-plane live audit semantics intact; live audit can prove current-run health but cannot by itself authorize Controller exit.
- Add tests and TestMesh mapping so fake-AI/release evidence cannot hide a missing terminal-return preflight.

## Capabilities

### New Capabilities

- `terminal-return-final-confidence`: Final-confidence evidence for formal FlowPilot exit claims, binding release evidence to `flowpilot_new.py final-preflight` terminal-return authority.

### Modified Capabilities

- `tiered-flowpilot-test-validation`: The `final-confidence` tier must fail closed for formal exit claims unless terminal-return preflight evidence is current and passing.

## Impact

- Affected simulations: `flowpilot_final_confidence_gate`, acceptance TestMesh release evidence, and related result artifacts.
- Affected tests: final-confidence unit tests, test-tier contract tests, acceptance TestMesh tests, and fake-AI package rehearsal assertions if needed.
- Affected process: release/final-confidence reports must state whether they prove repository confidence only or formal FlowPilot exit authority.
