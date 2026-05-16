## Context

FlowPilot already supports route mutation records, stale evidence lists,
execution frontier rewrites, route-display refreshes, final ledger scans, and
focused repair transaction models. The remaining release-facing weakness is not
the existence of mutation, but the completeness of its replacement policy:
return repairs, superseded original nodes, sibling branch replacement, and
completion blocking must all be represented by executable evidence.

This pass also runs in a shared workspace while other AI agents may be active.
Edits must stay narrow, avoid broad formatters, and re-check git state before
commit/push.

## Goals / Non-Goals

**Goals:**

- Make route repair/replacement policy explicit enough that old sibling or
  superseded evidence cannot remain current proof after a structural mutation.
- Use a focused FlowGuard model before production edits and preserve known-bad
  hazards for missing topology, stale evidence reuse, stale frontier reuse,
  missing replay, and premature completion.
- Update public-facing docs and privacy/release checks so a pre-release branch
  sync has clear evidence.
- Sync the local installed FlowPilot skill, commit the scoped changes, and push
  the branch to `origin`.

**Non-Goals:**

- Do not run the heavyweight Meta or Capability regressions in this pass.
- Do not tag, create a GitHub Release, publish binaries, deploy, or publish
  companion skill repositories.
- Do not build native Cockpit integration; keep this pass to release-facing
  readiness and route repair/replacement policy.

## Decisions

### Focused child model over broad parent regression

Add or extend a focused FlowGuard route repair/replacement model instead of
expanding Meta/Capability. This matches the touched risk and keeps the heavy
models explicitly skipped per user instruction.

Alternative considered: run the entire Meta/Capability suite. Rejected because
the user excluded those two heavy checks and this change has a narrower owner.

### Replacement policy is topology-plus-evidence, not display text

Runtime mutation records must carry the topology strategy and affected evidence
facts needed by later Router/frontier/final-ledger decisions. User-flow display
or PM narrative can explain the mutation, but cannot by itself make old
evidence stale or activate a replacement path.

Alternative considered: document the policy only in README/HANDOFF. Rejected
because the existing remaining gap is behavior-bearing.

### Public sync remains source-only

The final remote step pushes source commits to the FlowPilot repository only.
The release contract remains source-only until a separate tag/release action is
explicitly requested and validated.

Alternative considered: create a tag or GitHub Release for the new version.
Rejected because the user asked for pre-release maintenance and sync, not
publication.

## Risks / Trade-offs

- [Risk] Other agents edit overlapping files while this pass is running. →
  Mitigation: keep edits scoped and re-check git status before validation,
  commit, and push.
- [Risk] Focused FlowGuard coverage misses a broader parent-model issue. →
  Mitigation: run route repair/replacement, router-loop/runtime focused checks,
  release tooling, install checks, smoke fast, and record Meta/Capability as
  intentionally skipped rather than passed.
- [Risk] Public release check performs network URL probes that may fail because
  of temporary connectivity. → Mitigation: run the normal public check when
  feasible; if a network-only URL probe fails, report it separately from local
  privacy/source-boundary checks.
