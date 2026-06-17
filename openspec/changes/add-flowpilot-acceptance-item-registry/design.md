## Context

The existing FlowPilot flow already contains product architecture, root
contract, route skeleton, FlowGuard route checks, Reviewer route challenges,
node acceptance plans, work packet projection, Worker/FlowGuard/Reviewer
evidence, PM disposition, final route-wide ledger, final requirement matrix,
terminal backward replay, and closure. The observed weakness is not absence of
quality language. The weakness is that PM-added high standards and user
requirements are not always represented as the same atomic acceptance item
through all of those existing gates.

Repository rules require current-contract changes only. This design must not
add a parallel role, route, compatibility shim, legacy parser, or separate
acceptance workflow. The registry is a trace index embedded in the current
high-standard contract and projected through current artifacts.

## Goals / Non-Goals

**Goals:**

- Compile explicit user requirements, implicit commitments, PM high standards,
  hard low-quality-success risks, target-realization obligations, child-skill
  standards, and FlowGuard obligations into atomic acceptance items.
- Require every active item to name an owner node, review gate, evidence rule,
  and final replay disposition.
- Make route design, node planning, Reviewer review, FlowGuard process review,
  PM disposition, final ledger, and terminal replay check the same item ids.
- Keep high-quality closure binary at hard gates: closed at high quality or
  blocked. No four-grade scoring model is introduced.
- Add focused negative tests and model checks so missing/orphan/low-quality
  item coverage cannot regress.

**Non-Goals:**

- No new FlowPilot role, packet kind, runtime authority, daemon, fallback lane,
  historical artifact promotion, or old-shape migration.
- No four-level item score or generic quality rubric.
- No product-specific rules for any current target project.
- No release, publish, deploy, tag, or push action.

## Decisions

1. Reuse `high_standard_contract` as the registry seed.

   Alternative considered: create a new registry packet before route planning.
   Rejected because it would create a parallel quality workflow and another
   authority surface. The high-standard contract is already PM-owned and is
   already the first hard quality gate after startup/discovery.

2. Store `acceptance_item_registry` as a current-contract artifact, not a
   compatibility parser.

   Runtime will require the registry on new high-standard contract results.
   Older result bodies are not translated. If the registry is missing, the
   current packet is mechanically blocked and reissued with the required fields.

3. Project by ids, not by duplicated prose.

   Route nodes carry `acceptance_item_ids`. Node context packages carry
   `acceptance_item_projection`. Worker packets, PM dispositions, final
   matrix rows, final ledger blockers, and terminal replay summaries carry the
   same ids. Detailed pass/fail judgement still uses existing packet,
   contract, node-plan, result, review, and evidence artifacts.

4. Keep Reviewer ownership semantic.

   Reviewer does not simply tick a table. Reviewer checks whether each
   applicable item was completed at high quality against the existing
   acceptance sources and direct evidence. Low-quality or existence-only
   closure is a blocker, not a lower score.

5. Use FlowGuard for route reachability and freshness.

   FlowGuard operator checks that all active items are reachable by the route,
   attached to nodes, preserved through route mutation, and backed by current
   evidence/freshness rules. FlowGuard does not approve PM completion or
   replace Reviewer judgement.

## Risks / Trade-offs

- [Risk] Adding a registry can become a second source of truth.
  -> Mitigation: registry items are trace keys and closure rows only. Existing
  artifacts remain the pass/fail evidence sources.

- [Risk] PM may generate broad items such as "make it good."
  -> Mitigation: contract validation and Reviewer cards require atomic,
  evidence-bearing items with owner/review/final replay projection.

- [Risk] Route mutation can shrink the registry accidentally.
  -> Mitigation: final ledger and FlowGuard route checks must preserve active
  registry items unless superseded or waived by explicit authority.

- [Risk] Tests become too broad.
  -> Mitigation: add focused runtime negative tests and planning-quality model
  hazards, then run broader tier/install checks only after source changes
  settle.

## Migration Plan

This is a current-contract change. New runs require
`acceptance_item_registry` in `task.high_standard_contract` results. Existing
old-shape packet results remain unsupported for current completion and must be
reissued through the existing current-contract repair path.

## Open Questions

None for implementation. The control-plane terminal replay block contract is
tracked by the separate `repair-terminal-backward-replay-block-contract`
change and is intentionally not mixed into this registry change.
