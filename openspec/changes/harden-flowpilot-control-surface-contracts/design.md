## Context

The new FlowPilot runtime intentionally keeps the shell thin: `.flowpilot`
points to one current run, the current-run ledger owns authority, packets and
results are sealed, and foreground duty asks only for the next boundary.

The remaining miss happened below normal route logic. Some tools still expected
old current-pointer field names; one live audit crashed on a non-UTF-8 JSON file
instead of reporting unreadable evidence; and packet symmetry must be enforced
at the shared envelope boundary so a PM fix also protects reviewer, FlowGuard,
requested worker packets plus system validation and system closure outcomes.

## Decisions

### Decision: Use one current-run resolver

Runtime and audits will resolve current run through a shared helper. It accepts
these pointer shapes:

- `run_id` plus `run_root`
- `current_run_id` plus `current_run_root`
- `active_run_id` plus `active_run_root`
- `run_id` with an implied `.flowpilot/runs/<run_id>` root only when the root
  exists

It must not silently fall back to the project root or newest run directory. If
the pointer is missing or ambiguous, the caller receives a structured reason.

### Decision: Evidence reads are findings, not crashes

Read helpers return a small result object with `ok`, `value`, `error_code`, and
`message`. Missing files, invalid JSON, and invalid UTF-8 are ordinary audit
findings. Production command paths can still convert a failed required read to a
runtime error, but audit paths must keep going when possible.

### Decision: Symmetric packet contract check is role-neutral

Every current-run packet is checked with the same fields regardless of
responsibility:

- packet id, kind, responsibility, route version, source generation
- sealed body hash and body visibility
- explicit expected output authority
- separate ACK, result, and accepted-result states
- accepted packets cannot be reassigned or ACK-regressed
- result generation must match the current source generation unless explicitly
  quarantined

This is not a new heavy router. It is a small invariant checker over the
existing ledger.

### Decision: FlowGuard models the missed entrance layer

The model explicitly includes hazards for:

- ignoring the new current pointer schema
- falling back to project root/newest run after pointer failure
- crashing on non-UTF-8 audit evidence
- PM-only packet contract coverage
- ACK treated as result completion
- accepted packet reassignment
- old-generation result accepted as current evidence

These hazards explain why previous route-flow tests could pass while the
control surface remained weak.

## Validation

Focused validation must include:

- FlowGuard control-surface model and hazard checks
- unit tests for resolver schemas, safe reads, and packet contract symmetry
- live audit smoke that current-run resolution does not scan the wrong root and
  unreadable JSON becomes a finding
- focused new-runtime tests and install sync checks after source changes
