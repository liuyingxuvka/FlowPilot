## 1. OpenSpec And FlowGuard Model

- [x] 1.1 Create the OpenSpec proposal, design, spec, and task artifacts for
  PM-owned test obligation disposition.
- [x] 1.2 Add a focused FlowGuard model/check for the FlowPilot test
  obligation ownership chain.
- [x] 1.3 Run the focused FlowGuard check and inspect counterexamples before
  editing runtime cards further.

## 2. Runtime Cards And Contracts

- [x] 2.1 Update PM node-acceptance, officer request/report, role-work request,
  evidence-quality, and final-ledger cards with the test obligation matrix and
  disposition rules.
- [x] 2.2 Update worker role cards so worker test-maintenance packets return
  test obligation coverage rows without expanding beyond packet scope.
- [x] 2.3 Update reviewer cards so node completion and evidence reviews block
  undispositioned or unsupported test obligation rows.
- [x] 2.4 Update `contract_index.json` so worker current-node and PM role-work
  results require test obligation coverage when the source packet/request
  declares test obligations.

## 3. Ordinary Regression Tests

- [x] 3.1 Add focused tests that check cards and contracts expose the new
  authority chain.
- [x] 3.2 Run the focused tests and fix defects they expose.

## 4. Validation, Sync, And Local Git

- [x] 4.1 Run OpenSpec strict validation for this change.
- [x] 4.2 Run focused FlowGuard and relevant FlowPilot checks; run heavy model
  regressions in the repository background-log contract when practical.
- [x] 4.3 Sync repo-owned FlowPilot skill files into the local installed skill
  and run install freshness checks.
- [x] 4.4 Record FlowGuard adoption evidence and KB postflight notes.
- [x] 4.5 Capture the intended local git changes without reverting or
  overwriting parallel-agent work.
