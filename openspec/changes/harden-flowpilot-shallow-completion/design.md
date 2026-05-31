## Context

FlowPilot already has high-standard PM route planning, low-quality-success
review, Reviewer independent challenge, self-interrogation records, and terminal
backward replay. The recent ProjectRadar run showed a remaining failure mode:
the process can satisfy a design-plan contract while the user's practical next
step is still missing.

The fix must preserve FlowPilot's lightweight direction. The old FlowPilot
templates contain many evidence fields, but their useful mechanism is smaller:
identify a small list of task-specific shallow-completion traps, route work to
eliminate or explicitly bound them, make Reviewer attack them, and make Closure
replay from the delivered output back to the original user outcome.

## Goals / Non-Goals

**Goals:**

- Add a lightweight shallow-completion guard to existing PM, Reviewer, and
  Closure gates.
- Keep the guard task-specific and prose-friendly, so FlowPilot does not gain a
  broad new schema or many new required fields.
- Add focused FlowGuard/model bad-case evidence for the exact failure class:
  design-only route pass, reviewer downgrade to nonblocking, and lifecycle-only
  terminal closure pass.
- Sync repository-owned FlowPilot skill files to the local installed skill after
  validation.

**Non-Goals:**

- Do not recreate old FlowPilot's full product-function architecture templates.
- Do not add a new runtime ledger family for shallow-completion traps.
- Do not make every design/planning task require runnable implementation when
  the user explicitly asks for discussion, planning, or proposal only.
- Do not change packet envelope authority, sealed-body boundaries, or
  Controller mechanics.

## Decisions

1. Reuse existing low-quality-success and final-user usefulness language.

   The guard belongs in the PM route skeleton, Reviewer node-completion review,
   and PM closure cards because those gates already own route adequacy, quality
   challenge, and terminal approval. This avoids a new schema and keeps the
   behavior close to the role that can act on it. The trap list may contain a
   few concise items or paragraphs when the task has several obvious shallow
   success modes; the important rule is that each current item is routed,
   waived with scope, or blocked.

2. Treat "all-design route" as a warning, not a universal failure.

   A route dominated by Design/Define/Review/Integrate nodes is acceptable when
   the user asked only for planning. It becomes a blocker when the accepted user
   outcome requires a runnable pilot, first data pass, implementation-ready
   package, operational handoff, or other practical next action.

3. Add focused model hazards instead of broad state expansion.

   Existing planning-quality and reviewer-active-challenge checks already model
   low-quality success, user-intent replay, and existence-only evidence. Add
   narrow hazards there first. Add a closure-focused hazard only if existing
   tests do not already cover final replay being reduced to ledger cleanliness.

4. Validate source and installed skill separately.

   Source tests prove the repo behavior. Install sync and install audits prove
   the local `flowpilot` skill that future runs use matches the source. Per
   prior install-sync lessons, run sync before audit/check and do not parallelize
   audit with sync.

## Risks / Trade-offs

- Overblocking genuine planning tasks -> Mitigate by requiring the guard to read
  the accepted user outcome first; planning-only outcomes may pass with explicit
  boundary language.
- Prompt bloat -> Mitigate by editing a few concise paragraphs in existing
  cards rather than adding large templates.
- Model overreach -> Mitigate by adding small bad-case hazards and tests instead
  of expanding the parent Meta/Capability state space unless affected checks
  require it.
- Stale evidence after install sync -> Mitigate by rerunning install audit and
  check after sync, and rebuilding/checking topology after model/card/test
  changes.

## Migration Plan

1. Update OpenSpec artifacts for the new guard and affected existing
   capabilities.
2. Add focused FlowGuard/model hazards and tests for PM, Reviewer, and Closure
   shallow-completion failure.
3. Update the PM route skeleton, Reviewer review, and PM closure cards.
4. Run targeted model/test checks.
5. Rebuild/check project topology if model/test/card surfaces changed.
6. Sync repository-owned FlowPilot skill files into the local installed skill.
7. Run install audit and install/check validation after sync.
8. Record FlowGuard adoption and KB postflight evidence.
