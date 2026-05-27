# Close FlowGuard Full Coverage Findings

## Summary

Close the current FlowPilot FlowGuard full-coverage findings in priority order:
red runner findings first, then scoped evidence accounting, then remaining
StructureMesh-owned split findings where they are safe to address.

## Motivation

The full coverage inventory now enumerates all runners, but the current report
still has live/source findings, scoped replay evidence, skipped evidence, and
deferred structure split findings. The next pass must turn those items into
either current green evidence or explicit blocked/safely deferred evidence
without mutating active run state unsafely or weakening FlowGuard invariants.

## Scope

This change may update:

- FlowGuard live/source audit helpers when they misread split facade code or
  current metadata-only evidence;
- FlowPilot production code when an exposed finding maps to a real future-run
  behavior bug;
- focused ordinary tests for those audit and runtime boundaries;
- coverage inventory logic when it overcounts non-blocking artifact choices as
  skipped evidence;
- generated coverage/alignment reports and adoption records.

This change may not:

- rewrite active `.flowpilot/runs/` state without a separate safe authority
  proof;
- hide current-run contradictions by marking skipped/stale evidence as passed;
- perform broad StructureMesh splits without focused ownership and parity
  tests;
- push, publish, tag, or release.

## Success Criteria

- The current red runner group is reduced by every issue that can be safely
  repaired from source/model code.
- Split-facade audits resolve contracts from the real owner modules, not only
  the small compatibility facade text.
- Future material-scan runtime state keeps router phase and frontier phase in
  sync.
- Metadata-only live projections recognize valid controller-relayed startup
  intake status.
- Non-blocking output-file choices are not counted as skipped evidence.
- Remaining items, if any, are explicitly classified as live-state authority
  blockers or StructureMesh/deferred scope instead of being reported as fixed.
