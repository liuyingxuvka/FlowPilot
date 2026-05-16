## 1. Model

- [x] 1.1 Add FlowGuard hazards for invalid Router scheduler ledger JSON.
- [x] 1.2 Add FlowGuard hazards for invalid Controller action ledger JSON.
- [x] 1.3 Add FlowGuard hazards for non-atomic ledger writes, scheduler
      multi-writer access, and daemon status/lock/process mismatch.
- [x] 1.4 Run focused FlowGuard scheduler and persistent daemon checks.
- [x] 1.5 Add FlowGuard coverage for fresh write-lock waits versus stale/no-lock
      ledger corruption.

## 2. Minimal Runtime Repair Plan

- [x] 2.1 Inventory all runtime writes to `router_scheduler_ledger.json`,
      `controller_action_ledger.json`, daemon status, and daemon lock.
- [x] 2.2 Introduce one atomic JSON write helper for daemon-critical runtime
      ledgers and migrate these writes through it.
- [x] 2.3 Enforce Router-only scheduler ledger mutation and prevent foreground
      paths from writing scheduler rows while daemon owns startup/runtime.
- [x] 2.4 Make daemon status live only when lock, freshness, and process
      evidence agree; error locks must override active status.
- [x] 2.5 Add corrupted-ledger recovery behavior that blocks scheduling and
      exposes repair evidence instead of crashing silently.
- [x] 2.6 Treat fresh runtime JSON write locks as transient wait states instead
      of daemon corruption errors.

## 3. Validation

- [x] 3.1 Add runtime tests for repeated scheduler writes staying valid JSON.
- [x] 3.2 Add runtime tests for corrupted scheduler ledger recovery.
- [x] 3.3 Add runtime tests for daemon status after lock error and missing PID.
- [x] 3.4 Run focused FlowGuard checks, targeted runtime tests, install sync,
      and install audit. Skip heavyweight meta/capability regressions unless
      separately requested.
- [x] 3.5 Add runtime test coverage for fresh write-lock wait/retry behavior
      and rerun focused validation.
