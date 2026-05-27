## Context

FlowPilot deliberately allows several objects to coexist: independent runs, background Flow blocks, historical packets, superseded route branches, and replayed events. The safety problem is narrower: within a declared scope, some authorities must be singular. Examples include one daemon writer per run, one active holder for a packet lease, one semantic PM package disposition per batch/generation, one current route frontier after activation, and one current material-progress authority per material generation.

The repository already contains focused safeguards for many of these cases: run-scoped daemon locks, packet ledgers, scoped event identity replay, PM package disposition conflict checks, route mutation stale-evidence handling, ACK/output separation, model maturation signals, and model-test-code alignment. The missing architectural layer is a shared, install-visible authority matrix and model/check pair that ties those safeguards together and prevents future confidence claims from treating plural state, stale state, or progress-only evidence as singleton closure.

This change extends the existing model-maturation track instead of replacing it. It keeps runtime behavior changes narrow and evidence-driven, because parallel AI agents may be modifying adjacent model/result artifacts in the same worktree.

## Goals / Non-Goals

**Goals:**
- Define a singleton authority matrix that separates intended plurality from illegal duplicate authority.
- Add executable FlowGuard coverage for singleton conflict families.
- Add a live-state audit that inspects current `.flowpilot` authority surfaces without mutating them.
- Expose singleton gaps through model maturation and model-test-code diagnostics.
- Include the new checks in local install readiness and refresh the installed FlowPilot skill after source changes.
- Preserve peer-agent changes and avoid repo-wide cleanup.

**Non-Goals:**
- No release, deploy, remote push, or public publication.
- No destructive cleanup of `.flowpilot` runs, generated result artifacts, or peer-agent edits.
- No rewrite of the router, packet runtime, role-output runtime, Meta model, or Capability model.
- No claim that every possible duplicate in future extensions is closed; confidence is bounded by the authority matrix and current evidence.

## Decisions

1. **Represent singleton safety as an authority matrix plus executable hazards.**

   The matrix is the human-readable source of which scope owns each singleton, while the FlowGuard model encodes the high-risk transitions. This avoids scattering one-off duplicate checks across unrelated modules without a shared ownership contract.

   Alternative considered: add ad hoc tests around each current defect family. Rejected because it would not explain which duplicate states are legal plurality versus illegal split authority.

2. **Reuse existing model boundaries and add a focused child-style model.**

   Existing daemon, event-idempotency, route-mutation, material generation, and model-maturation models remain the owning boundaries. The new model consumes those ownership facts and checks cross-boundary singleton invariants.

   Alternative considered: extend Meta and Capability parent models directly. Rejected because those parents are already large and would make ordinary maintenance evidence slower and less local.

3. **Treat live-run evidence as audit input, not automatic repair.**

   The live audit reports duplicate/stale risks but does not rewrite `.flowpilot` state. Repairs stay under the router/control-plane mechanisms that own those files.

   Alternative considered: have the audit auto-supersede or quarantine duplicates. Rejected because it could conflict with active peer agents and bypass Router-owned repair transactions.

4. **Put installation sync after validation, not in parallel with install audits.**

   Source checks and background model regressions can run in parallel where safe, but install sync and install audit are serialized so the audit reads the final installed copy instead of racing the sync step.

   Alternative considered: start install audit while sync runs. Rejected because previous KB evidence shows that can produce stale installed digests.

5. **Use scoped confidence unless evidence is proof-bound and current.**

   Progress logs, missing exit files, stale result artifacts, or model-only results do not close singleton safety. The final report distinguishes full confidence, scoped confidence, and blocked gaps.

## Risks / Trade-offs

- **Risk: The matrix becomes another stale document.** → Generate/validate it through a checker and include it in install readiness.
- **Risk: Background regressions overwrite shared artifacts during peer work.** → Use unique names for auxiliary checks where possible, but inspect standard AGENTS artifacts last for required heavyweight checks.
- **Risk: The new model duplicates existing model responsibility.** → Keep it as an aggregation/cross-boundary hazard model and record ownership reuse decisions in documentation.
- **Risk: Live audit finds risk in another agent's active run.** → Report the finding and avoid mutation; only code/source changes are part of this change.
- **Risk: Broad confidence remains scoped.** → Accept scoped confidence when heavy evidence is stale, skipped, or peer-modified rather than overclaiming.

## Migration Plan

1. Add OpenSpec delta specs and tasks for singleton identity authority.
2. Add authority matrix documentation and an executable checker/model pair.
3. Feed singleton authority results into model maturation diagnostics and install readiness.
4. Add targeted tests for model hazards, live audit classification, and install visibility.
5. Run focused checks first, then background heavyweight checks using the repository artifact contract.
6. Sync repository-owned FlowPilot skill to the local installed copy.
7. Re-run install audit/check and finish only after task checkboxes reflect verified evidence.

## Open Questions

- Full legacy Meta/Capability regressions may remain long-running. If they do not complete within the work window, final confidence must name them as pending instead of claiming pass.
- If live audit finds an active peer-run conflict, this change will report it but not repair the active run unless a separate Router-owned repair route is opened.
