## Context

FlowPilot has a dense FlowGuard model mesh, Model-Test Alignment reports, known-friction gates, synthetic coverage matrices, and background test-tier evidence. The latest FlowGuard package exposes `review_model_maturation_loop()`, which turns route evidence into explicit model-upgrade actions before a broad claim is made.

The current gap is architectural rather than a single runtime bug: FlowPilot can have green alignment or coverage artifacts while post-evidence signals still imply that the model is too coarse, stale, or only scoped. This change adds a maintenance gate that consumes those signals and makes the next model action explicit.

## Goals / Non-Goals

**Goals:**
- Add a focused FlowGuard model and checker for FlowPilot model maturation closure.
- Encode the current known maturation signals: ACK settlement versus output completion, route replacement disposition, prompt assets as contract inputs, stale evidence, oversized parent models, and progress-only background evidence.
- Feed the new gate into existing validation surfaces and install readiness.
- Refresh targeted model evidence in a background-friendly way while preserving peer-agent changes.
- Keep broad confidence scoped until all required maturation actions are resolved.

**Non-Goals:**
- No release, publish, deploy, or remote push.
- No destructive cleanup or rollback of peer-agent work.
- No frozen acceptance-contract downgrade.
- No full rewrite of Meta, Capability, or router runtime internals.

## Decisions

1. **Add a focused model maturation gate instead of expanding every parent model.**

   Rationale: the new FlowGuard helper is designed to aggregate post-evidence signals. Expanding Meta or Capability directly would increase already large parent models and make evidence freshness harder to reason about.

   Alternative considered: inline maturation state into `meta_model.py` and `capability_model.py`. Rejected because it would blur runtime workflow state with maintenance evidence state.

2. **Treat maturation signals as ordinary FlowGuard evidence.**

   The checker will produce a result artifact that exposes decision, confidence, recommended actions, scoped signal ids, and findings. Existing validation surfaces can then consume that artifact like other model results.

   Alternative considered: make this a documentation-only checklist. Rejected because the user explicitly asked to use latest FlowGuard models, and prose-only checks would regress to the coarse-model problem.

3. **Use a data-driven signal registry.**

   A small Python model/check pair will encode the currently known signal families and their required actions. This makes future signal additions reviewable without changing runtime behavior.

4. **Keep stale and progress-only evidence visible.**

   The new gate will not treat progress logs, missing exit artifacts, stale result mtimes, or model-only evidence as pass. It will classify them as `refresh_evidence` or `downgrade_claim` until final artifacts exist.

5. **Update install/smoke surfaces narrowly.**

   The new gate should be part of `scripts/check_install.py` readiness because the installed FlowPilot skill otherwise could drift from repository source and still appear current.

## Risks / Trade-offs

- **Risk: More gates increase maintenance friction.** → Keep the model focused and make actions explicit so failures point to the owning model or evidence boundary.
- **Risk: Existing dirty result files are peer-owned.** → Avoid reverting or broad-formatting them; only update artifacts produced by this change or by commands run during this change.
- **Risk: Heavy regressions may run long.** → Use the repository background artifact contract and report final exit/meta status instead of progress-only claims.
- **Risk: Broad confidence remains scoped after implementation.** → That is acceptable when unresolved external peer edits, stale heavy evidence, or skipped release-only checks remain.

## Migration Plan

1. Add OpenSpec specs and tasks for the maturation closure gate.
2. Add a focused FlowGuard model/check script and result artifact.
3. Update validation and install surfaces to require the focused gate.
4. Run targeted foreground checks and background-compatible model regressions.
5. Sync installed FlowPilot skill from the repository and audit local install freshness.
6. Leave git working tree dirty if peer-agent changes remain uncommitted, but report exactly what this session changed.

## Open Questions

- Full release-level Meta/Capability legacy regressions may remain background or deferred evidence if they exceed the available time window; routine confidence can still be supported by thin parent and focused maturation evidence.
