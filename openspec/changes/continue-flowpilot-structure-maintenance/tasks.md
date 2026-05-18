## 1. Preflight And Target Selection

- [x] 1.1 Run predictive KB preflight and verify real FlowGuard is importable.
- [x] 1.2 Inspect git status, OpenSpec state, and repository coordination instructions.
- [x] 1.3 Delegate read-only target analysis for model runners, runtime owner modules, and test/script helper risks.
- [x] 1.4 Select only clean low-conflict targets for this batch.

## 2. Model-Test Alignment Runner Split

- [x] 2.1 Split common constants and helper builders out of `run_flowpilot_model_test_alignment_checks.py`.
- [x] 2.2 Split family alignment plans, source-contract plans, and known-bad cases into focused modules.
- [x] 2.3 Split full diagnostic surface inventory/background evidence logic into focused modules.
- [x] 2.4 Keep the original runner as a compatibility facade exposing the same public functions and CLI.

## 3. Declarative Runtime Table Splits

- [x] 3.1 Split `flowpilot_router_facade_export_manifest_controller.py` into controller manifest child shards while preserving `OWNER_EXPORTS_CONTROLLER` and `owner_exports_controller()`.
- [x] 3.2 Split `flowpilot_router_protocol_external_events.py` into event table child shards while preserving `EXTERNAL_EVENTS` and `external_event_contract()`.
- [x] 3.3 Update diagnostic split metadata to mark completed public-entrypoint reductions and keep remaining child debt explicit.

## 4. Validation And Diagnostics

- [x] 4.1 Run focused compile checks for touched modules.
- [x] 4.2 Run focused unit tests for model-test alignment and runtime declarative contract coverage.
- [x] 4.3 Regenerate full model-test-code diagnostic results.
- [x] 4.4 Run StructureMesh maintenance and test tier checks required for the touched boundaries.
- [x] 4.5 Run Meta/Capability fast full checks or equivalent final release-confidence checks if evidence changed.

## 5. Sync, Documentation, And Local Commit

- [x] 5.1 Update diagnostic documentation and FlowGuard adoption log with exact commands and remaining debt.
- [x] 5.2 Sync the repo-owned local FlowPilot skill and audit installed freshness.
- [x] 5.3 Run OpenSpec strict validation for this change.
- [x] 5.4 Run KB postflight and record reusable lessons if this pass exposes one.
- [x] 5.5 Stage only scoped changes and create a local git commit; do not push, tag, or publish.
