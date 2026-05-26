## 1. OpenSpec And FlowGuard Grounding

- [x] 1.1 Validate the OpenSpec change and keep the scope tied to existing repair/wait capabilities.
- [x] 1.2 Add FlowGuard model-miss evidence for the observed no-producer role reissue and generalized empty follow-up wait.

## 2. Runtime Implementation

- [x] 2.1 Add repair transaction producer validation so role-produced follow-up waits cannot commit without concrete producer evidence.
- [x] 2.2 Ensure material-scan failed self-check rework requires packet reissue, operation replay, bounded work packet, or explicit blocker/terminal outcome.
- [x] 2.3 Preserve valid packet reissue and existing replay paths while adding producer evidence to exposed follow-up waits where applicable.

## 3. Tests And Regression Coverage

- [x] 3.1 Add focused regression tests for the observed `role_reissue` without replacement work and expected rejection.
- [x] 3.2 Add focused tests that keep valid material `packet_reissue` behavior green.
- [x] 3.3 Add or update model/test alignment evidence for the new empty-wait obligation.

## 4. Validation And Sync

- [x] 4.1 Run focused unit/runtime tests for control blockers and material modeling.
- [x] 4.2 Run relevant FlowGuard model checks and background heavyweight checks where practical, then inspect completion artifacts.
- [x] 4.3 Sync the local installed FlowPilot skill, run install audit/check, inspect git status, and record KB postflight.
