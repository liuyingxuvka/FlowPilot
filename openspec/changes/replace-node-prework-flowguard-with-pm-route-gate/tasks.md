## 1. Runtime and Contracts

- [x] 1.1 Remove ordinary worker release dependency on `node_prework_flowguard`.
- [x] 1.2 Remove ordinary router next-action emission of `issue_node_prework_flowguard_packet`.
- [x] 1.3 Add `pm_flowguard_acceptance.pm_flowguard_acceptance` contract with strict accepted and `redesign_route` branches.
- [x] 1.4 Add PM FlowGuard acceptance packet issuance after structural FlowGuard pass and before Reviewer review.
- [x] 1.5 Ensure FlowGuard block on a structural decision prevents route mutation and returns to current repair/block handling.
- [x] 1.6 Allow `task.node_acceptance_plan` to choose either `decision=pass` with `node_context_package` or `decision=redesign_route` with strict `route_plan`.
- [x] 1.7 Apply staged route redesign only after FlowGuard pass, PM absorption, Reviewer pass, and system validation.
- [x] 1.8 Reject optional/uncertain FlowGuard decision fields and old node-prework compatibility paths.

## 2. Prompts and Public Guidance

- [x] 2.1 Update PM role and node acceptance cards with the binary path: keep structure -> node package; change structure -> strict route plan.
- [x] 2.2 Update FlowGuard Operator cards to say structural reports support PM and cannot mutate routes or release workers.
- [x] 2.3 Update Reviewer cards to block missing PM absorption, shallow/over-deep decomposition, and unreviewed structural route changes.
- [x] 2.4 Update HANDOFF and protocol docs so they no longer describe mandatory per-node pre-work FlowGuard.

## 3. Tests and Models

- [x] 3.1 Update high-standard runtime tests for ordinary node plan to worker without pre-work FlowGuard.
- [x] 3.2 Add focused tests for node acceptance `redesign_route`, PM repair redesign, PM disposition redesign, FlowGuard block, PM absorption missing, PM rewrite, and optional FlowGuard rejection.
- [x] 3.3 Update fake-AI and black-box rehearsal packet-shape tests for `pm_flowguard_acceptance`.
- [x] 3.4 Replace the old pre-work FlowGuard model semantics with route-redesign FlowGuard/PM-absorption semantics.
- [x] 3.5 Update model-test-alignment declarations to point to the new obligations and tests.

## 4. Validation

- [x] 4.1 Run focused runtime tests that cover node acceptance, route mutation, packet contracts, fake-AI rehearsal, and recursive execution.
- [x] 4.2 Run affected FlowGuard model runners and model-test-alignment checks.
- [x] 4.3 Run project-control meta checks because the route-control flow changes.
- [x] 4.4 Run capability checks because prompts/capability routing guidance changes.
- [x] 4.5 Rebuild and check topology after runtime/model/test/prompt artifacts change.
- [x] 4.6 Sync installed FlowPilot skill and run install/audit checks.
