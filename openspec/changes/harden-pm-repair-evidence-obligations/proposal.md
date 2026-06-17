## Why

Recent live FlowPilot runs showed a current-contract gap: a blocker can name
missing direct evidence, validation, replay, or FlowGuard/Reviewer evidence,
but the follow-up `pm_repair_decision` packet only requires `decision` and
`reason`. That lets a PM result be mechanically valid while dropping the
specific evidence obligations that caused the block, so the next packet can
repeat the same semantic failure.

The same failure class also appears as a sealed-body consumption gap: the
runtime can know which blocker, target result, or upstream result bodies are
relevant, while a downstream PM, repair worker, Reviewer, or FlowGuard operator
may act from only the current packet body, a summary, or one selected body.
Every sealed body created for the repair/recheck chain must therefore have a
role-owned downstream reader, and every required authorized body must be opened
before that role can submit a result.

## What Changes

- Add a current-contract repair evidence obligation surface to existing PM
  repair packets, derived from the active blocker and its missing fields,
  stale evidence, recommended resolution, gate kind, and required recheck role.
- Require PM repair decisions to disposition every repair evidence obligation
  when the packet declares obligations; `reason` text alone cannot satisfy an
  obligation.
- Reject unknown, duplicate, stale, reason-only, summary-only, and
  acceptance-registry-only repair dispositions through the existing
  packet/result contract path.
- Extend FieldLifecycleMesh, ContractExhaustionMesh, Model-Test Alignment,
  TestMesh, synthetic-agent coverage, and focused runtime regressions so the
  obligation chain is modeled from blocker creation through PM decision,
  reissue, FlowGuard semantic recheck, Reviewer evidence check, and blocker
  clearance.
- Treat `authorized_result_reads` and `current_handoff_contract` as the
  current-contract sealed-body bridge: PM, repair workers, Reviewers, and
  FlowGuard operators must read every delivered blocker/target/upstream body
  before submitting, and runtime must reject missing open receipts for required
  bodies.
- Keep the existing blocker -> PM repair decision -> repair packet -> recheck
  flow. This change does not add compatibility aliases, fallback parsers, a new
  packet kind, a parallel ledger, or a second repair authority.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `blocker-repair-policy`: PM repair decisions must carry structured
  disposition for blocker-derived repair evidence obligations.
- `flowpilot-control-plane-contract-kernel`: runtime packet/result contracts
  must preserve and validate repair evidence obligations and required
  sealed-body reads as current control plane fields.
- `synthetic-agent-coverage-matrix`: fake AI and synthetic coverage must include
  reason-only, summary-only, stale-obligation, unknown-obligation, and
  registry-only PM repair outputs, plus missing or partial authorized-body read
  outputs.
- `flowguard-boundary-test-alignment`: model/test/code alignment must bind the
  repaired obligation lifecycle and sealed-body consumption lifecycle to owner
  code contracts and focused tests.

## Impact

- Runtime: `skills/flowpilot/assets/flowpilot_core_runtime/runtime.py` and
  packet-result contract metadata.
- Prompt cards: PM, FlowGuard operator, and Reviewer role cards that describe
  repair evidence obligations and recheck consumption.
- FlowGuard models and runners: field contract, contract exhaustion,
  Cartesian control-plane exhaustion, model-test alignment, synthetic-agent
  coverage, and related result artifacts.
- Tests: focused runtime tests, field contract tests, model-test alignment
  tests, synthetic/fake AI tests, and install/topology validation.
