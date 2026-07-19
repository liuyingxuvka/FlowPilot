# Model-Miss Review: Background Toolchain Identity

## Observed discrepancy

The first release-tier attempt was launched by the frozen FlowGuard 0.58.0
environment, but the nested Meta and Capability commands retained a literal
`python`. On this Windows host that token resolved to the concurrently updated
default environment and FlowGuard 0.58.1. The commands had not produced
terminal reusable evidence when the drift was detected.

## Ownership decision

- The user-approved execution plan remains frozen to FlowGuard 0.58.0.
- The defect belonged to the existing background-command binding point, not to
  Meta, Capability, the product runtime, or a need for a compatibility route.
- The release supervisor and its exact descendants were terminated with
  descendant-zero confirmation. The partial root is preserved as non-reusable
  evidence.
- No later FlowGuard version is adopted and no automatic newest-version
  selection is permitted inside this release.

## Current-contract repair

The existing `run_flowguard_background.py` command parser deterministically
binds an exact leading `python` token to its current `sys.executable`. Launch
and `--verify` use the same normalized command identity. Other executables are
not guessed or translated.

## Backfeed

- TestMesh now rejects a background tier whose inner interpreter can follow an
  external upgrade.
- BCL requires inner Python execution to remain bound to the current execution
  owner.
- MTA gives toolchain identity its own leaf obligation, CodeContract, and edge
  test instead of overloading descendant cleanup.
- A real probe proved the normalized command used the frozen virtual
  environment, FlowGuard 0.58.0, the detached 0.58.0 source worktree, a stable
  source fingerprint, and descendant-zero cleanup.
