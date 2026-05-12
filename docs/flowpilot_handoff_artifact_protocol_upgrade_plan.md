# FlowPilot Handoff and Artifact Protocol Upgrade Plan

## Scope

This plan upgrades FlowPilot's role-output protocol so that formal work products, handoff letters, artifact references, PM suggestions, optional specialist consultation, and Router preservation form one enforceable loop.

Remote GitHub sync is out of scope. Local repository changes, local installed skill sync, local git status, and local checks are in scope.

## Optimization Checklist

| Order | Optimization point | Concrete target | Done evidence |
| --- | --- | --- | --- |
| 1 | Formalize the two-object output rule | Every substantive role output has a formal artifact and a readable handoff letter | Role cards and output contracts require both |
| 2 | Add handoff letter minimum structure | Handoff includes work summary, artifact refs, changed paths, inspection notes, risks, and PM suggestion items | Contract and prompt text name these sections |
| 3 | Preserve role-authored artifacts | Router validates and registers artifacts instead of silently rebuilding a narrowed official file | Route draft registration keeps PM-authored fields such as repair-return policy |
| 4 | Deliver handoff context to downstream roles | Reviewer/officer/PM delivery includes the upstream handoff path plus formal artifact refs | Delivery context and source paths include handoff and artifact refs |
| 5 | Require downstream consistency checks | Downstream roles read the handoff and verify it matches the formal artifacts | Reviewer/officer cards require handoff-artifact consistency review |
| 6 | Make PM suggestions universal | Every role output includes PM Suggestion Items or an explicit no-new-suggestion statement | Role cards and contracts require suggestion sections |
| 7 | Separate PM final disposition from optional consultation | PM can directly decide or request bounded specialist input; consultation is not a final disposition | PM cards and ledger schema distinguish consultation state from final disposition |
| 8 | Add bounded consultation packets | PM consultation requests name the target role, question, blocking status, and artifact refs | PM role-work request card supports consultation request packets |
| 9 | Require consulted role formal advice | Process/product/reviewer/worker consultation replies are formal advice artifacts, not chat | Officer/reviewer/worker cards define consultation response duties |
| 10 | Gate advancement on unresolved blocking items | A blocking suggestion cannot advance only because consultation is pending | Router/ledger checks reject unresolved blocking suggestion states |
| 11 | Keep ACK separate from completion | ACK only proves a card was received; handoff/artifact output proves work completion | System and role cards state ACK is not completion evidence |
| 12 | Sync local install after source change | Repository-owned FlowPilot skill refreshes installed `<Codex skills root>/flowpilot` | `install_flowpilot.py --sync-repo-owned --check --json` reports fresh source |

## Bug and Regression Risks to Model

| Risk id | Possible bug | Why it matters | FlowGuard catch required |
| --- | --- | --- | --- |
| R1 | Role puts the only work product in the handoff letter | Reviewers cannot inspect durable formal evidence | Reject message-only work product |
| R2 | Router rebuilds a narrowed official artifact and drops role-authored fields | PM can do the work and still fail review, as happened with route repair policy | Reject router artifact truncation |
| R3 | Downstream reviewer/officer does not receive or read the handoff letter | Reviewer may miss where the real artifact or changed files are | Reject downstream handoff omission |
| R4 | Handoff claims and formal artifact refs do not match | PM/reviewer may inspect the wrong or stale file | Reject handoff-artifact mismatch |
| R5 | Hash/path validation is skipped or stale | Router can accept stale or wrong artifacts | Reject stale or unchecked artifact hash |
| R6 | PM suggestions are omitted from a role output | Higher-standard opportunities vanish | Reject missing suggestion section |
| R7 | PM treats consultation request as final disposition | Suggestion closes before PM actually decides | Reject consultation-as-final |
| R8 | Consultation is forced for every minor suggestion | FlowPilot becomes unnecessarily slow and rigid | Reject forced consultation for minor direct-decision cases |
| R9 | PM requests consultation without a bounded formal packet | Consulted role cannot know what to answer | Reject unbounded/no-packet consultation |
| R10 | Consultation result returns but PM never reads it before final disposition | Specialist input is performative only | Reject unread consultation result |
| R11 | Blocking suggestion advances while still under consultation | Current gate can pass with unresolved blocker | Reject blocked gate advancement |
| R12 | ACK is treated as completed work | Flow can advance with no formal artifact or handoff | Reject ACK-as-completion |
| R13 | Major suggestion is directly rejected without reason or evidence basis | PM decision becomes opaque and unreviewable | Reject major no-consult/no-reason paths |
| R14 | Router or Controller leaks sealed body content into a public ledger | Privacy and role-boundary violation | Reject sealed body leakage |

