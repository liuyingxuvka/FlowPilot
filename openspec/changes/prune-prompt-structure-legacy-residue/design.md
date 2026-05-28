## Context

FlowPilot now treats FlowGuard as the process kernel and keeps many legacy
patterns only as compatibility evidence or negative fixtures. The active risk is
not a large architecture gap; it is small residual wording in prompts, cards,
registries, and maintenance notes that can still sound like active instructions
for retired paths.

The worktree is shared with other active agents. The `finish-flowpilot-maintenance-convergence-v2`
change remains in progress, so this cleanup must avoid taking over its scope and
must not rewrite peer-owned files except where a narrow, current residue fix is
clearly needed.

## Goals / Non-Goals

**Goals:**

- Identify stale active guidance in prompt/card/registry/structure surfaces.
- Classify findings as active residue, compatibility evidence, peer-owned, or
  deferred structural debt before editing.
- Patch narrow active residues so they name FlowGuard-kernel authority, Router
  ownership, runtime artifacts, and compatibility exports correctly.
- Validate the cleanup with focused prompt/registry checks, OpenSpec validation,
  and install freshness checks when skill assets change.

**Non-Goals:**

- Do not remove historical evidence, retired-path negative fixtures, or
  compatibility-facade tests solely because they mention old behavior.
- Do not split large modules or perform StructureMesh work unless a prompt
  residue fix cannot be made safely without it.
- Do not archive, push, tag, publish, or release this repository.
- Do not modify the peer-owned maintenance convergence v2 task list.

## Decisions

- **Classify before editing.** A textual hit on `legacy`, `heartbeat`,
  `cockpit`, `watchdog`, or compatibility exports is not automatically a bug.
  The bug is active guidance that tells runtime agents to use retired authority.
- **Prefer small prompt/registry patches.** Most issues should be fixed by
  tightening wording, ownership labels, or validation coverage, not by moving
  code.
- **Preserve compatibility names where contracts require them.** Some old field
  names and facade exports are still public compatibility surfaces; replacing
  them would break evidence or downstream consumers.
- **Treat peer writes as freshness boundaries.** If another agent changes a file
  during this cleanup, re-read it before editing and scope any patch to the
  current residue only.

## Risks / Trade-offs

- **False positives from historical docs** -> keep a classification ledger so
  retained references are deliberate.
- **Breaking compatibility evidence** -> run focused prompt/registry checks and
  avoid renaming exported compatibility fields without a dedicated spec.
- **Peer-agent overlap** -> inspect `git status` before edits and skip/report
  peer-owned candidates that are not safe to patch locally.
- **Overclaiming cleanup completion** -> report skipped heavy checks and
  residual deferred StructureMesh debt explicitly.
