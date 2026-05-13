# Barrier Bundle Equivalence

Date: 2026-05-05

Barrier bundles are the simplification layer for FlowPilot. They compress
repeated control checks into named barriers. For most barriers, the bundle must
prove that the same role-scoped evidence, packet hashes, reviewer gates,
FlowGuard officer gates, route mutation markers, final ledger, and terminal
backward replay still exist.

The Reviewer-only speed profile intentionally changes two default pre-route
gates: `root_contract` and `child_skill_manifest` now require PM and Reviewer
role slices only. Product and Process Officer checks are no longer default
requirements for those two barriers.

## Non-Negotiable Rule

A barrier bundle is metadata only. It may group checks, but it must not:

- merge role packet bodies;
- let Controller read, summarize, execute, approve, or originate project
  evidence;
- let a worker, reviewer, officer, PM, or Controller approve as another role;
- reuse cached evidence after input/source/hash invalidation;
- continue after route mutation without stale evidence markers and frontier
  rewrite;
- complete without the final route-wide ledger and terminal backward replay;
- let an AI choose that a gate is unnecessary.

The schema is `flowpilot.barrier_bundle.v1`, implemented in
`skills/flowpilot/assets/barrier_bundle.py`.

## Barrier Sequence

| Barrier | Purpose |
| --- | --- |
| `startup` | Startup answers, fresh run boundary, crew authority, Controller boundary, manifest delivery |
| `material` | Packet ledger mail, material scan/research, reviewer-before-worker evidence |
| `product_architecture` | PM synthesis, reviewer challenge, product FlowGuard officer modelability |
| `root_contract` | Root acceptance contract and Reviewer approval |
| `child_skill_manifest` | Child-skill gate manifest, Reviewer/PM approval |
| `route_skeleton` | Route/frontier, mutation policy, FlowGuard route checks |
| `current_node` | Current-node packet/result/reviewer loop |
| `parent_backward` | Parent backward replay and PM segment decision |
| `final_closure` | Final route-wide ledger, terminal backward replay, display/quarantine/nonblocking improvement closure |

## Executable Checks

The equivalence model is:

- `simulations/barrier_equivalence_model.py`
- `simulations/run_barrier_equivalence_checks.py`
- `simulations/barrier_equivalence_results.json`

The model checks a safe path through all barriers and adversarial states for AI
discretion, Controller body access, Controller-origin evidence, wrong-role
approval, missing role slices, missing legacy obligations, missing PM,
reviewer, process-officer, product-officer, packet-ledger, or final-replay
gates, invalid cache reuse, stale evidence use, route mutation without
stale/frontier markers, and final closure without the complete ledger/replay
contract.

The model also covers the controller-only `run-until-wait` simplification
boundary. `run-until-wait` may only apply internal Controller actions until the
next wait boundary. It is rejected if it loses the Controller-only boundary,
crosses a user or role wait boundary, applies a PM/reviewer/officer decision,
skips a packet-ledger check, or skips terminal backward replay.

## Why This Is Equivalent

The old protocol required every obligation to be separately prompted and
checked. The bundle format allows one barrier to attest to a set of required
checks, but the bundle is valid only if every required obligation and role slice
for the active profile is present. The Reviewer-only profile deliberately
removes Product/Process Officer default gate slices from `root_contract` and
`child_skill_manifest`; other barriers continue to preserve their required
role-scoped evidence.
