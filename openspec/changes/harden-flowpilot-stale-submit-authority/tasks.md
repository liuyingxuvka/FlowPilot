## 1. Model And Contract Grounding

- [x] 1.1 Update packet/control-plane FlowGuard coverage so stale submit, accepted duplicate submit, noncurrent packet submit, inactive lease submit, repeated dispatch, and `accepted_result_id` authority are modeled as multi-step behaviors.
- [x] 1.2 Update model-test-alignment obligations and source/test evidence rows for submit ingress rejection, dispatch idempotency, accepted result authority, projection failure separation, and Reviewer mechanical/prompt obligations.
- [x] 1.3 Update contract-exhaustion/D-card coverage so the same bad-case families are declared and owned by runtime, fake-AI, or coverage matrix evidence.

## 2. Failing Tests First

- [x] 2.1 Change lifecycle tests that currently expect late duplicate results to append history so they require ingress rejection with no result id, no result row, no `packet.result_ids` append, and unchanged `accepted_result_id`.
- [x] 2.2 Add focused tests for noncurrent packet submit, accepted packet resubmit, closed/superseded lease submit, repeated same-lease submit, and stale submit after next packet wait starts.
- [x] 2.3 Add dispatch-current-role tests proving repeated dispatch for the same current active lease is idempotent and does not create a second active lease.
- [x] 2.4 Add authority-reader tests proving accepted packet review, validation, PM disposition, repair, and closure ignore polluted historical `result_ids[-1]`.
- [x] 2.5 Add projection/materialization tests proving projection failure does not cause duplicate business result submission or stale submit acceptance.

## 3. Runtime Control-Plane Repair

- [x] 3.1 Move `submit_result` mechanical prechecks before result id allocation and before any ledger mutation.
- [x] 3.2 Make accepted, noncurrent, inactive-lease, mismatched-lease, closed-lease, and stale-route submissions reject through the existing current-contract runtime error surface.
- [x] 3.3 Ensure rejected stale/duplicate submissions produce no result row, no `result_ids` append, no accepted-result change, no route advance, and no review/validation trigger.
- [x] 3.4 Make repeated `dispatch-current-role` idempotently return the existing active current packet handoff when the assigned lease is already valid.
- [x] 3.5 Keep lease replacement limited to existing modeled repair/reissue/replacement paths.
- [x] 3.6 Audit and repair accepted-packet result readers so accepted packets use `accepted_result_id` instead of `result_ids[-1]`.
- [x] 3.7 Make materialized projection writes use complete temp-and-replace behavior where they currently direct-write, and report projection failures without replaying business submissions.

## 4. Reviewer Prompt And Mechanical Boundary

- [x] 4.1 Update every current Reviewer review packet/card surface to require active inspection of the current work, direct evidence opening, relevant test/model/FlowGuard checks, and review-scope test/fixture additions when necessary.
- [x] 4.2 Preserve the boundary that runtime only checks Reviewer mechanical structure, current subject, accepted-result binding, authorized-read/open receipts, evidence paths, and pass/block shape.
- [x] 4.3 Add tests proving Reviewer prompt/card surfaces include active verification duties without adding runtime semantic text grading or new Reviewer fields.
- [x] 4.4 Add fake-AI or replay coverage for mechanically invalid Reviewer pass attempts, including missing current body open receipt, stale subject, missing evidence path, empty required field, and forbidden field.

## 5. Synthetic And Fake-AI Coverage

- [x] 5.1 Extend fake-AI runtime replay for old backend agents that resubmit accepted packets, submit noncurrent packets after the next wait, and submit with inactive leases.
- [x] 5.2 Extend synthetic coverage matrix rows for stale submit, duplicate submit, repeated dispatch, stale historical result authority, projection-failure duplicate retry, and Reviewer mechanical-boundary cases.
- [x] 5.3 Ensure coverage boundaries state that fake-AI proves control-flow/mechanical behavior, not live AI semantic quality.

## 6. Verification, Install Sync, And Local Git State

- [x] 6.1 Run focused FlowGuard and unit checks from the verification contract for packet control plane, lifecycle guard, Reviewer active challenge, fake-AI runtime replay, contract exhaustion, and model-test alignment.
- [x] 6.2 Rebuild and check FlowGuard project topology after changed models/tests/code.
- [x] 6.3 Run install sync, local install audit, installed-skill check, and repository install self-check.
- [x] 6.4 Run meta and capability regressions through the repository background artifact contract and inspect final exit/result artifacts before claiming them passed.
- [x] 6.5 Review git status and diff to confirm only intended files changed and parallel-agent/untracked work was not reverted.
- [x] 6.6 Mark this OpenSpec task list complete only after the corresponding implementation and validation evidence exists.
