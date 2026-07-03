<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: System-card ACKs go through the current runtime card check-in command; this is the current-runtime return path for card ACKs. Current work-package ACKs and completion outputs go through the assigned current packet lease when present. For formal role outputs, write the body only to a run-scoped packet, result, report, decision, or blocker file, then submit it with `flowpilot_new.py submit-result --lease-id <lease-id> --packet-id <packet-id> --body <sealed_result_summary>` so the current runtime ledger records the event and later exposes only controller-visible envelope metadata with status, paths, and hashes. A local file write is only local storage and must not be treated as wait completion until the current runtime records the packet result. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
post_ack: ACK is receipt only; ACK is not completion. This is a work item when it asks for an output, report, decision, result, or blocker. After work-card ACK, do not stop or wait for another prompt; immediately continue the assigned work and submit the formal output or blocker through the current runtime path. The task remains unfinished until the current runtime receives that output or blocker.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. System-card ACKs, current work-package outputs, and formal role-output submissions go directly through the current runtime commands. Controller must follow the `flowpilot_new.py` lifecycle guard and foreground duty; no unsupported command text, stale runtime state, chat history, or historical artifact authorizes current-run progress.
runtime_context: Treat the runtime delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; submit a protocol blocker through the current runtime path.
-->
# PM Final Ledger Phase

## Role Capability Reminder

- Formal work products must live in run-scoped files or project artifacts. Handoff messages point to artifacts with paths/hashes, changed paths when applicable, output contract, inspection notes, and PM Suggestion Items; the message body is not the sole work product.
- PM may directly disposition suggestions when evidence is sufficient. Consultation is optional, not a mandatory step for every suggestion.
- If PM lacks basis, or the suggestion may affect route, product target, acceptance, process safety, replay, repair return path, or risk boundary, PM may request bounded consultation through an allowed role-work request, then must record a final PM disposition after reading the advice artifact.
- If a PM-owned decision still lacks evidence, modeling, research, review, or implementation support, register a bounded `pm_registers_role_work_request` only when the router's current `allowed_external_events` includes that event; otherwise record the limitation or blocker instead of emitting it.
- Treat the router's current `allowed_external_events` as the active authority for what this card may return.
- Put reviewer, worker, and FlowGuard operator advice that needs PM disposition into the PM suggestion/blocker ledger instead of leaving it only in prose.
- For non-trivial final-ledger, model-coverage, validation, evidence-freshness, terminal-replay, or completion-readiness judgement, cite FlowGuard Work Order and FlowGuard Report ids with freshness and PM acceptance, or record a scoped `flowguard_not_required_reason`.


Build the final route-wide gate ledger from the current route, not the initial
route.
Before building it, read the latest route-memory prior path context and use it
to make sure every completed, superseded, stale, repaired, blocked, and
experiment-influenced path is represented.
Also read `self_interrogation_index.json`. The final ledger must cite that
index, record `self_interrogation_index_clean: true`, and show zero unresolved
hard/current self-interrogation findings before terminal replay can become a
closure path.
Also read the current run-scoped `material_artifact_map.json`. The final ledger
must cite it when present and show zero blocked, stale, or unresolved material
artifact-map counts before terminal replay can become a closure path. The map
summary is an index only; final closure still depends on direct evidence paths,
reviewer gates, and PM-owned source files.
The map is not a permission allowlist. PM, Worker, FlowGuard operator, and
Reviewer may inspect any non-sealed project/run material needed for their
current duty. Sealed packet, result, report, and mail/letter bodies remain
runtime-authorized only.
If Router blocks ledger submission through a `control_blocker`, read the
policy row. Ledger, stale-evidence, and self-interrogation blockers return to
PM recovery; PM may rebuild the ledger, roll back to the affected node/gate,
insert supplemental evidence work, quarantine stale evidence, mutate route, or
stop for the user, but must name the return gate and cannot mark the terminal
ledger clean by waiver when hard-stop conditions remain.

Write `.flowpilot/runs/<run-id>/final_route_wide_gate_ledger.json` as the
source of truth for completion.

Resolve:

- requirement trace closure for every effective root requirement and every
  imported product requirement that remains active. Each row must name source
  requirement ids, change status, owner nodes, covering ledger entries, direct
  evidence paths, standard scenarios, stale evidence refs, waiver authority,
  supersession, and unresolved reason;
- acceptance item closure for every active `acceptance_item_id` in the
  accepted registry. Each row must name source type, source requirement ids,
  quality floor, required evidence, owner nodes, closed-by nodes, reviewer or
  FlowGuard gates, evidence paths, waiver authority, final replay requirement,
  and unresolved reason. A user-sourced or PM high-standard item that is
  orphaned, missing evidence, waived without authority, or closed only by
  generic prose keeps the final ledger open;
- terminal supplemental repair closure for every
  `supplemental_repair_contract` created after terminal backward replay.
  Each row must cite the original frozen contract hash, terminal Reviewer gap
  result, repair round, repair item id, owner repair node, acceptance item
  links, required evidence, current evidence ids, and status. A repair item
  with no owner node, no node projection, stale/missing evidence, or an
  unaccepted repair node keeps the final ledger and requirement matrix open;
