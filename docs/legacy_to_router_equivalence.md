# Legacy-To-Router Equivalence

Date: 2026-05-04

This file is the human-readable companion to
`docs/legacy_to_router_equivalence.json`. It records which old FlowPilot
obligations have a new prompt-isolated enforcement point and which still need
implementation. The goal is functional equivalence or intentional quarantine,
not copying the old monolithic prompt.

## Current Coverage

| Obligation | New enforcement point | Status | Missing work |
| --- | --- | --- | --- |
| Four-question startup gate | Small `SKILL.md`, router boot actions, router tests, prompt-isolation model | Covered | Runtime regression now rejects banner/run-shell before explicit startup answers |
| Fresh run root and legacy backup boundary | Router run shell, second backup manifest, install check | Partial | Add continuation import/quarantine rules |
| Six-role crew authority | Router role slots, role cards, runtime tests | Partial | Add live-agent ids, memory packets, replacement, role authority validators |
| Controller relay-only boundary | Controller card, manifest policy, router wait/resume actions, prompt and resume models | Covered | Keep adding role-isolation tests as packet-loop actions grow |
| System card manifest delivery | Runtime manifest, router manifest check, tests, install check | Covered | Keep validator in sync as cards grow |
| Packet ledger mail delivery | Packet runtime, packet tests, router mail/material/research/current-node packet checks | Partial | Extend the same sealed-envelope loop to generalized async officer modeling packets |
| PM material and research decisions | Material scan packets, sufficiency, research package, research packet/result relay, reviewer direct-source check, PM absorb, PM material understanding | Covered | Keep adding field-level validators as research package schemas grow |
| Reviewer before worker evidence use | Reviewer dispatch/result cards, node acceptance review, current-node dispatch card, packet runtime, router result relay, prompt model | Covered | Extend the same exact node/version matching to repair packets and officer packets |
| FlowGuard officer model gates | Officer role cards, product architecture/root contract officer cards, meta/capability models | Partial | Add generalized officer request/report packet gates |
| Route frontier/current-node loop | PM current-node card, node acceptance plan/review, route activation/frontier writer, current-node packet tests, parent backward replay gate, router-loop model | Partial | Add full automatic multi-node traversal and repair sibling resolver |
| Route mutation/stale evidence | PM repair card, reviewer-block event, mutation writer/frontier rewrite, router-loop model | Partial | Add dedicated mutation card and stale evidence ledger writer |
| Heartbeat/manual resume reentry | Stable docs/templates, runtime resume cards, router resume action, resume model/tests | Covered | Add production replay adapter later if resume evidence expands |
| Final ledger/terminal replay | PM final ledger card, reviewer final backward replay card, final ledger writer, terminal replay map, closure card, router-loop model, runtime tests | Partial | Add closure-suite lifecycle writer after PM closure approval |
| Cockpit or chat route display | Startup display answer, route diagram model/templates, startup display status writer | Partial | Startup chat route sign is covered; add current-node route sign refresh and Cockpit integration |
| Retired assets and old state quarantine | Retired path self-check and second backup | Partial | Add runtime import quarantine checks for old assets and old agent ids |
| Skill-improvement nonblocking report | Existing templates and meta/capability models | Planned | Add runtime cards and router events |

## Working Principle

An old obligation is considered `covered` only when it has an executable
enforcement point: router state, card manifest validation, packet runtime,
FlowGuard model, unit test, install check, or a quarantine check. Protocol prose
alone is `planned` or `partially_covered`.

## Next Conversion Targets

1. Generalized async FlowGuard officer request/report packets, because PM
   modeling requests should use the same envelope isolation as workers.
2. Automatic multi-node traversal and repair sibling resolution beyond the
   current active-node resolver.
3. Closure-suite lifecycle reconciliation after final reviewer replay, because
   terminal cleanup still needs a writer distinct from the ledger/replay gate.
