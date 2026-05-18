# FlowGuard Model-Test Alignment

This document explains the read-only Model-Test Alignment runner:

```powershell
python simulations/run_flowpilot_model_test_alignment_checks.py
```

The runner does not execute the referenced tests and does not run long
FlowGuard parent graphs. It uses the real FlowGuard API:
`ModelObligation`, `TestEvidence`, `CodeContract`,
`ModelTestAlignmentPlan`, `review_model_test_alignment()`,
`audit_python_code_contracts()`, `audit_python_test_assertions()`, and
`review_python_contract_source_audit()`.

In plain English, each row below says: "This FlowGuard model family owns these
obligations, and these ordinary tests are the current evidence for them." A
green row means the declared obligations have current passing evidence for the
required test kinds. It does not mean production conformance unless a separate
production replay or release check says that.

The runner has three layers:

- Declaration alignment: every major model family lists required obligations
  and current ordinary test evidence.
- Source-contract audit: a conservative AST-supported subset also lists real
  Python `CodeContract` rows, then verifies that selected tests directly call
  those public contract symbols and assert the external contract boundary.
- Full model-test-code diagnostics: a repository-wide coverage-accounting pass
  inventories owner modules, compatibility facades, script entrypoints,
  model-check runners, and test tiers, then reports missing-model,
  missing-test, extra-code, internal-only-test, stale-evidence, and
  needs-structure-split gaps with owner, severity, release relevance, repair
  type, dedupe, and priority metadata.

The public runner file is now a compatibility facade. The implementation is
split into focused `flowpilot_model_test_alignment_*` modules for common
declarations, family plans, source contracts, known-bad cases, and full
diagnostic surface inventory. The public command and importable helper names
remain unchanged.

The source-contract audit is intentionally narrower than the declaration table.
It proves that critical externally visible Python surfaces are not merely
mentioned by a test map. It does not claim full Python semantics, replace
runtime replay, or replace Meta/Capability/Router background regressions.

The full diagnostic layer is intentionally allowed to find gaps while the
runner exits successfully. `full_diagnostic_ok` means the diagnostic machinery
and its known-bad cases are working. `full_coverage_ok` remains false until
every inventoried surface is covered, including structure split debt. The
separate `release_convergence_ok` field is true only when all non-deferred
model/code/test/background gaps are gone and remaining findings are explicit
StructureMesh deferrals. The current burn-down pass adds direct
external-contract evidence for the remaining runtime owner modules and keeps
oversized modules visible as deferred structure work rather than hiding them.

Each full-diagnostic gap carries triage metadata so maintenance can be planned
without rereading every large script. The key fields are:

- `severity`: critical, high, medium, or low.
- `surface_owner`: the module, script, tier, or model runner that owns the
  repair.
- `release_relevance`: whether the gap blocks release tooling, validation,
  runtime contracts, public CLI behavior, legacy validation, or maintenance
  only.
- `repair_type`: the next repair class, such as adding external-contract tests,
  completing background evidence, rerunning public release evidence, or
  deferring a StructureMesh split.
- `dedupe_key` and `priority_score`: stable grouping and ordering fields for
  turning many raw rows into an actionable queue.

Background evidence is treated conservatively. Final pass, failed, running,
stale, incomplete, progress-only, and local-only release proof states are read
from the stable artifact contract. A progress log alone never counts as passing
evidence, and a `--skip-url-check` public release proof is marked
`release_local_only`. The current public release proof avoids duplicate nested
validation with `--skip-validation`, but still performs URL probing.

Structure-split findings distinguish immediate code movement from deliberately
deferred owner-module work. Fresh or state-ordering-sensitive modules may remain
above the line threshold, but they are still recorded as actionable
`defer_structure_split` rows with owner, reason, safety status, and recommended
next action metadata.

The current diagnostic reports 541 surfaces, 493 covered surfaces, and 48
remaining gap surfaces. All 48 are explicit `needs_structure_split` deferrals;
`unresolved_non_deferred_gap_count` is zero and `release_convergence_ok` remains
true.

The `legacy-full` tier is kept visible as legacy validation history but is not
ranked as the current release gate. When current layered full Meta/Capability
proofs are valid, failed or still-running legacy monolithic artifacts are
reclassified as `legacy_full_reclassified`: visible as raw background evidence,
but not counted as stale release evidence.

For source-audited evidence, `TestEvidence.path` points to the file containing
the real test function or class definition. The `command` may still be a public
aggregate wrapper such as `tests.test_flowpilot_router_runtime_startup_daemon`
when that is the supported command users run.

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
  sanity cases are rejected, including the source-contract audit layer.
- `alignment_ok`: true only when the main FlowPilot family plans have no
  blocker findings.
- `known_bad_ok`: true only when FlowGuard rejects the synthetic bad evidence
  cases.
- `source_audit_ok`: true only when the AST-supported model/code/test source
  contract subset is green.
- `source_known_bad_ok`: true only when the synthetic source-audit bad cases are
  rejected.
- `full_diagnostic_ok`: true only when the full diagnostic report is generated
  and its false-confidence known-bad cases are rejected.
- `full_coverage_ok`: true only when the full diagnostic has no current gap
  findings. This is intentionally separate from `ok`.
- `release_convergence_ok`: true when remaining full-diagnostic findings are
  only explicit StructureMesh deferrals.
- `full_model_test_code_diagnostic`: surface counts, gap counts, per-surface
  rows, actionable findings, deduplicated actionable summary, counts by
  severity/repair/release relevance, and full-diagnostic known-bad results.
- `per_plan`: one entry per family, including the serialized
  `ModelTestAlignmentPlan`, the FlowGuard report, model-check commands, and
  the coverage boundary.
- `source_contract_plan`: the serialized source-audited plan, its ordinary
  alignment report, and its Python source-audit report.
- `findings`: flattened findings from the main plans.
- `known_bad_sanity_checks`: synthetic cases proving the reviewer flags bad
  evidence.
- `source_known_bad_sanity_checks`: synthetic source-audit cases proving stale
  code/test bindings are rejected.

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

The source-audit layer adds these synthetic bad cases:

| Source known-bad case | Expected FlowGuard finding |
| --- | --- |
| Missing Python symbol | `source_contract_missing_symbol` |
| Test asserts an internal/helper path but never calls the declared contract | `source_test_missing_code_contract_call`, `source_test_internal_path_only` |
| Test calls the contract but has no external assertion | `source_test_missing_external_assertion`, `source_test_internal_path_only` |
| Code surface has undeclared side-effect-looking calls | `source_contract_extra_side_effect` |

The full diagnostic layer adds these synthetic bad cases:

| Full diagnostic known-bad case | Expected diagnostic finding |
| --- | --- |
| Orphan code surface | `missing_model`, `missing_test`, `extra_code` |
| Wrapper-only evidence | `internal_only_test` |
| Progress-only background evidence | `stale_evidence` |
| Local-only release proof | `stale_evidence` with `rerun_public_release_evidence` |
| Broad unsplit module | `needs_structure_split` |

Additional gate invariants now ensure that `release_gate` and `validation_gate`
surfaces do not regress to `missing_test` or `internal_only_test` after the
aggregate test-tier, model-check runner, and runtime owner contract tests are
present. Local-only public release evidence is still rejected by the known-bad
case, but the current release proof is no longer local-only.

These sanity checks are intentionally separate from the main alignment table.
They should fail as bad plans while the runner as a whole remains green.
