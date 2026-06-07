## 1. OpenSpec And FlowGuard Preflight

- [x] 1.1 Verify real FlowGuard package/schema, upgrade project adoption records when installed version is newer, and audit project status.
- [x] 1.2 Read current topology, handoff, field-contract, packet-contract, role-dispatch, fake-AI, and status-projection baselines.
- [x] 1.3 Record this OpenSpec change and keep tasks updated as implementation proceeds.

## 2. FlowGuard Models And Field Lifecycle

- [x] 2.1 Extend information-flow modeling so packet sufficiency includes input reads, top-level output fields, branch child shapes, missing-information exits, downstream consumer, and status projection.
- [x] 2.2 Extend field contract/field mesh rows for branch shape fields, route-plan child fields, dispatch fields, staged gate fields, and removed/negative-only old fields.
- [x] 2.3 Extend model-test alignment so branch-contract shape, reissue correction, role dispatch, and staged projection obligations bind to code, prompts, fake-AI, and tests.

## 3. Runtime Contract And Reissue Implementation

- [x] 3.1 Add packet-contract branch metadata for conditional outputs, including `pm_repair_decision.decision=redesign_route`.
- [x] 3.2 Make `current_handoff_contract.required_report_contract` expose branch-specific valid shapes.
- [x] 3.3 Make mechanical contract failures and reissue packets carry branch name, failed path, concrete reason, and branch-specific correction shape.
- [x] 3.4 Keep runtime rejection strict: no old wrappers, legacy aliases, missing-field defaults, or hidden fake-AI success fields.

## 4. Role Dispatch And Status Projection

- [x] 4.1 Add or expose one normal current role-dispatch command that records assignment and lease in one public step.
- [x] 4.2 Update lifecycle guard/foreground duty so normal next action is the single dispatch action, not a public resolve/lease pair.
- [x] 4.3 Preserve diagnostic assignment helpers without making them a normal current workflow.
- [x] 4.4 Fix staged PM gate final-preflight projection so accepted gate source packets are not misreported as current-target violations while their gate is pending.
- [x] 4.5 Add negative projection checks for stale accepted packet targets that are not justified by a pending staged gate.

## 5. Prompts, Cards, And Install Surfaces

- [x] 5.1 Update Controller card and action-ledger prompt to name the single dispatch action and current handoff contract.
- [x] 5.2 Update PM, FlowGuard operator, Reviewer, and Worker cards to consume branch shapes and authorized input materials from `current_handoff_contract`.
- [x] 5.3 Update packet identity boundary prompt to remove normal-path resolve/lease wording and forbid hidden old shapes.
- [x] 5.4 Update install checks if new split modules, commands, or prompt assets are required.
- [x] 5.5 Remove obsolete heartbeat/startup-gate wording from current FlowPilot reference surfaces and add coverage that blocks reintroduction.

## 6. Fake AI, Unit, Model, And Replay Tests

- [x] 6.1 Add fake-AI branch-shape success and failure rows for `redesign_route.route_plan`.
- [x] 6.2 Add fake-AI negative rows for hidden branch fields, old wrappers, missing branch child fields, and stale status projection.
- [x] 6.3 Add runtime unit tests for branch handoff metadata, branch-aware reissue correction, single dispatch action, and staged-gate projection.
- [x] 6.4 Add live-style historical replay for the observed `packet-0020` through `packet-0024` route-plan correction and staged FlowGuard gate path.
- [x] 6.5 Update existing tests that assert the old public resolve/lease next-action sequence.

## 7. Validation, Sync, And Git Version

- [x] 7.1 Run targeted unit tests for runtime contracts, new entrypoint, high-standard control flow, fake-AI rehearsal, field contract, and role dispatch.
- [x] 7.2 Run affected FlowGuard model checks, FieldContract, FieldMesh, information-flow alignment, Model-Test Alignment, and topology build/check.
- [x] 7.3 Run install sync/audit/check scripts and update local installed FlowPilot assets.
- [x] 7.4 Update version/changelog/adoption logs as needed.
- [x] 7.5 Inspect peer-agent changes, stage only intended compatible changes, commit the complete local Git version, and report validation evidence.
