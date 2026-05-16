## 1. OpenSpec and model preflight

- [x] 1.1 Create the `persist-self-interrogation-findings` OpenSpec change.
- [x] 1.2 Capture current behavior and target behavior in `proposal.md`.
- [x] 1.3 Add design, requirements, scenarios, and implementation tasks.
- [x] 1.4 Validate the OpenSpec change status before implementation.

## 2. FlowGuard model

- [x] 2.1 Extend `simulations/meta_model.py` with self-interrogation record,
  PM disposition, index-clean, and protected-gate state.
- [x] 2.2 Extend `simulations/capability_model.py` with the same capability
  routing constraints.
- [x] 2.3 Update model runners/summaries so new gate states are part of the
  checked state signature.
- [x] 2.4 Run the relevant FlowGuard checks and inspect artifacts/results.

## 3. Runtime contracts and prompts

- [x] 3.1 Add a self-interrogation record template/contract.
- [x] 3.2 Update PM phase/role cards so startup, product architecture,
  node-entry, repair, completion, and final ledger prompts require durable
  self-interrogation records or dispositions.
- [x] 3.3 Update reviewer, worker, and officer cards so self-interrogation
  discoveries become PM suggestion candidates or cited ledger entries.

## 4. Router implementation

- [x] 4.1 Add helpers to load and validate the self-interrogation index and
  records.
- [x] 4.2 Gate root acceptance contract freeze on clean startup/product
  self-interrogation state.
- [x] 4.3 Gate current-node packet registration/dispatch on clean current-node
  self-interrogation state.
- [x] 4.4 Require final ledger and terminal closure to cite the index and prove
  zero unresolved hard/current self-interrogation findings.

## 5. Verification and sync

- [x] 5.1 Add focused tests for missing/unresolved/malformed
  self-interrogation records at protected gates.
- [x] 5.2 Run focused tests and practical repo checks.
- [x] 5.3 Sync the installed local `flowpilot` skill from the repository.
- [x] 5.4 Audit local install sync and report local git working-tree state.
