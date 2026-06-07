## 1. Visual Tokens And Layout

- [x] 1.1 Tune startup intake WPF colors, typography, spacing, logo scale, button copy, and request-field dimensions in the active UI script.
- [x] 1.2 Mirror the same visual polish in the desktop preview script.

## 2. Visual And Runtime Validation

- [x] 2.1 Run startup intake FlowGuard checks and WPF smoke checks.
- [x] 2.2 Capture and inspect the polished startup UI screenshot; iterate if spacing, text, or proportions look wrong.

## 3. Local Sync And Git

- [x] 3.1 Sync the repository-owned installed FlowPilot skill and run local install verification.
  - `install_flowpilot.py --sync-repo-owned --json` refreshed the installed skill; `audit_local_install_sync.py --json` and `install_flowpilot.py --check --skip-self-check --json` passed. Full `check_install.py --json` remains blocked by pre-existing project topology staleness across unrelated dirty files, so the topology rebuild is intentionally not folded into this UI-only change.
- [x] 3.2 Stage only this change's files and create a local git commit without absorbing unrelated worktree changes.
