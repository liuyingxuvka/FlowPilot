## 1. Model And Contract

- [x] 1.1 Record OpenSpec requirements for self-owned stale write-lock recovery.
- [x] 1.2 Update the persistent daemon FlowGuard model with self-owned stale
  lock hazards and safe recovery obligations.

## 2. Runtime Implementation

- [x] 2.1 Keep normal same-call lock cleanup simple, bounded, and diagnostic.
- [x] 2.2 Add safe self-owned stale lock classification and takeover in runtime
  JSON write-lock acquisition.
- [x] 2.3 Preserve other-live-owner waiting and unsafe self-owned lock blocking.

## 3. Tests And Validation

- [x] 3.1 Add focused runtime tests for self-owned stale takeover, fresh self
  lock deferral, unsafe temp artifact blocking, and cleanup failure logging.
- [x] 3.2 Run focused tests and FlowGuard checks, with heavyweight regressions
  in background where practical.
- [x] 3.3 Sync the repo-owned FlowPilot skill to the local installed skill and
  run install/audit checks.
- [x] 3.4 Commit only this scoped fix and leave unrelated peer-agent changes
  untouched.
