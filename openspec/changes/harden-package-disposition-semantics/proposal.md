## Why

Live FlowPilot evidence showed that two different PM package-result dispositions could be recorded for the same material-scan batch/generation when their sealed role-output bodies differed. Existing tests and models treated `body_hash` as part of the event identity, so they verified mechanical role-output uniqueness while missing the semantic rule that one batch/generation has exactly one authoritative PM package disposition.

## What Changes

- Add a shared PM package disposition semantic contract for material-scan, research, and current-node result packages.
- Make batch identity, packet membership, and packet generation the event identity; keep body hash as conflict evidence, not as a way to create a second ordinary disposition.
- Require one authoritative PM package disposition per batch/generation, with per-packet outcomes for worker-specific acceptance, rework, blocking, cancellation, or route/node mutation.
- Reject conflicting second ordinary dispositions for the same package identity unless a later authorized repair/reissue path creates a new batch/generation.
- Extend FlowGuard/event-idempotency and control-plane friction checks so synthetic packages, fake AI tests, and live replay audits catch same-class duplicates.
- Refresh role-output contracts and PM-facing runtime cards so the intended workflow is encoded where PM decisions are produced.

## Capabilities

### New Capabilities
- `pm-package-disposition-semantics`: Defines the shared semantic identity, conflict policy, and per-packet outcome contract for PM package-result dispositions across material, research, and current-node packages.

### Modified Capabilities
- `partial-batch-accounting`: Batch member state must expose per-packet PM outcomes and prevent aggregate advancement when any blocking packet outcome is unresolved or rework/blocking.
- `router-external-wait-reconciliation`: Idempotent replay may close stale waits only for the same semantic package disposition; conflicting package bodies for the same batch/generation must block rather than silently replay.

## Impact

- Runtime protocol files under `skills/flowpilot/assets/` for scoped event identity, replay conflict checks, PM package disposition writing, work-contract payloads, and runtime contract registry entries.
- PM-facing cards/prompts under `skills/flowpilot/assets/runtime_kit/`.
- FlowGuard simulations and source audits for event idempotency, control-plane friction, meta/capability coverage, and model-test alignment.
- Router/runtime tests for material-scan, research, and current-node package result disposition behavior.
- Local installed FlowPilot skill sync after validation through `scripts/install_flowpilot.py --sync-repo-owned --json`, local install audit, and install check.
