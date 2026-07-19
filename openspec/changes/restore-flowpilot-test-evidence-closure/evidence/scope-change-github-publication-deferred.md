# GitHub Publication Scope Change

Original boundary date: 2026-07-10
Current superseding boundary date: 2026-07-18

The maintainer originally requested that this task avoid all Git actions while
another AI also repaired FlowPilot in the same working tree.  On 2026-07-18,
the maintainer explicitly authorized exact local Git closure while retaining
the remote-publication boundary.

Current authorization boundary:

- Continue local implementation, model/test validation, install sync, and
  evidence-backed handoff after concurrent changes settle.
- Stage only the agreed task-owned paths and create one local Git commit.
- Do not stage or commit concurrent/user-owned work.
- Do not create a Git tag.
- Do not push a branch or tag.
- Do not create or update a GitHub Release.
- Treat remote publication as deferred, not as passed evidence and not as a
  blocker for a truthful local-candidate claim.

Any future remote publication requires a new explicit maintainer action and
fresh verification against the then-current source tree.
