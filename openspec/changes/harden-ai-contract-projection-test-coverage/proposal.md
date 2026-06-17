## Why

Live FlowPilot runs exposed a gap between runtime contract validation and the AI-facing packet contract. Existing fake-AI rehearsals can generate the canonical `semantic_recheck` shape and runtime can reject some bad shapes, but the tests do not prove that conditional fields, finite options, minimal shapes, and rejection feedback are projected clearly enough for an AI to correct a bad result on the next round.

## What Changes

- Add Cartesian coverage for AI-facing contract projection whenever a packet has conditional result fields such as `semantic_recheck`.
- Add wrong-then-corrected fake-AI rehearsal rows for contract mistakes including missing fields, near-synonym fields, wrong value type, missing consumed read ids, and missing repair obligation ids.
- Require runtime reissue feedback tests to prove that blocked results produce enough packet-local correction information for a second-round fake AI package to return to the legal path.
- Register the new projection and convergence cases in the executable coverage matrix, ContractExhaustionMesh, TestMesh ownership, and Model-Test Alignment evidence.
- Preserve GlassBreak behavior as a separate fuse contract: ordinary recovery tests must not reach GlassBreak before the threshold, while dedicated threshold tests must still prove the fifth same-class repeat escalates.

## Capabilities

### New Capabilities

### Modified Capabilities

- `synthetic-agent-coverage-matrix`: add required branch families for AI-facing conditional contract projection and rejection-to-corrected-retry convergence.
- `multiround-fake-ai-control-rehearsal`: require fake-AI rehearsals to include realistic contract-misread packages followed by corrected retry packages.
- `flowguard-test-obligation-ownership`: require model/test ownership rows to distinguish runtime validator evidence from AI-facing packet projection and retry usability evidence.

## Impact

- Test files under `tests/` for contract projection, runtime reissue feedback, fake project rehearsal, contract exhaustion, and model-test alignment.
- Simulation models and runners under `simulations/` for executable matrix coverage, ContractExhaustionMesh, TestMesh, and Model-Test Alignment.
- Test helper logic in fake AI package generation may be extended with explicit bad-package modes, but production runtime behavior should remain under the parallel implementation change.
- Local validation and install sync commands must be rerun after tests and model evidence are updated.
