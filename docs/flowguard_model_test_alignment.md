# FlowGuard Model-Test Alignment

This document explains the read-only Model-Test Alignment runner:

```powershell
python simulations/run_flowpilot_model_test_alignment_checks.py
```

The runner does not execute the referenced tests and does not run long
FlowGuard parent graphs. It uses the real FlowGuard API:
`ModelObligation`, `TestEvidence`, `ModelTestAlignmentPlan`, and
`review_model_test_alignment()`.

In plain English, each row below says: "This FlowGuard model family owns these
obligations, and these ordinary tests are the current evidence for them." A
green row means the declared obligations have current passing evidence for the
required test kinds. It does not mean production conformance unless a separate
production replay or release check says that.

| Family | Model checks represented | Obligations in the alignment table | Ordinary test evidence | Boundary |
| --- | --- | --- | --- | --- |
| Startup | `run_flowpilot_startup_control_checks.py`, `run_flowpilot_deterministic_startup_bootstrap_checks.py` | Three-question pause before work, prompt-isolated run state, reviewer facts, and PM startup activation. | Startup daemon/runtime tests for answer waiting, prompt-isolated run creation, answer acceptance, and activation blocking. | Does not run UI smoke or parent Meta/Capability graphs. |
| Packet/card/ACK | Packet lifecycle, card envelope, and event-contract model checks. | Packet body separation, card/bundle ACK identity, and ACK/return wait preconsumption. | Packet runtime tests, card runtime tests, and ACK/return runtime tests. | ACK evidence stays mechanical; it is not semantic review or PM approval. |
| Route mutation | `run_flowpilot_route_mutation_activation_checks.py` | Mutation topology, process/product recheck, old packet supersession, sibling replacement, stale evidence, and route-sign projection. | Route-mutation parent contract tests, focused route-mutation runtime child suites, and user-flow diagram tests. | Covers ordinary route mutation behavior through split child-suite evidence; the legacy aggregate runtime module is a compatibility oracle, not the routine tier command. |
| Terminal/closure/resume | Runtime closure, recursive closure reconciliation, and resume checks. | Final ledger, backward replay, dirty-ledger closure blocking, and current-run resume re-entry. | Terminal, closure, and resume runtime tests. | This is not a production replay adapter. |
| Role/output contracts | Output contract and role-output runtime checks. | Registry-backed role outputs, current wait authority, packet output-contract binding, and wrong-recipient rejection. | Role-output runtime tests and output-contract tests. | Checks mechanics only; task semantic quality is outside this runner. |
| Router loop/daemon | Router-loop and persistent-daemon checks. | Current-node packet/result loop, direct-dispatch preflight, daemon lock/status ownership, and queue progress. | Router packet runtime tests and startup daemon runtime tests. | Does not run long daemon soak tests. |
| Test tiering/slow-test contracts | Test-tiering and slow-test contract model checks. | Fast/router tier scope, release-only exclusion, complete background artifacts, and parent/child slow-test ownership. | Test-tier runner tests and slow-test contract tests. | Progress output alone is never counted as pass evidence. |
| Meta/capability parents | Meta and Capability thin/layered parent commands. | Thin-parent default evidence, explicit layered/legacy boundary, stale proof rejection, and abstract confidence boundary. | Thin-parent tests, FlowGuard proof tests, smoke fast-path tests, and control-gate unit tests. | Parent results are abstract model confidence, not ordinary production conformance. |

## JSON Shape

The runner prints a JSON payload with:

- `ok`: true only when all declared alignment plans are green and all known-bad
  sanity cases are rejected.
- `alignment_ok`: true only when the main FlowPilot family plans have no
  blocker findings.
- `known_bad_ok`: true only when FlowGuard rejects the synthetic bad evidence
  cases.
- `per_plan`: one entry per family, including the serialized
  `ModelTestAlignmentPlan`, the FlowGuard report, model-check commands, and
  the coverage boundary.
- `findings`: flattened findings from the main plans.
- `known_bad_sanity_checks`: synthetic cases proving the reviewer flags bad
  evidence.

## Known-Bad Sanity Checks

The runner also builds synthetic bad plans to prove the FlowGuard alignment API
is actually enforcing the table:

| Known-bad case | Expected FlowGuard finding |
| --- | --- |
| Missing evidence | `missing_test_evidence` |
| Stale evidence | `stale_test_evidence` |
| Progress-only background evidence | `test_evidence_not_passing` plus missing current passing coverage |
| Overclaimed model confidence | `test_overclaims_model_confidence` |
| Orphan evidence | `orphan_test_evidence` |
| Duplicate same-kind evidence | `duplicate_test_evidence_owner` |

These sanity checks are intentionally separate from the main alignment table.
They should fail as bad plans while the runner as a whole remains green.
