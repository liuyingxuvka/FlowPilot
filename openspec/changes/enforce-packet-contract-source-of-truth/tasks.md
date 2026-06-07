## 1. Contract Source Of Truth

- [x] 1.1 Audit current packet-result families and confirm the authoritative contract row set.
- [x] 1.2 Make runtime mechanical contract checks expose contract family id, required fields, forbidden fields, missing fields, forbidden fields seen, and minimal valid shape.
- [x] 1.3 Ensure mechanical reissue packets carry the same contract metadata as the blocking result.

## 2. Fake AI Contract Parity

- [x] 2.1 Add or update fake AI success rows so they emit only fields declared by the matching packet contract.
- [x] 2.2 Add negative fake AI rows for missing fields, forbidden old fields, old wrappers, fallback evidence, and hidden-field overproduction.
- [x] 2.3 Add source-alignment checks that fail when successful fake AI bodies include undeclared hidden fields.

## 3. FlowGuard Model And Alignment

- [x] 3.1 Extend FieldContract to model packet contract misalignment and current packet family coverage.
- [x] 3.2 Extend FieldMesh or source checks so contract rows bind to runtime validators and fake AI parity evidence.
- [x] 3.3 Extend Model-Test Alignment evidence so broad e2e success is scoped until packet contract rows have code, fake AI, and negative-test evidence.

## 4. Runtime And Test Coverage

- [x] 4.1 Add runtime tests for contract metadata on mechanical blocks and reissued packets.
- [x] 4.2 Add high-standard/control-flow tests for hidden generic fields, missing fields, and old field rejection.
- [x] 4.3 Add fake AI rehearsal tests that prove contract-blind success and explicit negative overproduction.

## 5. Validation And Sync

- [x] 5.1 Run targeted unit tests for runtime, high-standard flow, fake AI rehearsal, and field contract model.
- [x] 5.2 Run FieldContract, FieldMesh, Model-Test Alignment, topology build/check, and layered parent regressions.
- [x] 5.3 Sync local FlowPilot install and run install/audit checks.
- [x] 5.4 Record FlowGuard and KB postflight evidence, commit, and push.
