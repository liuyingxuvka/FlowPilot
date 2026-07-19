# Existing Model Preflight

## Route Decision

- OpenSpec: `use_openspec` via this change because the work changes the public
  result-contract, evidence, test-tier, install, and release boundaries.
- FlowGuard: ExistingModelPreflight plus DevelopmentProcessFlow, FieldLifecycleMesh,
  ContractExhaustionMesh, Model-Test Alignment, TestMesh, ModelMesh, Behavior
  Commitment Ledger, and Model-Miss Review.
- Primary path: reuse the current packet/result registry and runtime. No new
  packet kind, role, result family, compatibility schema, or fallback runtime.

## Owner Snapshot

| Boundary | Primary owner | Current executable evidence | Change disposition |
|---|---|---|---|
| Result family schema, branch, type, option, required, and forbidden rules | `packet_result_contracts.py` | contract exhaustion, formal submit, runtime unit tests | Retain as sole mechanical registry |
| Dynamic run/packet/repair projection | `runtime._dynamic_effective_result_contract_for_envelope` | core runtime and terminal repair replay | Repair projection; reject static example-id drift |
| Role-visible handoff authority | envelope `current_handoff_contract.v2` | new entrypoint and strict open-result tests | Sole authority; body mirror deleted |
| Role-visible submission surface | `submission_checklist.v2` from `flowpilot_new_role_commands.py` | public ACK/open tests | Derived, fingerprinted, identity-bound projection |
| Canonical fake AI | `ContractDrivenFakeAI.from_open_packet_result` | strict open-result and fake-project replay | Remove packet/reissue/private-helper fallbacks |
| Static finite fault universe | ContractExhaustionMesh | 990,335 current declared cells | Enumerate; do not count as runtime execution |
| Responsibility/source negative universe | current-contract Cartesian model | 4,345,728 positive profile cells plus 35 source-purity negatives | Keep full model in release lane; 35-cell shard is fast |
| Public submit execution universe | AI response execution-closure model | 72 declared rows; fast/adversarial covering arrays | Execute selected pairwise/risk rows with receipts |
| Child test evidence truth | acceptance TestMesh | `ProofArtifactRef` with final exit/result/fingerprint | No proof means `not_run`, never hand-written green |
| Model/code/test alignment | packet-result-family MTA | owner code contracts and current external tests | Split single-authority, fake-AI, execution, proof, and repair risks |
| Parent receipt consumption | ModelMesh | child `ModelContractCoverageReceipt`s plus `CompositeHandoffAcceptance` | Broad confidence requires every current child receipt |
| Done/release/publish process | DevelopmentProcessFlow and release tiers | all/release/final-confidence plus Meta/Capability | Progress is liveness only; final artifacts own pass |

## Duplicate Boundary Risks Found

1. Packet-body and reissue-body mechanical mirrors could compete with the
   envelope handoff.
2. Fake-AI helpers could reconstruct shape from private runtime helpers or a
   static registry rather than the role-visible checklist.
3. TestMesh children could be declared passed/current without commands, final
   exits, result files, or fingerprints.
4. Generated Cartesian cells could be reported as executed tests.
5. `daemon_replay`, retired aliases, unknown roles, and missing responsibility
   could continue by normalization.
6. A static terminal PM repair route shape could omit a newly active acceptance
   item and reissue forever.

All six risks are assigned to existing owners. The repair removes or rejects
alternate paths and adds negative tests; it does not preserve compatibility.

## Claim Boundary

`Full` means full only inside the declared finite mechanical universe. The
change does not claim exhaustive natural-language correctness. Static cells,
selected executable rows, passed rows, failed rows, excluded rows, and not-run
rows remain separate. Broad release confidence additionally requires current
background, install, source-fingerprint, Git, and GitHub evidence.
