## 1. Startup Intake Provenance

- [x] 1.1 Add interactive/headless provenance metadata to startup intake result, receipt, and envelope artifacts.
- [x] 1.2 Make the headless helper write diagnostic-only metadata that formal startup cannot accept.

## 2. Router Enforcement

- [x] 2.1 Reject confirmed startup intake results that are missing interactive native provenance.
- [x] 2.2 Reject headless or formal-disallowed startup intake results before startup answers are recorded.
- [x] 2.3 Preserve cancelled startup handling for interactive UI cancellation while rejecting non-interactive cancel substitutes.

## 3. Prompt and Model Coverage

- [x] 3.1 Update FlowPilot prompt guidance to forbid substituting headless/scripted/chat-generated intake in formal startup.
- [x] 3.2 Update the FlowGuard startup intake model with the headless-bypass state and known-bad hazard.

## 4. Tests and Sync

- [x] 4.1 Update formal startup test fixtures with interactive provenance.
- [x] 4.2 Add runtime tests that reject headless confirmed startup intake.
- [x] 4.3 Run focused FlowGuard and pytest regressions, excluding Meta and Capability simulations.
- [x] 4.4 Sync the installed FlowPilot skill and verify local install sync.
