# Unified Progress and Parallel Liveness Plan

## Risk Intent Brief

This change protects the FlowPilot controller loop from two avoidable stalls:

- work-package waits that look dead because the controller cannot see safe
  metadata-only progress;
- heartbeat/manual-resume recovery that checks the six live roles one by one
  instead of probing them as a bounded batch.

The protected boundary is role isolation. Controller-visible progress remains a
short metadata status only; sealed packet bodies, result bodies, role-output
bodies, findings, evidence, recommendations, and role decisions stay outside
controller-visible chat and progress files. Six-role liveness may run in
parallel, but PM resume decisions still wait for all six final role records and
the crew rehydration report.

## Optimization Checklist

| Order | Optimization | Concrete Change | Done When |
| --- | --- | --- | --- |
| 1 | Make progress the default for all work packages. | Reuse the existing packet progress pattern as the standard: runtime writes baseline status at create/open/submit, roles update progress through runtime while working. | Packet work and formal role-output work both have controller-visible metadata progress by default. |
| 2 | Keep prompt distribution consistent. | Put the progress obligation in shared work-package/output-contract surfaces, not scattered one-off card patches. | Roles see the progress rule when they receive a packet or prepare a formal role output. |
| 3 | Keep controller visibility narrow. | Router wait actions expose only the matching controller-readable status artifact, not packet/result/role-output bodies or broad directories. | Every long or formal role wait has an exact progress status read grant and no sealed-body read grant. |
| 4 | Keep runtime as the progress writer. | Progress updates go through runtime commands and are validated for role, agent id, numeric progress, and safe short messages. | Manual JSON progress edits are modeled and tested as invalid. |
| 5 | Probe resume liveness as one batch. | Heartbeat/manual resume starts all six role liveness checks before waiting for individual results. | The rehydration action contract requires concurrent batch evidence for all six roles. |
| 6 | Preserve the resume join. | PM resume remains blocked until all six role records are restored or replaced, current-run memory is injected, and the crew rehydration report is written. | Parallel liveness reduces wait time but does not weaken the all-six-role gate. |

## Bug-Risk Checklist

| Risk | What Could Go Wrong | FlowGuard Must Catch |
| --- | --- | --- |
| R1 | A new work-package type has no default progress status, so controller waits look stuck. | A work-package wait with no matching status read fails. |
| R2 | The progress reminder exists for packet work but is missing from role-output preparation. | A formal role-output work item without progress prompt coverage fails. |
| R3 | Controller gets a broad directory read while waiting for progress. | Any progress visibility grant wider than the matching status artifact fails. |
| R4 | Progress status leaks sealed body content, findings, evidence, recommendations, or decisions. | Unsafe progress message/content fails. |
| R5 | A role or controller hand-edits progress JSON instead of using runtime. | Non-runtime progress writes fail. |
| R6 | Progress value is free-form, negative, or not comparable. | Non-numeric or negative progress fails. |
| R7 | Six-role liveness still happens serially during resume. | Resume liveness without concurrent batch proof fails. |
| R8 | Resume treats `timeout_unknown`, missing, cancelled, or unknown as active. | Timeout or missing liveness used as continuity fails. |
| R9 | PM resume starts before all six roles are restored/replaced and reported. | PM decision before all-six join, memory injection, report, and lifecycle reconciliation fails. |
| R10 | Replacement roles are spawned without current-run memory or common run context. | Unseeded replacement crew fails. |

## Model-First Execution Order

1. Upgrade the control-plane friction model for default progress coverage across
   packet and formal role-output work.
2. Upgrade the resume model for concurrent six-role liveness batch evidence.
3. Run model hazard checks first and confirm R1-R10 are detected.
4. Run the safe optimized model path and confirm it passes.
5. Implement production runtime/router/prompt changes in the same order.
6. After each implementation slice, run the narrow tests for that slice before
   moving to the next slice.
7. Run install sync and local source-fresh checks. Do not push to GitHub.

## Non-Goals

- Do not create an independent progress system unrelated to the existing packet
  progress pattern.
- Do not expose sealed packet, result, or role-output bodies to Controller.
- Do not use progress status as a pass/fail decision or approval signal.
- Do not remove the six-role resume gate.
- Do not change single-agent fallback semantics.
- Do not run repo-wide formatting or broad cleanup.
