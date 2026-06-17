## 1. OpenSpec And FlowGuard Boundary

- [x] 1.1 Record the OpenSpec proposal, design, spec deltas, and FlowGuard route snapshot for terminal replay blocker handling.
- [x] 1.2 Confirm source/installed FlowPilot divergence and identify the minimal current-contract runtime and test surfaces.

## 2. Runtime Contract Repair

- [x] 2.1 Update terminal backward replay validation to accept current pass and current block branches while keeping segment parity strict.
- [x] 2.2 Ensure only the pass branch records terminal replay closure evidence and only the block branch enters terminal semantic blocker handling.
- [x] 2.3 Preserve runtime-issued `segment_targets` and related terminal replay context on current-contract reissue packets.
- [x] 2.4 Update packet-result catalog/contract metadata so the role-visible contract no longer says terminal replay results must always have `passed=true`.

## 3. Tests And Model Alignment

- [x] 3.1 Add focused runtime tests for valid blocking replay, malformed blocking replay, and terminal reissue target preservation.
- [x] 3.2 Add or update fake-run/current-contract rehearsal coverage for the terminal replay negative branch.
- [x] 3.3 Update model-test alignment evidence so the terminal result contract has explicit negative blocker coverage.

## 4. Validation

- [x] 4.1 Run focused unit tests for terminal replay contract and high-standard terminal closure.
- [x] 4.2 Run FlowGuard model-test/field-contract checks affected by the runtime contract change.
- [x] 4.3 Run required broader/background checks and inspect final artifacts before claiming pass.

## 5. Sync And Closure

- [x] 5.1 Sync the repository-owned FlowPilot skill to the local installed copy after source validation.
- [x] 5.2 Run install check and local install sync audit serially after sync.
- [x] 5.3 Update adoption evidence, OpenSpec task status, KB postflight, and local git state without reverting peer work.
