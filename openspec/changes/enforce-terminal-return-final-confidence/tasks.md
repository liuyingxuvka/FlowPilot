## 1. Terminal-Return Evidence Gate

- [x] 1.1 Add a terminal-return evaluator that consumes `flowpilot_new.py final-preflight` output and fails closed unless `allowed=true`, `foreground_duty.action=terminal_return`, and `controller_stop_allowed=true`.
- [x] 1.2 Run terminal-return evidence by default from the final-confidence runner, with an explicit repository-only diagnostic opt-out.
- [x] 1.3 Preserve terminal-return blocker details, including nonterminal foreground duty and `open_startup_intake`, in final-confidence result JSON.

## 2. TestMesh And Tier Integration

- [x] 2.1 Update the final-confidence tier contract so its command includes terminal-return evidence by default.
- [x] 2.2 Update acceptance TestMesh release mapping so formal exit authority is visible as a release child requirement.
- [x] 2.3 Add unit coverage for passing terminal-return evidence, blocked startup-intake evidence, failed preflight subprocess evidence, and scoped repository-only diagnostics.
- [x] 2.4 Keep the read-only coverage sweep in explicit repository-only diagnostic mode while preserving strict terminal-return behavior in the dedicated final-confidence tier.

## 3. Validation And Sync

- [x] 3.1 Run OpenSpec strict validation for `enforce-terminal-return-final-confidence`.
- [x] 3.2 Run focused unit tests and model runners for final-confidence, acceptance TestMesh, fake-AI rehearsal, and test-tier contracts.
- [x] 3.3 Run topology build/check, install sync/audit/check, release/final-confidence evidence checks, FlowGuard adoption logging, and KB postflight.
