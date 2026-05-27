## 1. FlowGuard Bad-Case Modeling

- [x] 1.1 Extend the controller receipt evidence fold model with `receipt_done_without_controller_relay_signature` and require it to fail until runtime relay evidence exists.
- [x] 1.2 Extend packet-open authority/lifecycle coverage so path-only handoff cannot authorize Worker open.

## 2. Runtime Relay Surface

- [x] 2.1 Add a unified Controller-facing `flowpilot_runtime.py` relay command that delegates to existing packet runtime relay helpers without reading sealed bodies.
- [x] 2.2 Return compact machine-checkable JSON evidence from the command, including packet id, target role, envelope path, relay status, ledger holder/status, and lease evidence when applicable.

## 3. Router Relay Actions and Receipts

- [x] 3.1 Add structured runtime relay operations to material, research, current-node, and PM role-work packet/result relay actions.
- [x] 3.2 Tighten receipt reconciliation so relay `done` receipts close only when runtime relay evidence and required active-holder lease evidence are verified.
- [x] 3.3 Route missing relay evidence on otherwise relayable envelopes to a Controller-owned mechanical repair/replay path before PM/control-blocker escalation.

## 4. Prompts and Role Cards

- [x] 4.1 Update the Controller action ledger prompt to state that packet/result relay rows require runtime relay before receipt.
- [x] 4.2 Update the Controller role card to define valid relay evidence and forbid path-only/chat-only relay completion for all packet/result relay rows.

## 5. Tests and Regressions

- [x] 5.1 Add focused runtime/router tests for path-only relay plus done receipt, successful runtime relay, and Controller mechanical repair routing.
- [x] 5.2 Run focused pytest suites for packet runtime, router packet/material receipt folding, controller prompt coverage, and blocker routing.
- [x] 5.3 Run relevant FlowGuard checks and model regressions, using background artifacts for long checks and inspecting exit/log files before claiming completion.

## 6. Sync and Finalization

- [x] 6.1 Sync the repo-owned FlowPilot skill into the local installed skill version.
- [x] 6.2 Run install sync/audit checks after sync, serialized after the sync step.
- [x] 6.3 Review git status and summarize changed files, verification evidence, and any remaining risk.
