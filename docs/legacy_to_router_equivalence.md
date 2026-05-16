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
| Fresh run root and legacy backup boundary | Router run shell, second backup manifest, install check, continuation quarantine artifact | Partial | Expand imported-artifact disposition when old runs are intentionally imported |
| Six-role crew authority | Router role slots, role cards, runtime tests | Partial | Add live-agent ids, memory packets, replacement, role authority validators |
| Controller relay-only boundary | Controller card, manifest policy, router wait/resume actions, prompt and resume models | Covered | Keep adding role-isolation tests as packet-loop actions grow |
| System card manifest delivery | Runtime manifest, router manifest check, tests, install check | Covered | Keep validator in sync as cards grow |
| Packet ledger mail delivery | Packet runtime, packet tests, router mail/material/research/current-node/PM role-work packet checks, officer request lifecycle index | Partial | Keep adding field-level report validators as modeling packet families grow |
| PM material and research decisions | Material scan packets, sufficiency, research package, research packet/result relay, reviewer direct-source check, PM absorb, PM material understanding | Covered | Keep adding field-level validators as research package schemas grow |
| Reviewer before worker evidence use | Reviewer dispatch/result cards, node acceptance review, current-node dispatch card, packet runtime, router result relay, prompt model | Covered | Extend exact node/version matching to repair packets and dedicated officer-model reports |
| FlowGuard officer model gates | Officer role cards, product architecture/root contract officer cards, route draft process/product check cards, PM role-work request channel, officer lifecycle index, meta/capability/next-recipient/runtime-closure models | Partial | Add richer field-level product/process report contracts when new modeling packet families are introduced |
| Route frontier/current-node loop | PM current-node card, node acceptance plan/review, route activation/frontier writer, current-node packet tests, parent backward replay gate, router-loop model, recursive closure reconciliation model, route mutation activation model | Partial | Parent/module sibling traversal and sibling branch replacement are runtime-backed; add production replay adapters if abstract models become conformance checks |
| Route mutation/stale evidence | PM repair card, reviewer-block event, mutation writer/frontier rewrite, stale evidence ledger, sibling replacement topology, packet supersession, route-sign projection, route mutation activation model | Covered | Keep dedicated mutation card wording and stale-evidence fields aligned as new replacement strategies appear |
| Heartbeat/manual resume reentry | Stable docs/templates, runtime resume cards, router resume action, resume model/tests | Covered | Add production replay adapter later if resume evidence expands |
| Final ledger/terminal replay | PM final ledger card, reviewer final backward replay card, final ledger writer, terminal replay map, closure card, defect/role-memory/quarantine reconciliation, final user report metadata, router-loop/runtime-closure models, runtime tests | Covered | Keep closure reconciliation aligned as new ledger families are added |
| Cockpit or chat route display | Startup display answer, route diagram model/templates, startup display status writer, run-scoped `route_state_snapshot.json`, route-display refresh evidence | Partial | Startup chat route sign and canonical UI snapshot are covered; add native Cockpit rendering/integration |
| Retired assets and old state quarantine | Retired path self-check, second backup, continuation quarantine artifact | Partial | Expand quarantine into explicit imported-asset disposition when continuation imports old files |
| Skill-improvement nonblocking report | Existing templates and meta/capability models | Planned | Add runtime cards and router events |

## Working Principle

An old obligation is considered `covered` only when it has an executable
enforcement point: router state, card manifest validation, packet runtime,
FlowGuard model, unit test, install check, or a quarantine check. Protocol prose
alone is `planned` or `partially_covered`.

## Equivalent Barrier Bundle Layer

`docs/barrier_bundle_equivalence.md` defines the new barrier-bundle layer. A
bundle may group repeated control checks only when it uses
`equivalence_mode: preserve_existing_packet_semantics` and every bundled legacy
obligation still has role-scoped evidence, packet/result hash integrity,
required reviewer or FlowGuard officer approval, route-mutation stale evidence
handling, and final ledger/replay closure where applicable. The executable
model is `simulations/barrier_equivalence_model.py`.

## Next Conversion Targets

1. Native Cockpit consumption of `route_state_snapshot.json`, because the
   runtime now writes a canonical UI-readable snapshot but no desktop UI process
   consumes it yet.
2. Specialized field-level validators for future officer report families.
3. Production replay adapters for abstract route/resume models if those models
   are promoted from design checks to conformance checks.
