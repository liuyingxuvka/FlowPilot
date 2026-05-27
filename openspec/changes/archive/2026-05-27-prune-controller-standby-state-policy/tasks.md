## 1. Model And Route Grounding

- [x] 1.1 Reuse the existing Controller patrol FlowGuard model as the safety boundary for standby pruning.
- [x] 1.2 Confirm real FlowGuard import and current git/coordination state before behavior-bearing edits.
- [x] 1.3 Classify this round as internal branch pruning, not a file split or daemon authority change.

## 2. Runtime Branch Pruning

- [x] 2.1 Add internal standby state and foreground mode policy helpers.
- [x] 2.2 Refactor `_build_foreground_controller_standby_snapshot` to use the helpers while preserving returned fields.
- [x] 2.3 Keep `controller_patrol_timer` behavior compatible and avoid adding a second progress authority.

## 3. Validation And Sync

- [x] 3.1 Run focused source/unit checks for the new helper behavior.
- [x] 3.2 Run the Controller patrol FlowGuard checks.
- [x] 3.3 Run focused foreground Controller runtime tests.
- [x] 3.4 Run relevant structure checks and a background Meta check if the standby control-flow evidence needs parent confirmation.
- [x] 3.5 Sync repo-owned FlowPilot into the local installed skill and run install freshness checks.
- [x] 3.6 Record FlowGuard adoption evidence, KB postflight notes, and local git status.
