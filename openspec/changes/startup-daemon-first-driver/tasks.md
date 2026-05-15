## 1. FlowGuard

- [x] 1.1 Ensure the focused two-table async scheduler model accepts
      daemon-first startup driving.
- [x] 1.2 Ensure the model rejects startup UI, role startup, or heartbeat
      binding before daemon ownership, and rejects a pre-core daemon that only
      waits for Controller core.

## 2. Runtime

- [x] 2.1 Reorder startup so minimal run shell, current pointer, index, and
      Router daemon happen before startup UI, role startup, and heartbeat.
- [x] 2.2 Make the daemon schedule pre-Controller-core startup bootloader rows
      into the Controller action ledger and Router scheduler ledger.
- [x] 2.3 Prevent foreground Router calls from bypassing daemon-owned startup
      scheduling once the daemon is started.
- [x] 2.4 Mark daemon-scheduled bootloader rows complete/reconciled when their
      bootloader action succeeds.

## 3. Prompts And Docs

- [x] 3.1 Update FlowPilot skill/protocol text so startup uses the same
      two-table rule as later work.
- [x] 3.2 Update Controller-facing prompt cards so Controller reads startup
      rows top-to-bottom and checks them off without owning Router ordering.

## 4. Validation And Sync

- [x] 4.1 Add or update focused runtime tests for daemon-first startup
      ordering, daemon pre-core scheduling, and startup row reconciliation.
- [x] 4.2 Run focused FlowGuard checks and targeted tests while skipping
      heavyweight meta/capability regressions.
- [ ] 4.3 Sync the local installed FlowPilot skill and verify repo/install
      consistency.
