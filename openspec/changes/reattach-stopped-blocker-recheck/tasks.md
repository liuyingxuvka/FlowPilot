## 1. OpenSpec And FlowGuard

- [x] 1.1 Add OpenSpec deltas for stopped-blocker recheck reattachment.
- [x] 1.2 Add focused FlowGuard model coverage for stopped -> awaiting_recheck -> owner pass -> cleared.

## 2. Runtime And CLI

- [x] 2.1 Add `reattach_required_recheck` to `resolve-stopped-blocker`.
- [x] 2.2 Preserve and restore `pm_stop_previous_status` around `stop_for_user`.
- [x] 2.3 Force fresh FlowGuard/Reviewer recheck packets during reattachment.
- [x] 2.4 Keep reattachment user-requested and non-clearing.

## 3. Prompt And Skill Guidance

- [x] 3.1 Update FlowPilot skill command documentation.
- [x] 3.2 Update Controller break-glass exit guidance.

## 4. Validation And Sync

- [x] 4.1 Add focused unit tests for reattachment behavior and negative cases.
- [x] 4.2 Run focused FlowGuard checks and runtime tests.
- [x] 4.3 Run install sync/check and verify installed skill matches source.
- [x] 4.4 Record FlowGuard adoption evidence and final KB postflight.
