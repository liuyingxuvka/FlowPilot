## 1. Legacy Boundary And Scope

- [x] 1.1 Create a new legacy backup snapshot before source edits.
- [x] 1.2 Record allowed reuse and explicit non-reuse boundaries for old assets,
  old runtime state, and old validation evidence.
- [x] 1.3 Keep old `.flowpilot/` runtime state read-only and out of the new
  protocol's current evidence chain.

## 2. OpenSpec Contract

- [x] 2.1 Write proposal, design, tasks, and capability requirements for the
  clean AI project protocol kernel.
- [x] 2.2 Validate the OpenSpec change strictly before claiming the contract is
  usable.

## 3. Protocol Kernel Assets

- [x] 3.1 Add the readable protocol contract under
  `skills/flowpilot/assets/ai_project_protocol/`.
- [x] 3.2 Add schema examples for black-box ledger entries, dynamic agent
  leases, task packets, result packets, review reports, and FlowGuard route
  requests.
- [x] 3.3 Add a FlowGuard route scheduler table that says what is being modeled
  and which FlowGuard sub-skill owns the check.

## 4. FlowGuard Model And Fake-Agent Rehearsal

- [x] 4.1 Add an executable model for dynamic agent lifecycle, packet lifecycle,
  review isolation, route mutation, evidence freshness, and final backward
  closure.
- [x] 4.2 Add fake-agent scenarios for success, missing ACK, ACK without output,
  wrong packet shape, stale output, closed-agent output, weak review,
  self-review, stale evidence reuse, route mutation with old packets, and final
  closure gaps.
- [x] 4.3 Ensure the model rejects bad paths and accepts the intended happy path.

## 5. Tests And Regressions

- [x] 5.1 Add focused tests for protocol assets and model results.
- [x] 5.2 Run the AI project protocol checks and focused tests.
- [x] 5.3 Run heavyweight Meta and Capability regressions under the repository
  background log contract and inspect final artifacts.
- [x] 5.4 Validate OpenSpec after implementation.

## 6. Install Sync And Local Git

- [x] 6.1 Update version/changelog or equivalent release notes for the local
  protocol-kernel addition.
- [x] 6.2 Sync the repository-owned FlowPilot skill into the installed local
  skill and run install audit/check steps.
- [x] 6.3 Review final git scope, stage intended files only, and create a local
  git commit without push, tag, deploy, or release.
