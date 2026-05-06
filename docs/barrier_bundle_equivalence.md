# Barrier Bundle Equivalence

Date: 2026-05-05

Barrier bundles are the equivalent simplification layer for FlowPilot. They
compress repeated control checks into named barriers, but they do not relax the
old obligations. The simplification is valid only when the bundle proves that
the same role-scoped evidence, packet hashes, reviewer gates, FlowGuard officer
gates, route mutation markers, final ledger, and terminal backward replay still
exist.

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
| `root_contract` | Root acceptance contract and product FlowGuard officer approval |
| `child_skill_manifest` | Child-skill gate manifest, process/product officer checks, reviewer/PM approval |
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
checked. The new bundle format allows one barrier to attest to a set of
existing checks, but the bundle is valid only if every required obligation and
role slice is present. It reduces control-plane repetition without lowering the
acceptance standard.
