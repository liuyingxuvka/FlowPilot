# Model-Miss Review: Startup Write-Lock Permission Contention

## Observed discrepancy

Under the same two-owner load as the all tier, the installed shadow launcher's
`start` command failed with `PermissionError` while acquiring
`startup_state.json.write.lock`. The foreground startup fold and the newly
started Router daemon were writing current startup state concurrently. The
existing foreground settlement path handled an explicit
`RouterLedgerWriteInProgress`, but raw Windows permission denial from the
exclusive lock acquisition escaped before it could enter that settlement.

Because `start` failed before the test reached its cleanup `try/finally`, the
newly opened daemon remained live. The outer background owner then correctly
failed and terminated it. That surviving daemon was a consequence, not the
primary defect.

## Ownership decision

- The single current `start` path and existing runtime JSON lock remain the
  only owners.
- The repair belongs to `_acquire_json_write_lock`; no new startup path,
  alternate ledger, retry service, or compatibility behavior is introduced.
- Windows permission denial while taking this exact current lock is classified
  as writer contention inside the existing bounded settlement budget.
- Persistent permission denial still raises `RouterLedgerWriteInProgress` and
  fails closed.

## Current-contract repair

The exclusive lock acquisition now retries a transient `PermissionError`
within its existing bounded writer budget. If the permission condition does
not clear, it emits the current lock-liveness evidence and raises the same
structured writer-contention exception consumed by foreground and daemon
owners.

## Backfeed

- MTA's startup writer-settlement obligation now includes lock-acquire
  permission contention.
- One edge test proves a single transient denial settles to the same write
  path; one negative test proves persistent denial remains blocking.
- The high-load shadow/historical pair is the owning runtime regression for
  the originally observed failure.

## Later retry-boundary refinement

After permission acquisition entered the bounded settlement path, the same
high-load pair exposed a second defect: the generic foreground wrapper retried
the whole `start` operation. Each retry therefore requested a new invocation,
allocated a new run, and opened another daemon. Once run allocation was made
single-owner, the final retry also returned an empty folded-action list because
earlier successfully applied actions were not carried into the command
receipt.

Those are separate model misses owned by the current `start` and writer
settlement path. Their repair is recorded in
`model-miss-review-startup-single-invocation-retry.md`.
