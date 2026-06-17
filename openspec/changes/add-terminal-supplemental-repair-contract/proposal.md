## Why

Terminal review can expose required work after the original FlowPilot contract
has already been frozen and the main route appears mostly complete. Today the
runtime can repair terminal replay blockers, but it has no explicit bounded
contract layer for PM-owned supplemental repair work that preserves the frozen
contract while still forcing high-standard gaps to close.

## What Changes

- Add a PM-authored Terminal Supplemental Repair Contract that layers on top of,
  but never edits, the original frozen contract.
- Require Reviewer terminal gap reports to produce structured repair gaps when
  final replay or final ledger review finds blocking missing work.
- Require PM to convert original-goal latent high-standard gaps, missing
  implementation, missing validation, weak evidence, or terminal route-structure
  gaps into supplemental repair items and repair nodes/subnodes.
- Route supplemental repair nodes through the same current FlowPilot gates as
  ordinary work: PM planning, FlowGuard process coverage, Reviewer plan review,
  Worker/FlowGuard/Reviewer execution evidence, final ledger, and terminal
  replay.
- Add a hard runtime cap of three supplemental repair rounds. After the third
  round, if terminal closure is still not clean, runtime stops with
  `repair_rounds_exhausted` instead of opening another Reviewer/PM repair loop.
- Keep all behavior current-contract only. No legacy fallback, original-contract
  mutation, free-form percentage completion gate, or second parallel workflow is
  introduced.

## Capabilities

### New Capabilities

- `flowpilot-terminal-supplemental-repair`: PM-owned terminal supplemental repair
  contracts, repair item projection, bounded repair rounds, and hard exhausted
  terminal stop behavior.

### Modified Capabilities

- `terminal-ledger`: terminal ledgers and terminal backward replay must include
  supplemental repair contract rows and targets before closure can pass.
- `flowpilot-closure-kernel`: final closure must require clean original-contract
  evidence plus clean active supplemental repair contracts, or hard-stop when
  repair rounds are exhausted.
- `route-repair-replacement-policy`: terminal supplemental repair nodes and
  subnodes must reuse the current route mutation/repair-node rules and must not
  bypass node acceptance planning.
- `hard-gate-coverage-matrix`: hard gate coverage must include the supplemental
  repair contract, repair item closure, and three-round cap obligations.

## Impact

- Runtime ledger and packet/result contract fields for terminal supplemental
  repair state, contracts, repair items, and exhausted disposition.
- PM, Reviewer, FlowGuard operator, and Controller runtime cards for terminal
  repair contract authorship, gap reporting, process review, and hard-stop
  behavior.
- Final route-wide ledger, final requirement evidence matrix, terminal backward
  replay targets, and final-preflight closure blockers.
- FlowGuard models, model-test alignment evidence, field lifecycle evidence,
  focused unit tests, fake E2E rehearsal, topology, install sync, and local
  installed skill audit.
