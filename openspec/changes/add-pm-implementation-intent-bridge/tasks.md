## 1. OpenSpec And FlowGuard Preflight

- [x] 1.1 Run FlowGuard package/project preflight and upgrade the project record when the installed package is newer.
- [x] 1.2 Record existing model ownership, downstream FlowGuard route, and field-lifecycle boundary for the implementation-intent bridge.

## 2. Prompt Cards And Role Boundaries

- [x] 2.1 Add the PM implementation intent prompt card.
- [x] 2.2 Add the FlowGuard Operator target-realization modeling prompt card.
- [x] 2.3 Add the PM target-realization model decision prompt card.
- [x] 2.4 Add the Reviewer implementation intent challenge prompt card.
- [x] 2.5 Update product-model decision, route skeleton, route process check, node acceptance, role-work request, worker, final ledger, and reviewer cards to consume realization obligations.
- [x] 2.6 Update runtime card manifest entries for the new prompt cards.

## 3. Templates And Contracts

- [x] 3.1 Add PM implementation intent and PM target-realization decision templates.
- [x] 3.2 Extend FlowGuard modeling request/report templates for target-realization modeling.
- [x] 3.3 Extend node acceptance, packet, final ledger, and terminal replay templates with realization-obligation projections.
- [x] 3.4 Update output contract and control transaction registry surfaces for the new current-contract events and gates.

## 4. Runtime Planning Flow

- [x] 4.1 Wire the legal planning transition from accepted product model to PM implementation intent.
- [x] 4.2 Wire the FlowGuard target-realization request/report loop.
- [x] 4.3 Wire PM and Reviewer acceptance before route skeleton drafting.
- [x] 4.4 Reject route skeleton and downstream work when implementation intent or accepted realization obligations are missing.

## 5. FlowGuard Models And Tests

- [x] 5.1 Add planning-quality hazards for skipped intent, PM role leakage, FlowGuard intent mismatch, Reviewer omission, route/node/worker/final obligation loss.
- [x] 5.2 Update meta/capability model state where planning flow legality changes.
- [x] 5.3 Add or update focused unit tests for prompt cards, role-output contracts, router legal actions, planning quality, and closure obligation propagation.
- [x] 5.4 Rebuild the project topology after model, prompt, and runtime surface changes.

## 6. Install Sync And Validation

- [x] 6.1 Run focused FlowGuard checks and unit tests for changed surfaces.
- [x] 6.2 Run heavyweight meta and capability checks through the background log contract and inspect final artifacts.
- [x] 6.3 Run repository-owned FlowPilot install sync, install audit, and install check.
- [x] 6.4 Re-run FlowGuard project audit and record adoption evidence.

## 7. Closure

- [x] 7.1 Mark OpenSpec tasks complete only after matching implementation and validation evidence exists.
- [x] 7.2 Run final git status/diff review without reverting peer work.
- [x] 7.3 Perform predictive KB postflight and record any reusable lesson or route gap.
