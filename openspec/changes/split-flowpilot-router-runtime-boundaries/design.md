## Context

The router was originally documented as a deliberately small prompt-isolated
entrypoint. It now has more than 37k lines and combines several independent
control-plane responsibilities. The current public surface is still centered on
`flowpilot_router.py`: CLI commands, tests, install checks, runtime cards, and
some FlowGuard models refer to that filename directly.

The existing behavior is valuable and model-backed. The refactor must therefore
be a compatibility-preserving extraction, not a rewrite. The router remains the
public facade while new modules take ownership of narrower boundaries.

## Goals / Non-Goals

**Goals:**

- Make each extracted boundary readable and testable in isolation.
- Preserve CLI commands, runtime schemas, JSON artifact formats, and public
  imports through `flowpilot_router.py`.
- Keep ACK settlement separate from semantic work completion.
- Keep Controller, PM, Reviewer, officer, and worker authority boundaries
  unchanged.
- Maintain install freshness and FlowGuard evidence as completion gates.

**Non-Goals:**

- Do not redesign multi-node routing, packet schemas, or terminal closure
  behavior in this change.
- Do not collapse existing OpenSpec specs or FlowGuard models.
- Do not delete the legacy preserved backup.
- Do not treat moving code as permission to weaken invariants or tests.

## Decisions

- Keep `flowpilot_router.py` as the facade.
  - Alternative rejected: rename the public entrypoint immediately. Runtime
    cards, tests, install checks, and user instructions still point to that
    file, so a rename would create avoidable migration risk.

- Extract from lowest-risk to highest-risk boundaries.
  - First: constants, paths, JSON helpers.
  - Second: Controller ledger and card return settlement.
  - Later: packet/mail orchestration, startup/daemon, gate/terminal helpers.
  - Alternative rejected: one large split. The router carries many protocol
    invariants and a broad diff would make regressions hard to isolate.

- Preserve compatibility re-exports while tests migrate.
  - New modules own implementations, but `flowpilot_router.py` may re-export
    constants and helper functions during the transition so existing tests and
    scripts keep working.

- Validate every phase with focused checks before broad checks.
  - Focused checks catch seam regressions quickly. Meta and Capability checks
    still run before completion, preferably through the established background
    artifact contract.

- Keep backup evidence outside the runtime path.
  - A local `tmp/router_split_backup_*` snapshot records the pre-split router
    and test file. It is not imported, installed, or used as runtime fallback.

## Risks / Trade-offs

- [Risk] Moving helpers changes import-time side effects or constant identity.
  -> Mitigation: preserve facade exports and run import, compile, install, and
  focused tests after each extraction phase.

- [Risk] ACK settlement extraction accidentally frees output-bearing work.
  -> Mitigation: keep ACK wait settlement and work-output completion as
  separate model/test obligations.

- [Risk] Controller ledger extraction hides passive waits or creates ordinary
  work rows for pure waits.
  -> Mitigation: run controller-action-queue, dispatch-recipient, and
  scheduler-focused tests after the extraction.

- [Risk] The broad meta/capability models are expensive.
  -> Mitigation: launch them in the background using the repository's
  `tmp/flowguard_background/` artifact contract and inspect completion files
  before reporting them as passed.

- [Risk] Local installed skill freshness checks can be confused by cache files.
  -> Mitigation: use the repository install sync/audit commands and clear
  caches if freshness comparison reports cache-tainted differences.

## Migration Plan

1. Start from the completed ACK/busy-state repair baseline.
2. Keep a local non-runtime backup snapshot.
3. Extract one boundary at a time, preserving facade compatibility.
4. Move focused tests only after the corresponding implementation boundary is
   stable.
5. Run focused tests and FlowGuard checks after each risky boundary.
6. Run broad regressions, install sync, and install freshness audit before
   marking the OpenSpec tasks complete.
7. Leave future feature work, such as full multi-node traversal expansion, to a
   separate OpenSpec change.

## Open Questions

- None that block implementation. If an extraction seam requires behavior
  changes rather than pure movement, stop and add a new OpenSpec requirement
  before continuing.
