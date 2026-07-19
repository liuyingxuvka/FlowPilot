# Model-Miss Review: Background Child Settlement Window

## Observed discrepancy

The same-fingerprint `all` tier ran
`shadow_launcher_shadow_start_tests`. The selected pytest case passed, the
installed launcher reached the expected releasable state, and its own daemon
stop proved descendant zero. The outer tier owner nevertheless marked the
command failed because three exact Windows descendants were still completing
normal process teardown after the fixed two-second settlement window.

## Ownership decision

- The installed launcher and daemon cleanup contract remained correct.
- The failure belonged to the background test owner: its bounded natural-exit
  settlement window was shorter than a real current launcher teardown.
- The descendant-zero invariant remains hard. A process that survives the
  bounded window is terminated and the child receipt remains failed.
- No fallback result, alternate success path, compatibility reader, missing
  cleanup default, or second process ledger was added.

## Current-contract repair

The existing settlement window is fifteen seconds. The existing positive
regression now keeps an exact descendant alive for eight seconds, so the test
would fail under the former five-second window. The existing negative regression
keeps an exact descendant alive for thirty seconds and still requires a failed
receipt plus confirmed termination.

## Backfeed

- The owning TestMesh model still requires bounded natural settlement and
  rejects surviving descendants.
- The current CodeContract and test-evidence family remain unchanged because
  the correction stays inside their already declared boundary.
- The failed broad root was preserved as non-reusable evidence after the exact
  supervisor tree was terminated and descendant zero was confirmed.
- Focused validation covers the longer positive, the surviving-orphan
  negative, predating-PID rejection, and the formerly failing installed
  launcher case through the real background child owner.