- FlowGuard modeling coverage closure: startup capability snapshot, Product
  Modeling Plan, all accepted product model families, ordinary child-skill
  model-family projection, Process Modeling Plan, all accepted process model
  families, merge/skip reasons, and unresolved model-family count. Completion
  is blocked if any planned product or process family is missing, unresolved,
  stale, or closed only by child-skill manifest prose;
  include the accepted target-realization model and PM decision. Every active
  realization obligation, thin-success trap, non-downgrade rule, and evidence
  gate must have terminal disposition: closed by proof, superseded with reason,
  waived by authority, or returned for repair;
  include every active `flowguard_work_order_id`, `flowguard_report_id`,
  `flowguard_route_used`, `flowguard_report_freshness`, skipped-check reason,
  progress-only status, and `flowguard_pm_acceptance`; unresolved, stale,
  blocked, or unaccepted FlowGuard reports keep the ledger open;
  before writing the final route-wide ledger, include a PM-accepted
  `flowguard_terminal_coverage_closure` that points to the current
  `flowpilot.flowguard_terminal_coverage_report.v1` report and fresh coverage
  matrix for this route version. Scattered node-level FlowGuard notes,
  progress-only reports, stale reports, unresolved blockers, undispositioned
  PM suggestion items, or unaccepted reports do not count as terminal
  coverage closure;
- effective and superseded nodes;
- every major node, parent/module, child subtree, promoted former leaf, repair
  node, and supplemental node in the current route. Before project completion,
  walk backward over the whole route and prove that no major node or subtree
  was skipped;
- final-user intent and delivered-product usefulness claims, including the
  evidence that proves each current user-facing claim instead of merely proving
  that an artifact exists;
- low-quality-success risks inherited from product architecture, root
  contract, route nodes, and node acceptance plans. Each hard risk must have
  terminal disposition: closed by proof of depth, superseded with reason,
  waived by authority, or returned for repair. A hard part cannot be closed by
  existence-only evidence, report prose, or a clean ledger row;
- child-skill and review gates;
- product/process FlowGuard gates;
- final evidence id validity: review, FlowGuard, and validation ids only count
  when the runtime resolves the referenced current-route record as accepted,
  passing, fresh, and blocker-free. A blocked review id, progress-only or stale
  FlowGuard order, failed validation record, old-route id, or historical
  artifact remains unresolved evidence rather than proof;
- model-test alignment for every active FlowGuard-backed gate:
  `model_obligations`, `ordinary_test_evidence`, `missing_test_kinds`,
  `conformance_boundary`, `residual_blindspots`, PM
  current evidence disposition, and any long/background check completion
  required for cited long/background tests. Completion cannot count ordinary
  tests as model coverage when required test kinds are missing, stale, skipped,
  failed, still running, undispositioned by PM, or supported only by progress
  logs without exit/meta artifacts;
- minimum sufficient complexity dispositions for route nodes, skills, and
  artifacts that were considered, superseded, deferred, or discarded;
- structure debt dispositions for patch stacks, fallback-like paths,
  compatibility branches, duplicate adapters, stale generated artifacts,
  non-current evidence, and retained maintenance layers. Each item must be
  removed, rejected, preserved as
  negative rejection evidence, retained as owned current-runtime recovery,
  retained as owned maintenance, superseded, or blocked. Any retained surface
  must name owner, scope, validation evidence, and sunset or
  next-disposition criteria. Unowned, unresolved, or compatibility-by-default
  paths keep the ledger open;
- final artifact hygiene closure for every current final hygiene finding from
  PM evidence quality review or terminal Reviewer replay. Rows must identify
  artifact family, direct surface, classification, owner repair node or PM
  disposition, evidence refs, and unresolved status. Findings classified as
  `current_goal_required_repair` or `clean_delivery_required_repair` keep the
  final ledger open until repaired through current FlowPilot gates, waived with
  authority, route-mutated, or stopped. `pm_decision_support` and
  `future_contract_candidate` items require PM disposition but do not count as
  current closure blockers unless PM imports them into the supplemental repair
  contract;
- generated-resource lineage;
- stale, invalid, missing, waived, blocked, or superseded evidence;
- old evidence that attempts to close a changed or superseded requirement;
- whole-output composition closure: start from the final delivered artifact,
  software behavior, document, story, report, workflow, or skill behavior and
  confirm that route results form one coherent user-facing outcome. Node-level
  passes do not close this row by themselves when the final output is
  scattered, contradictory, duplicative without purpose, missing callbacks, or
  unable to carry the root intent. Optional concision or polish improvements
  remain PM decision-support when hard root/acceptance proof is closed;
- zero unresolved count;
- zero unresolved requirement count;
- zero unresolved residual risks.

If the final backward walk finds an omitted major node, omitted subtree,
unclosed bug class, unresolved hard low-quality-success risk, or stale evidence
class, first decide whether the
Product/FlowGuard operator process model missed the class. When it did, update the
model, search the same class across the whole route, add supplemental or repair
nodes, rerun stale gates, rebuild this ledger, and only then request terminal
Reviewer replay.

Return `prior_path_context_review` and cite both route-memory files. If any
repair or route mutation happened after that context was refreshed, block and
ask Controller to refresh route memory before building the ledger.

Then build `terminal_human_backward_replay_map.json` as ordered segments from
delivered output to root, parents, leaves, child-skill gates, repairs, and
generated resources. Request terminal backward replay from Reviewer; any repair
or stale evidence found there requires ledger rebuild before closure.
The replay map must include the `flowguard-coverage-governance` segment so
Reviewer explicitly checks that the PM ledger contains current terminal
FlowGuard coverage closure.
The replay map must start from the delivered product or final output as a
final user, reader, operator, maintainer, or recipient would experience it, and
then walk backward to route evidence and root intent.

Do not let unused complexity survive as a completion note. Extra nodes, skills,
resources, reports, or validation branches must either prove a current gate,
be explicitly superseded, be quarantined, or be discarded with a concrete
reason before unresolved count can be zero.

Do not complete from ledger existence alone. Completion requires direct
evidence or approved disposition for each effective requirement, plus terminal
Reviewer backward replay from delivered output back to root intent.
