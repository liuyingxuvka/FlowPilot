## 1. FlowGuard And OpenSpec Setup

- [x] 1.1 Confirm real FlowGuard 0.51 package, schema, and project audit.
- [x] 1.2 Validate this OpenSpec change.

## 2. Native FlowGuard Cartesian Evidence

- [x] 2.1 Add FlowGuard `ContractAxis`, `ContractInteractionGroup`, coverage shard, and receipt generation to the existing Cartesian model.
- [x] 2.2 Attach generated combination case ids, shard ids, and receipt ids to applicable Cartesian cells.
- [x] 2.3 Add exact source mutation bridging so unknown upstream mutation kinds fail instead of being mapped to a generic field miss.

## 3. Downstream Consumption

- [x] 3.1 Update the Cartesian runner to summarize native combination cases, required shard ids, receipt ids, and missing consumption.
- [x] 3.2 Update TestMesh child-suite evidence so every required native or model-owned coverage shard has a current owner.
- [x] 3.3 Update synthetic-agent coverage rows to carry Cartesian shard and receipt identifiers.
- [x] 3.4 Update Model-Test Alignment contracts and tests if needed so the new evidence fields are not orphaned.

## 4. Validation And Repair

- [x] 4.1 Run the upgraded Cartesian runner and targeted pytest suite.
- [x] 4.2 Run affected synthetic coverage, MTA, layered proof, inventory, test-tier, install, and topology checks.
- [x] 4.3 Fix any current-contract bug exposed by the upgraded matrix without adding fallback/compatibility surfaces.

## 5. Sync And Postflight

- [x] 5.1 Sync repository evidence, local install evidence, FlowGuard adoption records, and git version.
- [x] 5.2 Perform predictive KB postflight and record a reusable lesson if this exposes a route gap.
