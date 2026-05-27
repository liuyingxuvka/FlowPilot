# Repair FlowGuard Exposed Issues

## Summary

Fix the safest current FlowGuard-exposed issue first: the coverage sweep marks
`flowpilot_process_liveness` as unparsed even though the underlying runner can
emit compact JSON.

## Motivation

The full test-gap closure pass made missing coverage visible. The next repair
step should remove real false-negative inventory noise before touching live run
state or broader architecture. `flowpilot_process_liveness` is the safest
candidate because the failure is in runner invocation/coverage plumbing, not
business behavior.

## Scope

This change may update:

- the read-only coverage sweep runner invocation logic;
- ordinary tests that assert `flowpilot_process_liveness` is parseable;
- inventory results and reports;
- adoption logs and OpenSpec task records.

This change must not:

- mutate active `.flowpilot/runs/` state;
- weaken model invariants;
- convert not-OK live findings into pass evidence;
- push, tag, publish, or release.

## Success Criteria

- The coverage sweep invokes compatibility facades with compact JSON arguments
  when their implementation supports them.
- `flowpilot_process_liveness` is no longer classified as
  `runner_unparsed_or_unavailable`.
- Focused inventory/tests pass.
- Remaining not-OK/live/scoped findings stay visible.
- Local FlowPilot install freshness is checked after the repair.
