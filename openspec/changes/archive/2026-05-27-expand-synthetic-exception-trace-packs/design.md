## Overview

The implementation extends the existing synthetic trace helper rather than
creating a second fake framework. All new packages must use real FlowPilot
runtime surfaces where practical:

- `packet_runtime` for packet, lease, ACK, result, relay, reviewer audit, and
  body-boundary behavior.
- `role_output_runtime` for PM/reviewer/officer output envelope authority.
- existing router runtime fixtures or focused helper calls for control blocker,
  resume, route mutation, material repair, and terminal dirty-ledger scenarios
  where a full router run is needed.
- `scripts.test_tier.background` for background-artifact classification.

Synthetic replay proves that the control surface rejects, blocks, escalates, or
records the correct runtime shape. It does not prove live AI answer quality.

## Risk Tiers

P0 branches are required synthetic replay targets unless a concrete runtime
reason makes synthetic replay impossible:

- control blocker reissue and retry-budget PM escalation;
- PM repair decision accepting only registered/receivable rerun targets;
- PM repair decision rejecting unregistered, stale, or non-receivable targets;
- fatal control blocker rejecting ordinary PM waiver;
- resume preempting normal work when active control blocker or ambiguous state
  exists;
- ACK-only worker activity leaving semantic work open.

P1 branches are required after P0:

- route mutation stale sibling proof and old active packet disposal;
- PM package disposition envelope authority and raw/manual event rejection;
- controller boundary repair budget escalation;
- material repair generation and stale progress flag rejection;
- dirty defect, PM suggestion, or self-interrogation ledgers blocking terminal
  completion.

## Coverage Matrix Shape

Every explicit exceptional replay row should declare:

- `risk_tier`: `P0`, `P1`, or `P2`;
- `synthetic_replay_required`: boolean;
- `synthetic_replay_status`: `present`, `not_required`, or
  `not_replayable`;
- `non_replayable_reason`: required only when status is `not_replayable`;
- `covered_failure_mode`: the bug class the fake package is meant to catch.

The matrix gate should fail when a P0/P1 row is required but lacks a replay row
or a concrete non-replayable reason.

## Validation Strategy

1. Focused synthetic trace tests prove the new fake package behavior.
2. Coverage matrix tests prove missing P0/P1 replay rows fail.
3. Model-test alignment and fast tier verify no existing coverage gates were
   weakened.
4. Relevant router child suites verify the same high-risk paths still pass
   through ordinary runtime coverage.
5. Meta and Capability full model regressions run in background with final
   out/err/combined/exit/meta artifacts inspected before claiming done.
6. Install sync and audit run serially after source validation.

## Non-Goals

- Do not replace ordinary router runtime tests with synthetic traces.
- Do not claim live AI semantic quality from fake packages.
- Do not weaken existing hard invariants to make replay easier.
- Do not supervise or overwrite unrelated peer-agent work.
