## 1. Model And Contract

- [x] 1.1 Add FlowGuard hazards for fresh dead-owner write locks, writer death while holding a lock, stop during startup scheduling, and false recovery that does not rejoin active or terminal flow.
- [x] 1.2 Add FlowGuard safe paths proving live-writer contention defers, dead-owner takeover rejoins normal daemon replay, and terminal stop stays terminal.
- [x] 1.3 Validate the focused persistent-daemon FlowGuard checks before relying on runtime tests.

## 2. Runtime Lock Handling

- [x] 2.1 Refactor runtime JSON write-lock classification into one helper that uses owner liveness as well as lock age.
- [x] 2.2 Make fresh dead-owner locks immediately replaceable and record durable takeover diagnostics.
- [x] 2.3 Make live or uncertain write-lock contention raise a daemon-deferrable condition instead of a generic fatal Router error.

## 3. Terminal Fence

- [x] 3.1 Add a stop/cancel terminal fence helper that writes terminal daemon status, terminal daemon lock projection, and terminal runtime projections immediately.
- [x] 3.2 Invoke the terminal fence from user stop/cancel lifecycle request handling before returning to the caller.
- [x] 3.3 Cancel or supersede pending nonterminal Controller/startup rows while preserving terminal cleanup actions.

## 4. Background Entry Guards

- [x] 4.1 Guard Router daemon ticks so terminal lifecycle returns terminal status without scheduling active work.
- [x] 4.2 Guard startup daemon scheduler entry points so stopped runs cannot append startup rows.
- [x] 4.3 Guard heartbeat binding creation and related startup actions against terminal lifecycle.

## 5. Runtime Tests

- [x] 5.1 Add tests for fresh dead-owner write-lock takeover and live/uncertain writer deferral.
- [x] 5.2 Add tests proving daemon does not exit fatally on deferrable write-lock contention.
- [x] 5.3 Add tests proving user stop immediately marks daemon lock/status terminal and clears active daemon mode.
- [x] 5.4 Add tests proving stop during startup scheduling does not create startup rows or heartbeat binding actions.
- [x] 5.5 Add tests proving terminal projections agree and stale nonterminal next-step text is not active.

## 6. Verification And Sync

- [x] 6.1 Run focused FlowGuard daemon checks and targeted router runtime tests.
- [x] 6.2 Run router/release tier checks with background artifacts and inspect final status.
- [x] 6.3 Run Meta and Capability FlowGuard checks or record any concrete blocker.
- [x] 6.4 Synchronize the installed local FlowPilot skill and verify install freshness.
- [x] 6.5 Update maintenance notes/changelog if the user-visible behavior contract changed.
- [x] 6.6 Commit the local repository changes without push, tag, or release publication.
