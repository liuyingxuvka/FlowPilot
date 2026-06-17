## Context

The terminal backward replay Reviewer card correctly tells the Reviewer to keep
top-level `passed=false` when any replay segment blocks closure. The core
runtime contract currently rejects that shape before `_apply_valid_packet_result`
can classify the result as a semantic blocker. The installed skill also had a
temporary terminal reissue improvement that has not been restored to the source
tree, so source-driven installation can reintroduce the missing
`segment_targets` problem.

## Goals / Non-Goals

**Goals:**

- Make terminal backward replay validation branch-aware: pass branch closes,
  block branch records a semantic terminal blocker.
- Preserve segment parity, reviewer identity, direct evidence, PM segment
  decision, blocker, and restart-policy requirements in both branches.
- Keep terminal closure unavailable after any blocking replay result.
- Update FlowGuard/model-test alignment so the exact negative branch is covered.
- Sync the repository-owned installed skill only after source validation.

**Non-Goals:**

- Do not add legacy aliases or accept old generic result bodies.
- Do not make a terminal blocking replay count as successful final evidence.
- Do not introduce a new packet family, role, or closure workflow.
- Do not archive unrelated in-progress OpenSpec changes.

## Decisions

1. Branch on `payload.passed` after validating that it is a boolean.
   - Rationale: top-level `passed` is already the review outcome field used by
     `_parse_packet_outcome`; allowing `false` lets the existing semantic
     blocker path run without inventing a new signal.
   - Alternative rejected: add a new `decision=block` field. That would add a
     second authority surface and conflict with the current new-only contract.

2. Require exact `segment_targets` parity for both branches.
   - Rationale: a blocking result is only actionable if it is bound to the
     runtime-issued replay map. Missing or unexpected segments remain
     mechanical errors.
   - Alternative rejected: allow partial blocking reports. That would make it
     unclear whether unmentioned segments were reviewed.

3. Require `pm_segment_decision=continue` on pass segments and a repair decision
   on failed segments.
   - Rationale: passing segments can advance, while failed segments must carry
     PM-repair intent into the existing blocker flow.
   - Alternative rejected: infer repair from `passed=false` alone. That would
     lose the PM decision that final replay is designed to record.

4. Keep reissue packets in the same family but specialize terminal replay body
   data when route scope is `terminal_backward_replay`.
   - Rationale: mechanical correction still belongs to the same packet family;
     preserving `segment_targets` makes the correction possible.
   - Alternative rejected: create a new terminal reissue family. That broadens
     the protocol surface without changing the underlying responsibility.

## Risks / Trade-offs

- A branch-aware contract is slightly more complex than a `passed=true` gate.
  Mitigation: add direct tests for pass, valid block, invalid block, and reissue
  target preservation.
- Fake E2E can still miss the branch if it only generates happy-path terminal
  results. Mitigation: add a controlled negative fake-run or focused helper test
  that submits a valid terminal blocker.
- Model-test alignment can overclaim if it only lists the symbol. Mitigation:
  add an explicit negative evidence row bound to the terminal result contract.

## Migration Plan

1. Update OpenSpec proposal, design, specs, and tasks.
2. Patch source runtime and contract catalog.
3. Add focused tests and model-test alignment evidence.
4. Run focused runtime tests and FlowGuard checks.
5. Sync installed FlowPilot from source, then run install check and installed
   freshness audit serially.
6. Update adoption logs and task status after validation.
