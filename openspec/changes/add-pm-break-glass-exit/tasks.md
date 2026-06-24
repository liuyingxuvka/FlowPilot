## 1. OpenSpec And FlowGuard Framing

- [x] 1.1 Validate this OpenSpec change before implementation.
- [x] 1.2 Preserve the new-only/no-fallback constraint.
- [x] 1.3 Record the stop-for-user versus break-glass boundary as the acceptance rule.

## 2. Runtime Contracts

- [x] 2.1 Add `break_glass` to PM repair-decision allowed values and branch shapes.
- [x] 2.2 Add `break_glass` to PM FlowGuard-acceptance allowed values and branch shapes.
- [x] 2.3 Add `break_glass` to PM resume/stop-for-environment contract surfaces where the PM can otherwise stop.
- [x] 2.4 Reject removed or synonym decisions exactly as before.

## 3. Runtime Behavior

- [x] 3.1 Record PM `break_glass` decisions without clearing or waiving the blocker.
- [x] 3.2 Route PM `break_glass` decisions to existing `control_plane_blocker` duty.
- [x] 3.3 Keep `stop_for_user` behavior unchanged: it waits for explicit user resume.
- [x] 3.4 Ensure break-glass cannot mark PM/Reviewer/FlowGuard gates passed or mutate routes.

## 4. Cards And Prompt Surfaces

- [x] 4.1 Update PM repair guidance to list `break_glass` as a legal option.
- [x] 4.2 Update PM FlowGuard-acceptance guidance to distinguish `block`, `stop_for_user`, and `break_glass`.
- [x] 4.3 Update PM resume guidance if the resume contract exposes a stop-for-user/environment option.
- [x] 4.4 Update card coverage tests for the exact machine token and meaning boundary.

## 5. FlowGuard Models And Cartesian/Fake-AI Coverage

- [x] 5.1 Update the project-control model for PM-selected break-glass.
- [x] 5.2 Update model-test alignment obligations for the new PM exit.
- [x] 5.3 Extend fake AI response package replay with a PM `break_glass` package.
- [x] 5.4 Extend Cartesian control-plane coverage so `stop_for_user` and `break_glass` are both exercised.

## 6. Verification

- [x] 6.1 Run focused runtime unit tests for PM repair and PM FlowGuard acceptance.
- [x] 6.2 Run fake AI runtime replay and Cartesian control-plane checks.
- [x] 6.3 Run required FlowGuard meta/capability checks for control-flow changes.
- [x] 6.4 Rebuild/check topology if touched surfaces require it.

## 7. Sync And Local Version

- [x] 7.1 Sync repository-owned FlowPilot files to the installed local skill.
- [x] 7.2 Verify install sync and installed FlowPilot checks.
- [x] 7.3 Commit the scoped local Git change without reverting peer-agent work.
