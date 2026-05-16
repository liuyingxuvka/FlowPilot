## 1. Model and Contract Guard

- [x] 1.1 Add or update a focused FlowGuard/prompt-boundary check that rejects Controller ledger rows whose metadata still instructs Controller to apply instead of writing a receipt.
- [x] 1.2 Run the focused FlowGuard check before production edits and record the result.

## 2. Runtime Metadata Projection

- [x] 2.1 Add a Controller action ledger projection that sets receipt completion fields and preserves original Router apply intent under explicit diagnostic names.
- [x] 2.2 Use the projection when writing `runtime/controller_actions/*.json` and `runtime/controller_action_ledger.json` summaries.
- [x] 2.3 Keep direct Router pending actions on the existing apply path outside Controller ledger projection.

## 3. Controller-Visible Wording

- [x] 3.1 Rewrite display/startup/role/heartbeat/terminal Controller-visible wording from "apply" to "write a Controller receipt" where the action is ledger-row scoped.
- [x] 3.2 Update the Controller role card and FlowPilot skill guidance so daemon Controller rows consistently describe the receipt path.

## 4. Regression Tests

- [x] 4.1 Add runtime tests for startup banner, role slots, heartbeat, controller core, display, and terminal summary Controller rows.
- [x] 4.2 Add a regression test proving direct startup intake pending actions still expose the normal apply path.
- [x] 4.3 Run focused router/runtime tests for the touched metadata and receipt paths.

## 5. Sync and Broad Validation

- [x] 5.1 Run or launch the required meta/capability FlowGuard regressions with the repository background log contract, then cancel them by explicit user direction because they are too heavy for this pass.
- [x] 5.2 Sync the local installed FlowPilot skill and verify the install audit reports source freshness.
- [x] 5.3 Review the combined working tree, including any peer-agent changes present before final git submission.
