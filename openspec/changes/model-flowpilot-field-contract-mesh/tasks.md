## 1. Field Model

- [x] 1.1 Add a parent FlowGuard field contract model for current transition fields.
- [x] 1.2 Add a child field mesh that classifies every observed field by model family and importance.
- [x] 1.3 Bind critical fields to current code validators and fail on unbound fields.
- [x] 1.4 Model old FlowPilot fields only as negative hazards, not accepted production paths.

## 2. Entry And Install Surface

- [x] 2.1 Ensure role handoff commands use the public `flowpilot_new.py` entrypoint after split.
- [x] 2.2 Require split entrypoint modules in install checks.
- [x] 2.3 Add tests that prevent router runtime tests from synthesizing default agent ids.

## 3. Validation

- [x] 3.1 Run field contract checks.
- [x] 3.2 Run field mesh checks.
- [x] 3.3 Run focused entrypoint, install-surface, and router-runtime agent id tests.
