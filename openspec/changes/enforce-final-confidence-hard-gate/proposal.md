## Why

FlowPilot already has FlowGuard models, defect-family gates, Risk Evidence Ledger helpers, live-run audits, and rich fake-AI/runtime test matrices, but local green checks can still be reported independently of the final confidence boundary. This change makes the final confidence claim fail closed whenever live evidence, full model-test coverage, defect-family proof, or evidence freshness is red, skipped, stale, scoped, or not run.

## What Changes

- Add a first-class final confidence hard gate that aggregates current FlowGuard/FlowPilot evidence into `full_confidence`, `scoped_confidence`, or `blocked`.
- Require the gate to treat skipped live audit, current live-audit failure, stale/progress-only background evidence, `full_coverage_ok=false`, and blocked/scoped Risk Evidence Ledger decisions as blocking evidence for broad confidence.
- Add executable tests for false-confidence cases where model checks pass but live audit or full coverage is missing.
- Add the hard gate to the test-tier surface so agents can run it explicitly instead of inferring final confidence from local green subchecks.
- Preserve existing runtime behavior and peer-agent changes; this change is an evidence/validation gate, not a router semantic rewrite.

## Capabilities

### New Capabilities
- `final-confidence-hard-gate`: Aggregates model, test, live-run, defect-family, and risk-ledger evidence into a single fail-closed final confidence decision.

### Modified Capabilities
- `tiered-flowpilot-test-validation`: Expose the final confidence gate as a named validation tier/command so skipped or scoped evidence remains visible before completion claims.

## Impact

- Affected scripts: new final confidence check under `simulations/`, test-tier definitions.
- Affected tests: new focused tests for gate aggregation and test-tier exposure.
- Affected OpenSpec artifacts: new final confidence hard-gate capability and a small tiered-validation delta.
- No remote publish, destructive cleanup, or rollback of peer work.
