## 1. Prompt And Policy Surfaces

- [x] 1.1 Add one shared replayability rule to common FlowPilot packet/package instructions.
- [x] 1.2 Update reviewer guidance to inspect existing run results first and rerun only targeted evidence.
- [x] 1.3 Update PM blocker guidance to prefer existing Controller break-glass for control-plane replayability failures before user stop.

## 2. Runtime Stop Semantics

- [x] 2.1 Harden stopped-blocker recovery so `stop_for_user` does not auto-reissue PM repair decisions during ordinary patrol/resume.
- [x] 2.2 Keep explicit user-requested stopped-blocker recovery available with recorded user intent.

## 3. FlowGuard And Tests

- [x] 3.1 Add focused FlowGuard coverage for replayable artifact policy, targeted reviewer rerun, control-plane break-glass routing, and hard user stop.
- [x] 3.2 Add or update unit tests for replayability prompt text, PM guidance, reviewer guidance, and stopped-blocker recovery behavior.

## 4. Validation And Sync

- [x] 4.1 Run focused tests and FlowGuard checks for the touched surfaces.
- [x] 4.2 Run install checks and sync the source repo-owned skill to the local installed skill.
- [x] 4.3 Verify installed skill matches source and record final git/KB status.
