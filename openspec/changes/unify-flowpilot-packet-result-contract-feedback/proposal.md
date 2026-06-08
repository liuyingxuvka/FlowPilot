## Why

The current FlowPilot packet-result source of truth covers generic result
fields, while the current role output contracts and role cards require richer
Reviewer and FlowGuard operator reports. This can let fake AI rehearsals or
runtime happy paths pass with only `decision` and `pm_visible_summary`, even
though the current Reviewer and FlowGuard contracts require independent
challenge, model boundary, skipped checks, missing test kinds, confidence
boundary, and contract self-check evidence.

## What Changes

- Keep the current FlowPilot trunk unchanged: PM node context package,
  pre-work FlowGuard, Worker, post-result FlowGuard, independent Reviewer, PM
  disposition.
- Fold the old root-acceptance-contract idea into the current
  `high_standard_contract` path. The current contract must preserve hard user
  intent, forbidden scope, completion meaning, and evidence rules instead of
  treating a generic "complete the user request" row as enough.
- Require route nodes, node acceptance plans, and node context packages to
  project the accepted high-standard and skill-standard obligations into the
  actual Worker, FlowGuard, Reviewer, and PM disposition path.
- Make packet-result families for `review` and `flowguard_check` point to the
  existing role report fields instead of accepting a generic minimal result.
- Make PM disposition absorb current Worker, FlowGuard, and Reviewer evidence
  before accepting a node, including residual risks, missing tests, review
  findings, semantic downgrade risk, and hard requirement coverage.
- Extend route deliverable checks inside the existing `deliverable_checks`
  surface so final closure can test product facts, forbidden artifacts,
  freshness, JSON fields, and required/forbidden text without creating a
  second final-checker path.
- Make the final requirement evidence matrix and final route-wide gate ledger
  semantic closure gates: hard requirements need direct evidence or explicit
  waiver, not only an accepted node id.
- Require terminal backward replay before broad completion when high-standard
  flow is active, so final closure starts from delivered output and walks back
  to the frozen user intent.
- Keep runtime/router ownership mechanical: required field paths, forbidden old
  fields, current packet family, missing field repair, and PM-visible summary
  presence.
- Keep Reviewer and FlowGuard operator semantic ownership unchanged: Reviewer
  judges human quality; FlowGuard operator judges model/process/state evidence.
- Update fake AI success bodies and negative tests so rehearsal cannot mask a
  missing role-report contract, empty/generic field content, missing PM
  absorption, forbidden UI creation, stale final reports, or missing
  deliverable proof.
- Extend FlowGuard field/model evidence so role report body fields are modeled
  as current packet-result fields, and so the high-standard contract ->
  route-node -> node-context-package -> role-report -> PM-disposition ->
  final-ledger chain is modeled as one current path.

## Non-Goals

- No compatibility route for old Reviewer or FlowGuard packet shapes.
- No fallback parser that converts generic `decision`-only bodies into current
  rich reports.
- No new role, ledger, or parallel workflow.
- No semantic quality judgement in runtime.
- No restoration of the old FlowPilot Router or old root-contract authority as
  a separate active path.
- No separate "ultimate checker" outside the current closure ledger/matrix and
  terminal backward replay surfaces.

## Impact

- `skills/flowpilot/assets/flowpilot_core_runtime/packet_result_contracts.py`
- `skills/flowpilot/assets/flowpilot_core_runtime/runtime.py`
- `skills/flowpilot/assets/flowpilot_core_runtime/fake_e2e.py`
- FlowPilot role output contract index and role-output schema helpers
- FlowGuard field/model alignment checks in `simulations/`
- Runtime, fake AI, role-output, and OpenSpec tests
