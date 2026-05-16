## 1. FlowGuard Boundary

- [x] 1.1 Add startup-control model coverage that rejects full `user_intake` PM release before `startup_activation_approved`.
- [x] 1.2 Add prompt-isolation model coverage that preserves early startup metadata but rejects full task-body delivery to PM before activation.
- [x] 1.3 Run focused FlowGuard startup/prompt checks and record Meta/Capability as skipped by user direction.

## 2. Runtime And Cards

- [x] 2.1 Update Router startup release logic so the full `user_intake` packet remains sealed until startup activation approval.
- [x] 2.2 Update PM startup-intake and activation cards so pre-activation PM work uses startup metadata, not the full task body.
- [x] 2.3 Ensure post-activation material scan entry confirms full PM user intake delivery before material/product/route work.

## 3. Tests And Documentation

- [x] 3.1 Update router runtime tests and helpers for the new startup order.
- [x] 3.2 Update packet/prompt/card tests that describe user intake visibility.
- [x] 3.3 Update design/protocol docs and FlowGuard adoption notes for the new boundary.

## 4. Sync And Verification

- [x] 4.1 Run focused Python tests and install checks; skip heavy Meta/Capability simulations by user direction.
- [x] 4.2 Sync the local installed FlowPilot skill from the repository.
- [x] 4.3 Re-run local install sync/check validation and review the final diff.