## FlowGuard Work Plan

1. Add a focused FlowGuard model: `simulations/flowpilot_handoff_artifact_protocol_model.py`.
2. Add executable checks: `simulations/run_flowpilot_handoff_artifact_protocol_checks.py`.
3. Require the model to show:
   - valid direct PM disposition passes;
   - valid optional consultation then PM final disposition passes;
   - valid no-suggestion handoff passes;
   - valid route artifact preservation passes;
   - every risk R1-R14 is rejected by a named hazard check.
4. Run the model before code changes.
5. Only after the model passes, modify FlowPilot router, contracts, cards, and install sync.
6. After each implementation cluster, run the targeted checks for that cluster plus the new handoff/artifact protocol checks.

## Implementation Clusters

| Cluster | Files likely touched | Verification |
| --- | --- | --- |
| Model and plan | `docs/`, `simulations/flowpilot_handoff_artifact_protocol_*` | New FlowGuard check script |
| Output contracts | `skills/flowpilot/assets/runtime_kit/contracts/contract_index.json`, role-output runtime if needed | Output contract checks and role-output runtime checks |
| Role and system prompts | `skills/flowpilot/assets/runtime_kit/cards/**` | Card instruction coverage checks |
| Router preservation and delivery | `skills/flowpilot/assets/flowpilot_router.py` | New regression plus router/action/loop checks |
| Local install sync | `scripts/install_flowpilot.py` if needed, installed skill directory | Install check reports `source_fresh: true` |

## Local Sync Policy

- Do not push GitHub remote.
- Preserve existing local changes unless explicitly part of this upgrade.
- Keep source repository changes in the active FlowPilot checkout.
- Refresh installed skill from the source repository after validation.
- Confirm local git status at the end so changed files are visible for commit.

## Implementation Status

| Area | Status | Evidence |
| --- | --- | --- |
| FlowGuard handoff/artifact model | Complete | `simulations/run_flowpilot_handoff_artifact_protocol_checks.py` passes and detects R1-R14 hazards |
| Router route-draft preservation | Complete | `_write_route_draft` preserves PM-authored payload fields and records `router_preservation` metadata |
| Router regression test | Complete | `test_pm_route_draft_preserves_role_authored_repair_policy_fields` passes |
| Role and phase prompts | Complete | PM, worker, reviewer, officer, all PM phase cards, and resume system card carry artifact-backed handoff and optional-consultation rules |
| Packet/result templates | Complete | Packet template requires artifact-backed handoff; result template includes `Artifact Handoff` |
| Packet output contracts | Complete | Default packet output contract and registry require `Artifact Handoff` for packet result families |
| Output-contract FlowGuard model | Complete | Implementation contract model includes artifact refs, changed paths, inspection notes, and PM suggestions |
| Installed local skill sync | Pending | Run after final source checks |

## Verification Log

| Check | Result | Note |
| --- | --- | --- |
| `python -m unittest tests.test_flowpilot_card_instruction_coverage` | Pass | Card prompt coverage still valid |
| `python simulations\run_flowpilot_handoff_artifact_protocol_checks.py` | Pass | Direct PM disposition and optional consultation both pass; listed hazards are detected |
| `python -m unittest tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_pm_route_draft_preserves_role_authored_repair_policy_fields` | Pass | Route draft no longer drops PM-authored repair policy fields |
| `python -m unittest tests.test_flowpilot_output_contracts` | Pass | Contract registry and packet contract projection include artifact handoff |
| `python simulations\run_output_contract_checks.py` | Pass | Output-contract model remains safe |
| `python -m unittest tests.test_flowpilot_role_output_runtime` | Pass | Role-output runtime unchanged mechanically |
| `python simulations\run_flowpilot_role_output_runtime_checks.py` | Pass | Role-output runtime model/source scan passes |
| `python -m unittest tests.test_flowpilot_planning_quality tests.test_flowpilot_reviewer_active_challenge` | Pass | Planning/reviewer prompt expectations remain valid |
| `python simulations\run_protocol_contract_conformance_checks.py` | Fails on pre-existing broader issues | Reports PM resume payload-contract and reviewer-block-lane gaps outside this handoff/artifact upgrade |
| `python -m unittest discover -s tests -p "test_flowpilot_*.py"` | Timed out | Full discovery exceeded 10 minutes and was not used as pass/fail evidence |
