## Context

The current FlowPilot protocol already requires a PM-owned product-function
architecture, a Product FlowGuard Officer product behavior model, a Process
FlowGuard Officer route process model, recursive route decomposition, and
child-skill standard extraction. A later Reviewer-only optimization removed
default child-skill Process/Product Officer gates from the child-skill manifest
approval path. That speed profile is useful for some narrow gates, but it makes
the global protocol easy to misread as "one product model plus one route model
is enough."

The desired shape is not to replace the existing order. FlowPilot should still
build product understanding first, process viability second, and route execution
third. The strengthening is a new PM-owned modeling coverage decision before
product modeling, using a current startup snapshot of FlowGuard capabilities.

## Goals / Non-Goals

**Goals:**

- Treat FlowGuard as a required FlowPilot foundation, not an ordinary optional
  child skill.
- Generate one run-scoped FlowGuard capability snapshot at startup and use it
  for the whole run.
- Require PM to plan product-side model families before Product Officer work.
- Require PM to choose ordinary child skills only after product model acceptance.
- Require PM to plan process-side model families before Process Officer work.
- Allow model families: core product, UI/interaction, data/state,
  failure/recovery, validation evidence, route hierarchy, child-skill
  conformance, test/replay flow, and repair-return models.
- Make every merge or non-modeling decision explicit and reviewable.

**Non-Goals:**

- Tracking FlowGuard upgrades during an active run.
- Forcing every possible model family on every task.
- Removing Reviewer-only root/child manifest compatibility where it remains a
  deliberate speed profile.
- Reworking the in-progress packet review simplification.
- Publishing, pushing, or changing unrelated autonomous UI skill work.

## Decisions

1. **Snapshot once at startup.**

   Router startup writes `.flowpilot/runs/<run-id>/flowguard/capability_snapshot.json`
   before PM product modeling. It resolves FlowGuard from the active Python
   environment and discovers FlowGuard skills from portable Codex/project skill
   roots instead of any user-specific path. The snapshot includes FlowGuard
   import/schema/version evidence, discovered FlowGuard skill routes, source
   paths, content hashes, portable resolution roots, and a short PM-readable
   capability menu. The run does not monitor mid-run FlowGuard upgrades.

2. **PM plans product models before Product Officer modeling.**

   PM writes `flowguard/product_modeling_plan.json` before Product Officer work.
   The plan lists product model families, merge decisions, explicitly skipped
   families with reasons, and Product Officer role-skill bindings from the
   snapshot. Product Officer must either deliver the planned family or return a
   blocker/split request.

3. **Ordinary child-skill selection happens after product model acceptance.**

   PM uses the accepted product model family to decide which ordinary child
   skills are needed. The child-skill manifest remains the place that maps
   selected skill standards to route nodes, worker packets, reviewer gates, and
   officer gates.

4. **PM plans process models before Process Officer modeling.**

   PM writes `flowguard/process_modeling_plan.json` before Process Officer work.
   The plan lists route hierarchy, child-skill conformance, validation/replay,
   repair-return, and other process-side families. Process Officer must prove
   the process can cover the accepted product model family and child-skill
   manifest.

5. **Final closure checks model family coverage.**

   The final route-wide ledger must reference the startup FlowGuard snapshot,
   PM modeling plans, accepted officer reports, skipped/merged model decisions,
   child-skill bindings, and validation evidence. It must not count a manifest,
   route draft, or single-model report as coverage for unaddressed model
   families.

## Risks / Trade-offs

- **Risk: This adds ceremony to small runs.** -> Mitigation: PM may merge or
  skip families, but must record a short reason so the route is reviewable.
- **Risk: Officers over-expand into all FlowGuard skills.** -> Mitigation: the
  snapshot is a menu, not a mandate; PM selects only the needed role bindings.
- **Risk: Existing dirty Meta/Capability model work conflicts with this pass.**
  -> Mitigation: add a focused model/check runner first, then run heavyweight
  regressions in background without editing peer-owned model files unless a
  follow-up pass is required.
- **Risk: Reviewer-only child-skill gates contradict model-family coverage.** ->
  Mitigation: keep Reviewer-only manifest approval as a local speed gate, but
  require modeling coverage elsewhere before route activation and completion.

## Migration Plan

1. Add the OpenSpec requirements and focused FlowGuard model for the strengthened
   modeling coverage sequence.
2. Add templates and cards for the startup snapshot, Product Modeling Plan, and
   Process Modeling Plan.
3. Update officer cards, PM decision cards, and final ledger wording to require
   model-family references and explicit merge/skip reasons.
4. Add focused tests and install checks for the new artifacts.
5. Run focused checks and background Meta/Capability regressions.
6. Sync the installed local FlowPilot skill from repo-owned source and commit the
   scoped local change.
