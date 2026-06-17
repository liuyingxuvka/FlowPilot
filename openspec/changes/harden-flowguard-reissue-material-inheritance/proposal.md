## Why

FlowPilot recently passed FlowGuard/Cartesian checks while a live WorldGuard run still exposed a same-family miss: a FlowGuard check packet required the operator to read the subject result body, but the runtime-generated current-contract reissue packet lost that required authorized read at the envelope/current-handoff-contract layer. The previous coverage declared field and body-consumption checks, but it did not prove that derived packets inherit material-read obligations across runtime reissue transitions.

## What Changes

- Treat runtime-generated derived packets, especially FlowGuard current-contract reissue packets, as material-inheritance transitions rather than isolated packets.
- Require derived packets to preserve the source packet's current material-read contract when they keep the same subject, target result, blocker, and packet family.
- Add FlowGuard model coverage for inherited `authorized_result_reads`, required read ids, required read count, semantic recheck contract, blocker identity, repair obligations, and evidence policy.
- Add runtime enforcement so a reissued FlowGuard check packet carries required authorized reads in the envelope and `current_handoff_contract`, not only in explanatory body payload fields.
- Add observed-regression and same-class tests for the WorldGuard path: FlowGuard result mechanically rejected, current-contract reissue created, missing inherited subject-result read rejected, inherited subject-result read required and opened before submit.
- Keep the current new-only contract. Do not add compatibility shims, old-shape translation, fallback body guessing, or legacy aliases.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `flowpilot-control-plane-contract-kernel`: derived runtime packets must preserve current material-read obligations through envelope and handoff-contract fields.
- `flowguard-boundary-test-alignment`: FlowGuard obligations, owner code contracts, and tests must align for derived-packet material inheritance and same-class reissue misses.

## Impact

- Runtime: `skills/flowpilot/assets/flowpilot_core_runtime/runtime.py`
- Models: field contract/lifecycle, ContractExhaustionMesh, Cartesian control-plane exhaustion, Model-Test Alignment, synthetic-agent coverage, coverage inventory/topology where needed
- Tests: focused runtime regressions, contract-exhaustion tests, Cartesian tests, Model-Test Alignment tests, synthetic-agent coverage tests
- OpenSpec and adoption evidence for the new model-miss closure
