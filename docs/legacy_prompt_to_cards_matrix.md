# Legacy Prompt To Cards Matrix

Date: 2026-05-05

This document is the human-readable companion to
`docs/legacy_prompt_to_cards_matrix.json`. It compares the second-backup
monolithic FlowPilot prompt with the prompt-isolated router/card runtime.

The goal is not to copy the old prompt. The goal is to decide, section by
section, whether an old rule should be:

- preserved as a hard gate;
- rewritten as a small system card;
- enforced by the router or an install/runtime validator;
- kept only as a template/runtime artifact;
- merged into an existing card;
- downgraded because the new architecture already prevents the old failure;
- deferred until UI, heartbeat, release, or child-skill work exists;
- retired as an old-architecture guard.

## Snapshot

- Legacy prompt sections mapped: 45
- Current runtime cards: 58
- Template files: no old/new template file count gap was found
- Covered sections: 20
- Partially covered sections: 22
- Planned sections: 2
- Deferred sections: 0
- Retired sections: 1

The biggest gap is no longer missing core startup/material/route/final cards.
Those have been split into runtime cards and router-enforced transitions. The
2026-05-16 runtime-closure pass added the generalized officer request lifecycle
index, current-run quarantine baseline, route-display refresh record, and final
user-report metadata. The 2026-05-16 recursive closure pass then added
parent/module sibling traversal and defect-ledger, role-memory, and
continuation-quarantine closure reconciliation. The remaining gaps are narrower:
full repair sibling route replacement policy, native Cockpit consumption of the
route snapshot, and field-level validators for future specialized officer
report families.

## Key Architectural Decision

The old startup hard gate should not be copied wholesale.

The monolithic prompt needed a heavy startup guard partly because the main
assistant could see too many rules too early and start acting as PM, reviewer,
worker, or route author. The new launcher/router/card design reduces that
specific risk by keeping the entry prompt small, requiring router pending
actions, and delivering system cards only after manifest checks.

That means some old startup checks can be downgraded to router invariants:

- no work after asking the three startup questions;
- no banner or run shell before explicit answers;
- no broad reference-file reading in the launcher;
- no action without a router pending action;
- Controller cannot approve, implement, or read sealed bodies.

But some startup checks remain hard gates because they verify real external
authority rather than old prompt contamination:

- the user answered all three startup questions;
- current run root and `.flowpilot/current.json` / `index.json` agree;
- six role slots are current for this task, or an explicit fallback is recorded;
- continuation mode is real: heartbeat if authorized and available, manual
  resume if not;
- display surface matches the user's answer, with a chat route sign as the
  active fallback when Cockpit is unavailable;
- old state, old assets, old screenshots, old icons, and old agent ids are not
  current authority.

## Coverage By Decision

| Decision | Count | Meaning |
| --- | ---: | --- |
| Preserve as hard gate | 17 | Must remain a blocking route condition |
| Preserve as system card | 12 | Needs one or more focused role cards |
| Preserve as router validator | 7 | Best enforced by state/file/schema checks |
| Preserve as template/runtime artifact | 3 | Keep artifact path, wire later |
| Merge into existing card | 3 | Do not create standalone cards unless needed |
| Downgrade to router invariant | 2 | New architecture already handles most of it |
| Defer until surface exists | 0 | Relevant when Cockpit/UI display work resumes |
| Defer until release work | 0 | Relevant to install/release path |
| Retire as old architecture guard | 1 | Keep as reference only, not runtime behavior |

## Highest Priority Gaps

1. Full repair sibling route replacement policy beyond the current active
   subtree resolver.
2. Native Cockpit consumption of the route snapshot.
3. Field-level validators for future specialized officer report families.

## Section Matrix

