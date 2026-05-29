## Why

FlowPilot already keeps model obligations and ordinary tests aligned, but the
current alignment result can still be green without showing the concrete runtime
path that matched each model obligation. That makes maintenance harder when real
code, tests, and FlowGuard models drift in different directions.

## What Changes

- Add FlowGuard runtime-path evidence to each major FlowPilot model-test family.
- Require every family plan to emit parseable progress lines that name the
  compared FlowGuard model, node, obligation, source evidence, and run id.
- Bind every model obligation to a required runtime node so missing runtime-path
  evidence blocks model-test alignment.
- Add known-bad coverage proving FlowGuard rejects missing runtime-path evidence.
- Keep the runtime-path layer as evidence and diagnostics; it does not replace
  ordinary tests, source-contract audits, or parent/child model checks.

## Impact

- Affected areas include FlowPilot runtime evidence helpers, model-test
  alignment plans and reports, known-bad alignment checks, focused unit tests,
  OpenSpec validation, local FlowGuard adoption records, and installed skill sync.
- No GitHub push, tag, release, deploy, destructive runtime-data cleanup, or
  broad router rewrite is in scope for this maintenance pass.
