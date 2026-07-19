# Model-Miss Review: Startup Single-Invocation Retry

## Observed discrepancy

After transient Windows lock acquisition correctly entered foreground
settlement, the two-owner shadow/historical load still left multiple Router
daemons alive. The exact survivor commands pointed to different run roots.
Inspection of the temporary project showed that one public `start` command had
allocated three fresh runs. The foreground settlement wrapper was retrying the
whole `run_until_wait(..., new_invocation=True)` operation after the first run
and daemon already existed.

Once allocation was separated from advancement, a second discrepancy became
visible: the resumed retry reached the correct wait boundary but returned an
empty `folded_applied_actions` list, losing evidence for actions completed
before contention.

The first strict MTA rerun then exercised that exception path directly and
found a third implementation miss: `run_until_wait` referenced
`RouterLedgerWriteInProgress` in its preservation handlers without importing
the exception in that split module. The former wrapper-only test could not
enter this branch, so the code looked covered while the real owner path would
raise `NameError`.

## Ownership decision

- The existing public `start`, bootstrap state, current pointer, runtime writer
  settlement, and daemon event log remain the only owners.
- Fresh-run allocation happens once before advancement. Writer retries resume
  the persisted bootstrap with `new_invocation=False`.
- A live exact current-run startup-daemon identity is reattached from the
  existing daemon event log; multiple live identities block.
- Completed actions from an interrupted fold are carried into the final
  command receipt.
- No invocation ledger, alternate launcher, compatibility field, inferred
  old-run reader, or fallback path is introduced.

## Current-contract repair

The `start` command now persists one bootstrap under the existing bounded
writer settlement before running safe startup advancement. Later settlement
retries reuse that bootstrap. `run_until_wait` attaches only successfully
completed folded actions to writer-contention exceptions, and the existing
settlement owner prepends them to the final result. The daemon startup owner
reattaches one exact live in-flight process and rejects multiplicity.

## Backfeed and evidence

- The daemon reconciliation FlowGuard model now rejects more than one run
  allocation and loss of completed folded-action evidence.
- MTA binds the `start` allocation boundary, retry evidence, exact in-flight
  daemon authority, and installed shadow replay to the existing startup
  writer-settlement obligation.
- Focused tests cover in-flight daemon reattachment and folded-action receipt
  preservation both inside `run_until_wait` and across foreground settlement.
- The direct `run_until_wait` regression proves the imported current exception
  type is caught and carries only successfully completed actions.
- The installed shadow replay asserts one run directory for one start command.
- Two consecutive two-owner background probes passed with current source
  fingerprints and descendant-zero terminal receipts.
