## Why

FlowPilot currently creates clean repair nodes, but PM repair packets can lose
the concrete reason that caused the repair. In the observed ProjectRadar loop,
Reviewer reported a specific stale path repair, yet the PM-facing repair packet
only carried a generic failure phrase. PM then copied the old context into each
new repair node and the same small defect repeated.

At the same time, PM cannot make a formal repair judgement from a short summary
alone. The summary is useful for finding the issue quickly, but the formal
decision still requires the role to open the authorized sealed result/report
body through runtime.

## What Changes

- Require formal non-PM role result bodies to include a role-authored
  `pm_visible_summary` list.
- Treat a missing or malformed `pm_visible_summary` as a current result
  contract failure that blocks the result and reissues the same current packet
  family.
- Propagate only role-authored summary text into PM packets through
  `recent_role_report_summary`; runtime validates and relays but does not
  generate prose summaries.
- Keep `authorized_result_reads` and `open-result` as the formal sealed-body
  judgement path. PM repair packets can carry both the quick summary and a
  required authorized read of the blocking report body.
- Preserve concrete structured role guidance, such as
  `blocking_findings[].required_repair`, in the PM-facing blocker and repair
  packet.
- Keep every repair on a new repair node when PM chooses repair.

## Capabilities

### Modified Capabilities

- `role-output-transaction-boundaries`: formal role results carry
  role-authored PM-visible summaries, and downstream roles can open explicitly
  authorized result bodies for formal judgement.
- `flowpilot-packet-review-flow`: PM packets carry recent summaries for quick
  navigation and authorized result-read grants for formal body inspection.
- `blocker-repair-policy`: PM repair-decision packets preserve concrete role
  repair guidance while still requiring PM to open the blocking body when the
  packet grants that read.

## Impact

- Runtime result contract and PM packet construction in
  `skills/flowpilot/assets/flowpilot_core_runtime/runtime.py`.
- `flowpilot_new.py` command surface and packet facade helpers for result-body
  opens when the parallel authorized-read change is active.
- Role and phase prompt cards that describe `pm_visible_summary`,
  `recent_role_report_summary`, and authorized result/report reads.
- Focused runtime tests for missing summary blocking, PM summary propagation,
  concrete repair guidance, authorized result reads, missing read receipts, and
  Controller denial.
- FlowGuard/OpenSpec validation and local install synchronization.
