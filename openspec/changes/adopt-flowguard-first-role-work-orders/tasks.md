## 1. OpenSpec And FlowGuard Grounding

- [x] 1.1 Validate the OpenSpec change artifacts and keep the proposal, design, specs, and tasks internally consistent.
- [x] 1.2 Record FlowGuard existing-model/development-process grounding for the FlowGuard-first work-order rollout.

## 2. Shared FlowGuard-First Prompt Protocol

- [x] 2.1 Add shared FlowGuard work-order/report guidance for core runtime cards.
- [x] 2.2 Update PM core and phase cards so non-trivial product, process, route, node, repair, evidence, resume, and closure decisions cite FlowGuard work orders/reports or scoped non-required reasons.
- [x] 2.3 Update Product and Process FlowGuard Officer cards so they execute FlowGuard work orders, select the smallest applicable FlowGuard route, and preserve PM authority.
- [x] 2.4 Update Reviewer cards so FlowGuard-backed gates check report existence, scope, freshness, skipped checks, progress-only evidence, and PM acceptance.
- [x] 2.5 Update Worker and Controller cards so Workers return packet-scoped FlowGuard obligation coverage and Controller remains status-only.
- [x] 2.6 Update event cards so FlowGuard-backed reviewer/PM events carry work-order/report traceability.

## 3. Focused Runtime Card Validation

- [x] 3.1 Add focused card coverage tests for required FlowGuard work-order/report vocabulary on core cards.
- [x] 3.2 Add guard tests that Officer, Reviewer, Worker, and Controller cards do not gain PM route/gate authority from FlowGuard language.

## 4. Focused FlowGuard Model Evidence

- [x] 4.1 Add a focused FlowGuard model/check for the role work-order/report obligation chain.
- [x] 4.2 Add known-bad scenarios for missing work order, stale report, progress-only evidence, reviewer bypass, worker route mutation, officer gate approval, and controller report interpretation.

## 5. Validation And Synchronization

- [x] 5.1 Run OpenSpec validation for the new change.
- [x] 5.2 Run focused card and FlowGuard model tests for this change.
- [x] 5.3 Start heavyweight meta/capability regressions in background artifacts when source changes are ready.
- [x] 5.4 Synchronize the local installed FlowPilot skill from the repository-owned source and audit install freshness.
- [x] 5.5 Recheck git status and document owned changes without reverting parallel agent work.