| Legacy section | Coverage | Decision | Current mapping | Next action |
| --- | --- | --- | --- | --- |
| Core Rule | Covered | Preserve as hard gate | `pm.core`, `pm.final_ledger`, `pm.closure`, final-ledger replay | Keep source-of-truth and frozen-contract replay regressions current |
| Experimental Packet-Gated Control Plane | Covered | Preserve as router validator | Controller/reviewer cards, `packet_runtime`, router-loop/resume/runtime-closure models | Keep packet checks aligned as specialized report families grow |
| Required Dependencies | Partial | Preserve as router validator | Officer core cards, `check_install.py`, dependencies manifest | Add capability-probe cards/events only when needed |
| Explicit Activation Only | Covered | Downgrade to router invariant | Small launcher and router tests | Keep small-launcher and no implicit activation checks |
| Four-Question Startup Gate -> Three-Question Startup Gate | Covered | Preserve as hard gate | `BOOT_ACTIONS`, startup banner, prompt-isolation model | Keep three explicit startup answers; the old run-mode question stays retired |
| Startup Hard Gate | Partial | Preserve as hard gate | Startup templates, startup PM review model, startup fact-check, PM activation, continuation binding/quarantine, crew freshness cards | Expand imported-artifact disposition when old files are intentionally imported |
| Run Modes | Retired | Retire as old architecture guard | none | Do not add runtime mode state; keep hard gates independent of modes |
| Startup Workflow | Partial | Merge into existing card | PM phase cards and router startup | Use as source for future card batches, not one card |
| Material Intake And PM Handoff | Covered | Preserve as system card | PM material scan packets, reviewer sufficiency, research package, sealed research packet/result relay, reviewer direct-source check, PM material understanding | Keep adding field-level validators as schemas grow |
| Product Function Architecture Gate | Partial | Preserve as hard gate | PM product architecture, product officer modelability, reviewer challenge | Keep strengthening architecture field validation |
| PM Child-Skill Selection Gate | Covered | Preserve as hard gate | `pm.child_skill_selection`, `pm.child_skill_gate_manifest`, reviewer/officer child-skill cards, capability evidence sync | Keep child-skill gate validators in sync with new child skills |
| Root Acceptance Contract And Standard Scenarios | Covered | Preserve as hard gate | PM root contract, reviewer challenge, product officer modelability, PM freeze, final-ledger root replay | Keep frozen-contract replay aligned with root schema growth |
| Node Acceptance Plans | Partial | Preserve as system card | `pm.node_acceptance_plan`, `reviewer.node_acceptance_plan_review`, PM high-standard recheck, parent replay cards, node/parent replay templates, route-display refresh, recursive closure reconciliation model | Parent/module sibling traversal is covered; expand repair sibling replacement policy |
| FlowPilot Skill Improvement Notes | Covered | Preserve as runtime artifact | improvement templates and child-skill improvement reporting path | Add nonblocking PM improvement-report card near closure if needed |
| Defect And Evidence Governance | Covered | Preserve as router validator | defect/evidence scripts/templates/model, PM evidence quality package, final ledger writer, closure cleanliness check, defect-ledger reconciliation | Keep defect reconciliation aligned as defect schemas grow |
| Persistent Six-Agent Crew | Partial | Preserve as hard gate | role cards, crew templates, crew rehydration/freshness card, role memory skeleton | Expand live-agent replacement validation and role memory writeback |
| Reviewer Fact-Check Baseline | Covered | Preserve as system card | reviewer core/dispatch/result/startup/material/route/final cards | Add specialized cards only as new gate families appear |
| Actor Authority Matrix | Partial | Preserve as router validator | core role cards, controller policy, role-owned router events, models | Add explicit required_approver metadata to every gate artifact |
| Universal Adversarial Approval Baseline | Partial | Preserve as system card | reviewer/officer core cards | Add approval snippets to each gate card |
| PM-Owned Child-Skill Gate Manifests | Covered | Preserve as hard gate | `pm.child_skill_gate_manifest`, reviewer child-skill review, process/product officer child-skill cards | Keep gate manifest schema tied to selected skills |
| Strict Gate Obligation Review | Partial | Preserve as hard gate | route skeleton card, reviewer strict-gate card, meta/capability models | Add caveat taxonomy, same-inspector recheck, and route activation validator |
| Self-Interrogation | Planned | Preserve as system card | none yet | Replace broad self-interrogation with PM challenge card |
| User Flow Diagram / Temporary Chat Cockpit | Partial | Preserve as hard gate | route diagram templates/model, controller display note | Keep chat route-sign as active fallback; defer only Cockpit-specific evidence |
| FlowGuard Role | Covered | Preserve as system card | process/product officer core cards | Add officer packet runtime later |
| Dual-Layer Product And Process Models | Partial | Preserve as hard gate | meta/capability/runtime-closure models, officer core cards, PM officer request/report card, officer request lifecycle index | Add specialized field-level validators as new model-report families appear |
| PM-Initiated FlowGuard Modeling | Partial | Preserve as system card | request/report templates, PM officer request/report card, officer request lifecycle index | Keep PM officer loop packet-bound and add report-specific validators when needed |
| Human-Like Inspection Loop | Partial | Preserve as system card | reviewer core/result/startup/material/node/final cards, terminal replay, human review template | Add richer UI/product walkthrough cards when those route surfaces are active |
| Recursive Route Tree Planning | Partial | Preserve as router validator | route templates, route skeleton card, parent backward replay cards, effective-node auto-advance, parent/module sibling entry | Expand repair sibling replacement policy |
| Controlled Nonterminal Stop Notice | Partial | Preserve as runtime artifact | pause/continuation templates, resume model | Add pause snapshot action and PM stop/block path |
| Quality Package | Covered | Merge into existing card | `pm.evidence_quality_package`, `reviewer.evidence_quality_review`, evidence/generated-resource/quality ledgers | Extend quality fields as new route surfaces require them |
| `.flowpilot/` Source Of Truth | Partial | Preserve as router validator | run shell, resume state load, continuation quarantine, final-ledger source-of-truth builder | Expand old-file import disposition beyond the quarantine baseline |
| Real Heartbeat Continuation | Partial | Preserve as hard gate | heartbeat templates, resume cards, one-minute binding/tick writer, continuation binding card | Wire host automation adapters to record the same binding event |
| Capability Routing | Partial | Preserve as system card | capability templates/model, PM selection/gate-manifest/officer cards | Add loaded-file evidence, domain review, and child-loop closure validator |
| Prompt Layer Boundary | Covered | Downgrade to router invariant | small launcher, manifest, check_install | Keep enforcing small launcher and card delivery |
| Visual Example Particle | Covered | Merge into existing card | generated resource ledger, PM evidence quality UI/visual old-asset rejection | Keep old visual assets quarantined as historical references only |
| UI And Visual Evidence | Covered | Preserve as system card | PM evidence quality package, reviewer evidence quality review, generated-resource ledger, UI screenshot/old-asset validator | Add richer UI walkthrough fields when Cockpit/UI route work resumes |
| Final Route-Wide Gate Ledger | Covered | Preserve as hard gate | final ledger templates/card, source-of-truth final ledger writer, segmented reviewer replay, terminal map, closure suite, router-loop model | Keep replay segment generation aligned with future source-of-truth entry types |
| Chunk Rule | Partial | Preserve as system card | worker cards, current-node card, node acceptance plan/review, router-loop model | Extend the same packet loop to repair packets and officer packets |
| Residual Risk Triage Gate | Covered | Preserve as hard gate | PM final ledger writer validates `unresolved_residual_risk_count=0` | Extend residual-risk source ledger if a route adds explicit risk entries |
| Terminal Closure Suite | Covered | Preserve as hard gate | closure card/template, lifecycle script, closure-suite writer, continuation disable, dirty-ledger block, defect-ledger/role-memory/quarantine reconciliation, final user report metadata | Keep closure reconciliation aligned as new ledger families are added |
| Route Updates | Covered | Preserve as router validator | route mutation writer, repair cards, stale-evidence ledger, superseded node history | Expand to full branch/sibling route replacement policies |
| Hard Gates | Partial | Preserve as hard gate | PM core, HANDOFF | Add gate metadata to route/ledger artifacts |
| Automatic Tool Installation | Partial | Preserve as system card | installer/check scripts, dependencies manifest, PM dependency-policy card | Add router-visible dependency decision records when a route needs an install |
| Completion | Partial | Preserve as hard gate | final ledger writer, segmented reviewer terminal replay, closure card, closure-suite writer, router-loop/runtime-closure models, final user report metadata | Keep closure authority separate from user-facing report output |
| References | Covered | Preserve as runtime artifact | reference files remain | Keep for targeted maintainer/card-writing reads; bulk-read prevention lives in prompt boundary |

## Immediate Next Work

1. Add full repair sibling route replacement policy beyond the current active
   subtree resolver.
2. Add native Cockpit consumption of the route snapshot.
3. Add specialized field-level validators when future officer report families
   are introduced.
