## 1. Contracts And Model

- [x] 1.1 Add OpenSpec requirements for declared outcome authority and current-effective blocker projection.
- [x] 1.2 Extend FlowGuard semantic outcome modeling for prose overread, current blocker filtering, repair-chain clear, and final-ledger effective packets.

## 2. Runtime Implementation

- [x] 2.1 Replace whole-body non-pass text scanning with structured-field and declaration-line parsing.
- [x] 2.2 Add current-effective blocker and packet helpers for routing, status projection, final route-wide ledgers, and closure.
- [x] 2.3 Clear same-gate repair blocker chains from current passes and mark repaired blocked packets as non-current history.

## 3. Tests And Validation

- [x] 3.1 Add tests for declared pass with failure wording and declared block behavior.
- [x] 3.2 Add tests for stale accepted-node blockers not projecting as current.
- [x] 3.3 Add tests for final route-wide ledgers ignoring historical blocked packets while still blocking current unresolved packets.
- [x] 3.4 Run OpenSpec strict validation, FlowGuard semantic outcome checks, py_compile, and targeted pytest for this change.
- [x] 3.5 Run repo-owned install sync and local install digest audit.
- [x] 3.6 Run background meta and capability thin-parent checks and inspect exit artifacts.
- [x] 3.7 Clear the full install self-check.
- [x] 3.8 Clear the broad fast tier.

## 4. Repository Sync

- [x] 4.1 Sync the repo-owned FlowPilot skill into the local installed version.
- [x] 4.2 Review git status and commit only scoped files for this change.
