## Why

The new FlowPilot foreground duty prevents passive foreground exit, but a live run showed that repeated short patrols can still classify a slow, working reviewer as replaceable. This corrupts packet lifecycle state when the original result arrives before or during replacement, because an already accepted packet can be reassigned to a new lease.

## What Changes

- Add a new-runtime liveness recovery ladder for packet waits: patrol first, remind/check liveness at wait-class thresholds, grace-wait when the role is still working, and replace only after current no-output or inactive evidence.
- Block packet assignment and ACK state regression after a packet has an accepted result.
- Expose a small public progress command backed by the existing runtime progress ledger so live roles can report "still working" without completing the packet.
- Add a current-run repair path for the observed accepted-result/reassigned-lease race.
- Extend FlowGuard models, fake AI rehearsals, and focused tests for slow live roles, progress-preserved waits, accepted-packet reassignment, late original result races, and replacement-only-after-current liveness failure.
- Sync the installed local `flowpilot` skill after validation.

## Capabilities

### New Capabilities

- `new-flowpilot-liveness-recovery`: New-runtime packet wait, progress, liveness, replacement, and accepted-packet race recovery rules.

### Modified Capabilities

- `runtime-ledger-persistence`: Persist progress, liveness recovery decisions, and repair/supersession records from the current ledger without stale state regression.
- `multiround-fake-ai-control-rehearsal`: Rehearse slow-but-working AI packets and replacement races, not only fast happy paths and immediate dead-lease cases.
- `known-friction-regression-gates`: Treat the observed reviewer replacement race as a required regression family before claiming the fix is complete.

## Impact

- Runtime: `skills/flowpilot/assets/ai_project_runtime/runtime.py`
- Entrypoint: `skills/flowpilot/assets/flowpilot_new.py`
- Current run repair: `.flowpilot/runs/run-20260530-102304/`
- Models and rehearsals: lifecycle guard, fake project rehearsal, model-test alignment, and relevant result artifacts.
- Tests: focused runtime/entrypoint/lifecycle guard tests plus public fake AI rehearsal.
- Install sync: local installed `flowpilot` skill under the active Codex skills directory.
