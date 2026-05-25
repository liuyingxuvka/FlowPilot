## 1. Grounding

- [x] 1.1 Verify real FlowGuard import, clean git state, and peer-agent coordination boundaries.
- [x] 1.2 Read the existing synthetic replay suite, coverage matrix, and model-test alignment results.
- [x] 1.3 Identify the smallest set of system-level stories that extends single-branch exception coverage.

## 2. System-Level Replay Packages

- [x] 2.1 Add a valid-envelope/bad-content replay story that rejects completion.
- [x] 2.2 Add a stacked-blocker replay story that proves control-plane preemption and preserves lower-priority unresolved evidence.
- [x] 2.3 Add a failed-PM-repair-loop story that escalates or remains blocked after retry budget exhaustion.
- [x] 2.4 Add a restart/stale-state replay story that rejects old packet/body/disposition evidence.
- [x] 2.5 Add a peer/parallel-write interference story that rejects foreign or stale authority.
- [x] 2.6 Add a terminal-total-gate story that rejects completion while any dirty ledger or incomplete background artifact remains.

## 3. Matrix and Evidence Gates

- [x] 3.1 Extend coverage matrix rows with `story_level`, `recovery_loop`, `story_steps`, and `terminal_expectation`.
- [x] 3.2 Add system-level rows for all new story packages.
- [x] 3.3 Add known-bad matrix cases for missing system replay metadata and live-completion overclaiming.
- [x] 3.4 Refresh generated synthetic coverage matrix JSON.

## 4. Validation

- [x] 4.1 Run focused system replay tests.
- [x] 4.2 Run coverage matrix tests.
- [x] 4.3 Run model-test alignment and fast tier.
- [x] 4.4 Run Meta and Capability model regressions in background and inspect final artifacts.
- [x] 4.5 Run relevant router child slices for foreground, terminal, route, and material recovery.

## 5. Sync and Finalization

- [x] 5.1 Validate OpenSpec change.
- [x] 5.2 Synchronize repository-owned local FlowPilot skill.
- [x] 5.3 Run install sync audit and install check serially.
- [x] 5.4 Record FlowGuard adoption evidence and predictive-KB postflight.
- [x] 5.5 Commit local git state without pushing or publishing.
