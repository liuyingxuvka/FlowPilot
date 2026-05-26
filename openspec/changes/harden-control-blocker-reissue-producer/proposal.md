## Why

A real FlowPilot run exposed a control-plane miss: worker material-scan results failed their own contract self-checks, PM correctly requested rework, but a `role_reissue` repair decision was accepted as a wait for `worker_scan_results_returned` without issuing any fresh worker work. FlowPilot must not enter a nonterminal wait unless the awaited event has a concrete producer.

## What Changes

- Tighten control-blocker repair decisions so `role_reissue` is executable only when it creates or references a real role work producer for the awaited event.
- Require material-scan rework after failed worker result self-checks to use a concrete `packet_reissue`, replayable operation, bounded work packet, or explicit blocker/terminal decision.
- Extend wait reconciliation evidence so control-blocker follow-up waits can prove the awaited event is producible, not merely valid by name.
- Add FlowGuard model-miss coverage and runtime regression tests for the observed bad case and a generalized same-class empty-wait case.

## Capabilities

### New Capabilities

- None. This change hardens existing FlowPilot control-plane capabilities.

### Modified Capabilities

- `executable-repair-transactions`: Repair transactions that wait for a role-produced event must prove a concrete producer before commit.
- `blocker-repair-policy`: PM same-gate repair guidance must distinguish packet reissue or operation replay from open-ended role reissue.
- `router-external-wait-reconciliation`: Follow-up waits after a repair decision must retain producer evidence and reject empty waits.

## Impact

- Affected runtime assets: control-blocker repair decision validation, repair transaction execution planning, control-blocker wait action creation, and material rework paths.
- Affected FlowGuard models: process liveness, executable repair transaction/model-miss evidence, and model-test alignment obligations for empty waits.
- Affected tests: focused router runtime control-blocker/material packet tests and output contract/self-check regression tests.
- Local installation sync is required after validation because this repository implements the installed `flowpilot` skill.
