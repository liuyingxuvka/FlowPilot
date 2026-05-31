## 1. Specification and Model

- [x] 1.1 Add OpenSpec requirements for generic role handoff and formal current packet open.
- [x] 1.2 Add a focused FlowGuard model/check for role packet access.
- [x] 1.3 Register the missing handoff/body exposure failure as known-friction evidence.

## 2. Runtime Implementation

- [x] 2.1 Add a runtime-generated handoff helper covering all packet responsibilities.
- [x] 2.2 Add `flowpilot_new.py role-handoff`.
- [x] 2.3 Add `flowpilot_new.py open-packet`.
- [x] 2.4 Harden the lower-level packet opener checks and audit event.
- [x] 2.5 Return safe handoff text from `lease-agent`.

## 3. Prompt and Card Surfaces

- [x] 3.1 Update FlowPilot skill launcher guidance to use generated handoff and formal open command.
- [x] 3.2 Update role cards and packet identity prompt to tell roles to use `open-packet` after ACK.
- [x] 3.3 Preserve sealed-body non-disclosure and Controller body-read prohibition.

## 4. Tests, Regression, and Sync

- [x] 4.1 Add core runtime tests for safe opens and rejection cases.
- [x] 4.2 Add card/instruction coverage tests for all background roles.
- [x] 4.3 Run targeted FlowGuard/model checks and focused unit tests.
- [x] 4.4 Validate OpenSpec artifacts.
- [x] 4.5 Rebuild/check topology when required.
- [x] 4.6 Sync the repository-owned skill to the local installed skill and run install audit/check.
- [x] 4.7 Commit the local repository changes without reverting unrelated peer work.
