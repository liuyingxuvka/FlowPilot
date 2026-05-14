## 1. Router Display Behavior

- [x] 1.1 Change startup waiting `sync_display_plan` so it remains an internal/host visible-plan sync and no longer emits `FlowPilot Startup Status` user-dialog text.
- [x] 1.2 Preserve `display_plan.json`, route authority metadata, and controller no-invented-route safeguards.
- [x] 1.3 Keep startup `FlowPilot Route Sign` as the only required user-dialog display before PM route activation.

## 2. FlowGuard Model Updates

- [x] 2.1 Update route-display FlowGuard model hazards and invariants for internal-only startup waiting state.
- [x] 2.2 Rerun route-display checks and inspect results.

## 3. Tests And Sync

- [x] 3.1 Update focused router runtime tests for hidden startup waiting card and unchanged canonical route display.
- [x] 3.2 Run focused unit tests and OpenSpec status/validation.
- [x] 3.3 Synchronize the local installed FlowPilot skill and run install/audit checks.
