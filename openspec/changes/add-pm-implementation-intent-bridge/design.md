## Context

FlowPilot already has PM product-function architecture, FlowGuard product-behavior modeling, PM route skeleton drafting, FlowGuard route-process checks, node acceptance plans, worker packets, and terminal closure ledgers. The missing boundary is the PM's realization judgment between "what the product must be" and "how the route should execute it."

Current constraints:

- PM must remain the product and planning authority, not the formal FlowGuard model author.
- FlowGuard Operator must own formal target-realization modeling and simulation.
- Reviewer must challenge quality, user intent preservation, and PM/FlowGuard alignment.
- Runtime/Router must enforce strict current-contract JSON and legal events; no prose fallback, legacy alias, or compatibility path may be added.
- LogicGuard and SourceGuard remain out of scope for this change.

## Goals / Non-Goals

**Goals:**

- Insert a mandatory PM implementation-intent bridge after accepted product behavior modeling and before route skeleton drafting.
- Require FlowGuard Operator to formalize and simulate that PM intent as a target-realization model.
- Require PM and Reviewer acceptance before route skeleton work.
- Carry accepted realization obligations into route, process, node, worker, and terminal closure surfaces.
- Add negative model/test coverage for skipped, downgraded, or unconsumed realization intent.
- Sync the repository-owned installed FlowPilot skill after source changes.

**Non-Goals:**

- Do not make PM write the formal FlowGuard model.
- Do not add LogicGuard, SourceGuard, or external research/source workflows.
- Do not add a separate ledger family or compatibility aliases for old fields.
- Do not change the frozen user acceptance contract semantics.
- Do not modify unrelated in-progress OpenSpec changes.

## Decisions

1. **Place the bridge after product model acceptance, before route skeleton.**

   Product behavior modeling gives PM a stable "what." Implementation intent then captures PM's "how it should be realized" before route skeleton decomposes the work.

   Alternative considered: put implementation intent inside product architecture. Rejected because it keeps the current hidden coupling and lets route drafting consume mixed product and realization notes without a dedicated FlowGuard simulation gate.

2. **Use a PM implementation intent brief, not a PM-authored model.**

   PM output is structured but plain-language: selected realization path, rejected alternatives, hard parts, thin-success traps, non-downgrade rules, evidence expectations, FlowGuard questions, and route implications.

   Alternative considered: ask PM to write FlowGuard states/transitions directly. Rejected because it blurs PM and FlowGuard ownership and may lower PM's strategic product judgment into implementation mechanics.

3. **Reuse the existing FlowGuard modeling request/report family.**

   Add a target-realization model kind and required report fields instead of creating a parallel operator channel.

   Alternative considered: introduce a new ledger or packet family. Rejected under the minimal current-contract rule because the existing packet/result/gate surfaces can express the new step.

4. **Gate route skeleton on PM and Reviewer acceptance.**

   PM confirms the FlowGuard model preserved PM intent. Reviewer confirms the PM intent and FlowGuard model preserve user value and block low-quality completion.

   Alternative considered: let FlowGuard green status directly unlock route skeleton. Rejected because FlowGuard validates process/model shape, while Reviewer owns substantive human-quality challenge.

5. **Propagate realization obligations through downstream artifacts.**

   Route nodes, route-process checks, node acceptance plans, worker packets, and final ledgers must cite the accepted realization obligations they consume or explicitly waive with PM/Reviewer authority.

## Risks / Trade-offs

- **Risk: The bridge becomes another generic prose essay.** → Use strict templates and role-output contracts with required fields and negative tests for generic/missing content.
- **Risk: The bridge adds planning overhead to simple tasks.** → Allow route profiles to mark trivial/simple tasks as narrow, but still require an explicit PM waiver reason rather than silent skipping.
- **Risk: Runtime complexity grows.** → Reuse existing modeling request/report and control-transaction surfaces; add only the minimum legal phases/events needed.
- **Risk: Parallel AI work changes nearby files.** → Keep edits scoped, recheck git status before each broad phase, and do not revert peer edits.
- **Risk: Evidence goes stale after prompt/model changes.** → Rerun affected focused checks, rebuild topology, sync install, and rerun install audits before claiming done.
