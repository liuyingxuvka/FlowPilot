## 1. Prompt Boundary

- [x] 1.1 Update the FlowPilot skill startup-intake instruction to return to Router daemon status and the Controller action ledger after the UI closes.
- [x] 1.2 Update Router-generated startup-intake summary/plain instruction text to use the same ledger-oriented wording.

## 2. Regression Coverage

- [x] 2.1 Add focused tests for direct startup action wording and daemon-projected Controller row wording.
- [x] 2.2 Strengthen prompt-boundary checks so startup intake instructions do not regress to direct-apply wording.

## 3. Validation And Sync

- [x] 3.1 Run focused tests and prompt/model boundary checks.
- [x] 3.2 Sync the installed local FlowPilot skill and audit the sync.
- [x] 3.3 Review git state for compatible peer-agent changes before staging or committing.
