# Design

## Candidate Selection

FlowGuard surfaced several issue groups. The safe first repair is
`flowpilot_process_liveness` parseability because:

- it is deterministic and local to coverage evidence plumbing;
- the underlying model runner already returns valid JSON with `--json`;
- it does not require touching current run state;
- it improves later diagnostics by removing a false unparsed bucket.

The not-OK live/current-state findings remain visible and require separate
Model-Miss or runtime-state repair rounds.

## Implementation

Extend the coverage sweep argument detection so a compatibility facade can
inherit supported compact-output flags from its `_runner_impl` module. When the
implementation supports `--json`, the sweep should pass it. When it supports
`--no-write-results`, the sweep should pass that too, preserving the sweep's
read-only contract.

## Validation

Run:

- focused direct invocation for `flowpilot_process_liveness`;
- coverage sweep and full inventory rebuild;
- ordinary focused coverage-gap and inventory tests;
- OpenSpec strict validation;
- local install freshness audit/check.
