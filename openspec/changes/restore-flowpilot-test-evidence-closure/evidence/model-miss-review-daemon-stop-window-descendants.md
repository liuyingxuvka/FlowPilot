# Model-Miss Review: Daemon Stop-Window Descendants

## Observed discrepancy

The installed shadow-launcher pytest case passed and reported daemon cleanup,
but its outer exact-process owner still found one Router-daemon process tree
alive after the bounded settlement window under full-tier load. The former
daemon stop path captured descendants only before it requested the daemon to
stop. A descendant appearing during the wait-to-exit window was therefore
absent from the cleanup set even though the lock could be released.

## Ownership decision

- The test-tier settlement duration remains fifteen seconds.
- The installed-launcher test, PM/Reviewer workflow, and external FlowGuard
  version are not owners of this defect.
- The defect belongs to the existing `stop_router_daemon` exact-tree cleanup
  stage.
- The failed full-tier owner and every observed descendant were terminated
  with descendant-zero confirmation; its evidence root remains non-reusable.

## Current-contract repair

The existing stop path now accumulates exact descendant identities throughout
the bounded stop wait. After the owner exits or is terminated, every still-live
identity in that accumulated set is cleaned and rechecked before the daemon
lock can be released. A late child therefore stays inside the same stop
transaction instead of becoming an unowned process.

No new daemon, alternate stop path, retry loop, or compatibility behavior is
introduced.

## Backfeed

- The daemon descendant-zero MTA obligation now explicitly covers the whole
  stop window.
- A dedicated edge test creates a descendant after the initial snapshot and
  proves the lock remains unreleasable until that exact child is cleaned.
- The BCL failure boundary now names an untracked stop-window descendant as a
  blocking condition.

## Later root-cause refinement

After failure receipts began recording survivor command lines, the repeated
high-load incident showed that `start` had failed earlier on
`startup_state.json.write.lock` permission contention. The test therefore
never entered its cleanup `try/finally`; the daemon survivor in that incident
was a consequence of startup failure, not proof that the stop transaction had
returned a false green. The stop-window accumulation remains valid defensive
hardening with its own edge test, while the primary incident is owned by
`model-miss-review-startup-write-lock-permission.md`.
