"""Source-audited model obligations for FlowPilot model-test alignment."""

from __future__ import annotations

from flowpilot_model_test_alignment_common import *

def _source_obligation(
    obligation_id: str,
    *,
    obligation_type: str,
    description: str,
    required_test_kinds: Sequence[str],
    allow_shared_evidence: bool = False,
) -> ModelObligation:
    return _obligation(
        obligation_id,
        obligation_type=obligation_type,
        description=description,
        required_test_kinds=required_test_kinds,
        allow_shared_evidence=allow_shared_evidence,
        allow_shared_implementation=True,
    )




def source_obligations() -> tuple[ModelObligation, ...]:
    """Return source-audited model obligations."""

    return (
        _source_obligation(
            "current_contract.structured_authority_references",
            obligation_type="invariant",
            description=(
                "Current node context accepts only typed, current-run authority references with exact "
                "path fingerprints and required route, packet, result, node, and generation identity."
            ),
            required_test_kinds=(HAPPY, NEGATIVE),
            allow_shared_evidence=True,
        ),
        _source_obligation(
            "current_contract.exact_requested_role_resume",
            obligation_type="transition",
            description=(
                "Manual resume and role-memory recovery target every and only roles owning a current "
                "unresolved obligation; idle, historical, fixed-roster, stale, and foreign roles stay audit-only."
            ),
            required_test_kinds=(HAPPY, NEGATIVE),
            allow_shared_evidence=True,
        ),
        _source_obligation(
            "current_contract.staged_effect_exact_identity",
            obligation_type="invariant",
            description=(
                "A pending staged effect is reusable only for the exact source packet/result, target, "
                "blocker, trigger gate, scope, repair generation, and source generation."
            ),
            required_test_kinds=(HAPPY, NEGATIVE),
            allow_shared_evidence=True,
        ),
        _source_obligation(
            "current_contract.terminal_exact_segment_replay",
            obligation_type="invariant",
            description=(
                "Terminal backward replay accounts exact route segments, final artifacts, acceptance items, "
                "blockers, and waivers without aggregate or newest-result substitution."
            ),
            required_test_kinds=(HAPPY, NEGATIVE),
            allow_shared_evidence=True,
        ),
        _source_obligation(
            "current_contract.reviewer_workstream_semantics",
            obligation_type="contract",
            description=(
                "The existing workstream plan remains a planning and Reviewer comparison surface; Runtime "
                "projects mechanical shape but does not score narrative completeness or replace substantive review."
            ),
            required_test_kinds=(HAPPY, NEGATIVE),
            allow_shared_evidence=True,
        ),
        _source_obligation(
            "current_contract.daemon_descendant_zero_cleanup",
            obligation_type="hazard",
            description=(
                "The Router daemon owner binds exact process identity, continuously accumulates exact "
                "descendants throughout the stop window, and produces descendant-zero cleanup proof "
                "before releasing its lock or admitting a terminal stop."
            ),
            required_test_kinds=(EDGE,),
            allow_shared_evidence=True,
        ),
        _source_obligation(
            "current_contract.process_tree_descendant_lineage",
            obligation_type="hazard",
            description=(
                "A process can enter an exact owner's descendant set only when its orderable start "
                "token is not earlier than that owner; stale Windows parent-PID links cannot authorize "
                "termination of a pre-existing process."
            ),
            required_test_kinds=(NEGATIVE,),
        ),
        _source_obligation(
            "current_contract.background_child_descendant_zero_cleanup",
            obligation_type="hazard",
            description=(
                "Each heavyweight background validation owner binds exact process identity, allows one "
                "bounded natural-exit settlement window, and produces descendant-zero cleanup proof "
                "before its terminal receipt can be reused; any descendant surviving that window fails closed."
            ),
            required_test_kinds=(NEGATIVE, EDGE),
            allow_shared_evidence=True,
        ),
        _source_obligation(
            "current_contract.background_toolchain_identity",
            obligation_type="evidence_freshness",
            description=(
                "A heavyweight background owner binds an inner Python command to the current "
                "execution-owner interpreter and, on Windows virtual environments, launches the "
                "bound base interpreter as the direct process owner while preserving the virtual-"
                "environment identity, so an external FlowGuard upgrade or short-lived launcher "
                "shim cannot change or prematurely end one frozen release plan."
            ),
            required_test_kinds=(EDGE,),
        ),
        _source_obligation(
            "current_contract.owner_scoped_evidence_applicability",
            obligation_type="evidence_freshness",
            description=(
                "The canonical repository snapshot is provenance only. Each tier command has one explicit "
                "owner input identity; current exact identity reuses one prior v4 proof through a valid "
                "TestResultReuseTicket, changed identity executes that owner, and any unmapped or ambiguous "
                "changed input blocks without a blanket-run fallback."
            ),
            required_test_kinds=(HAPPY, NEGATIVE),
            allow_shared_evidence=True,
        ),
        _source_obligation(
            "startup.questions.pause_before_work",
            obligation_type="contract",
            description="Source-audited startup boundary for run-until-wait, action application, and next-action answer handling.",
            required_test_kinds=(HAPPY, NEGATIVE),
        ),
        _source_obligation(
            "startup.run_isolation_and_activation",
            obligation_type="scenario",
            description="Source-audited startup boundary that rejects legacy reviewer/PM startup role gate events.",
            required_test_kinds=(FAILURE,),
        ),
        _source_obligation(
            "startup.runtime_writer_settlement",
            obligation_type="invariant",
            description=(
                "Foreground startup begins its bounded writer-settlement budget at first contention, "
                "treats transient daemon-readiness sharing violations and Windows write-lock acquire "
                "permission errors as current writer contention, allocates one current run before "
                "advancement, reattaches the exact current in-flight daemon, preserves completed "
                "folded-action evidence across retry, and still fails closed for a persistent current writer."
            ),
            required_test_kinds=(HAPPY, NEGATIVE, EDGE),
            allow_shared_evidence=True,
        ),
        _source_obligation(
            "new_entrypoint.startup_ui_to_new_ledger",
            obligation_type="contract",
            description="Source-audited fresh FlowPilot entrypoint boundary from native startup UI output into the new current-run ledger.",
            required_test_kinds=(HAPPY,),
        ),
        _source_obligation(
            "new_entrypoint.formal_headless_rejection",
            obligation_type="hazard",
            description="Source-audited fresh FlowPilot entrypoint boundary that rejects headless startup output as formal startup evidence.",
            required_test_kinds=(NEGATIVE,),
        ),
        _source_obligation(
            "new_entrypoint.rehearsal_closure",
            obligation_type="scenario",
            description="Source-audited fake-host rehearsal boundary proving startup, packet, FlowGuard, review, validation, and closure can compose.",
            required_test_kinds=(HAPPY,),
        ),
        _source_obligation(
            "new_entrypoint.blackbox_fake_project_rehearsal",
            obligation_type="scenario",
            description="Source-audited black-box fake project rehearsal boundary proving the public CLI and startup UI script can drive normal and error packet flows without internal helper proof.",
            required_test_kinds=(HAPPY, NEGATIVE, EDGE),
            allow_shared_evidence=True,
        ),
        _source_obligation(
            "new_entrypoint.symmetric_role_packet_lifecycle",
            obligation_type="invariant",
            description="Source-audited new-entrypoint packet lifecycle boundary requiring requested PM, FlowGuard operator, reviewer, and worker responsibilities to use issued packet, lease, ACK, result, packet-owned side effect, and clean lease projection while system validation and closure remain ledger outcomes.",
            required_test_kinds=(HAPPY, NEGATIVE, EDGE),
        ),
        _source_obligation(
            "new_entrypoint.role_lease_requires_matching_packet",
            obligation_type="hazard",
            description="Source-audited dynamic lease boundary rejecting a backend role lease against another responsibility's packet before allowing the role through its own issued packet.",
            required_test_kinds=(NEGATIVE,),
        ),
        _source_obligation(
            "new_entrypoint.side_command_surface_unsupported",
            obligation_type="hazard",
            description="Source-audited formal public surface boundary that omits unsupported direct FlowGuard, review, validation, and closure side-command paths.",
            required_test_kinds=(NEGATIVE,),
        ),
        _source_obligation(
            "new_entrypoint.host_kind_value_menu",
            obligation_type="contract",
            description="Source-audited dynamic host-kind boundary requiring prompts and CLI help to enumerate live/fake/dry_run and reject invented values such as codex_background_worker.",
            required_test_kinds=(HAPPY, NEGATIVE),
        ),
        _source_obligation(
            "new_entrypoint.portable_runtime_self_check_receipt",
            obligation_type="install_portability_contract",
            description="Source-audited installed FlowPilot start boundary records a run-local runtime self-check receipt and proves target projects are not required to contain FlowPilot development-repository simulation scripts.",
            required_test_kinds=(HAPPY, NEGATIVE),
            allow_shared_evidence=True,
        ),
        _source_obligation(
            "new_entrypoint.blackbox_fake_project_result_portability",
            obligation_type="evidence_projection",
            description=(
                "Tracked fake-project rehearsal results project repository and temporary work roots "
                "to portable identifiers without weakening the black-box scenario evidence."
            ),
            required_test_kinds=(EDGE,),
            allow_shared_evidence=True,
        ),
        _source_obligation(
            "new_entrypoint.flowguard_run_local_evidence",
            obligation_type="contract",
            description="Source-audited FlowGuard operator packet and runner-output boundary requiring formal evidence to use run-local output paths instead of tracked simulation baselines.",
            required_test_kinds=(HAPPY, NEGATIVE),
            allow_shared_evidence=True,
        ),
        _source_obligation(
            "new_entrypoint.lifecycle_guard_stop_authority",
            obligation_type="invariant",
            description="Source-audited new-runtime lifecycle guard boundary blocks nonterminal Controller stop and allows terminal return only after final closure.",
            required_test_kinds=(HAPPY, NEGATIVE),
            allow_shared_evidence=True,
        ),
        _source_obligation(
            "new_entrypoint.lifecycle_guard_resume_patrol",
            obligation_type="transition",
            description="Source-audited lifecycle guard resume and patrol boundary rehydrates current-run state and classifies repeated waits without old monitor UI authority.",
            required_test_kinds=(HAPPY, EDGE),
            allow_shared_evidence=True,
        ),
        _source_obligation(
            "new_entrypoint.lifecycle_guard_stale_result_quarantine",
            obligation_type="hazard",
            description="Source-audited lifecycle guard result boundary rejects or quarantines inactive-lease, superseded-packet, stale-route, and stale-generation results.",
            required_test_kinds=(NEGATIVE,),
            allow_shared_evidence=True,
        ),
        _source_obligation(
            "packet.physical_body_boundary",
            obligation_type="contract",
            description="Source-audited Controller handoff boundary that keeps packet bodies out of Controller relay text.",
            required_test_kinds=(NEGATIVE,),
        ),
        _source_obligation(
            "card.ack_identity_and_bundle",
            obligation_type="hazard",
            description="Source-audited card open/ACK/validation contract for externally visible card acknowledgement mechanics.",
            required_test_kinds=(HAPPY,),
        ),
        _source_obligation(
            "ack.return_wait_preconsumption",
            obligation_type="transition",
            description="Source-audited ACK preconsumption boundary through Router events and card ACK helpers.",
            required_test_kinds=(EDGE,),
        ),
        _source_obligation(
            "route_mutation.topology_and_recheck",
            obligation_type="contract",
            description="Source-audited route mutation precondition boundary through Router events, exact pre-write route-memory authority, and packet issuance.",
            required_test_kinds=(HAPPY, NEGATIVE),
        ),
        _source_obligation(
            "route_mutation.sibling_replacement_stales_old_evidence",
            obligation_type="hazard",
            description="Source-audited sibling replacement boundary through Router events, packet issuance, and route-sign output.",
            required_test_kinds=(EDGE, NEGATIVE),
        ),
        _source_obligation(
            "unified_repair.pm_historical_direct_entry_no_blocker",
            obligation_type="transition",
            description=(
                "Source-audited PM historical-defect entry accepts a structured defect observation, target node, "
                "and impact frontier without requiring a manufactured semantic blocker."
            ),
            required_test_kinds=(HAPPY, NEGATIVE),
            allow_shared_evidence=True,
        ),
        _source_obligation(
            "route_authority.rejection_feedback_projection",
            obligation_type="contract",
            description="Source-audited route-authority rejection helper boundary that projects wrong-path events, missing prerequisite flags, and unsupported payload fields into current-contract feedback.",
            required_test_kinds=(EDGE,),
            allow_shared_evidence=True,
        ),
        _source_obligation(
            "terminal.final_ledger_and_backward_replay",
            obligation_type="invariant",
            description="Source-audited terminal replay/final-ledger boundary through Router event intake.",
            required_test_kinds=(HAPPY, NEGATIVE),
        ),
        _source_obligation(
            "terminal.final_ledger_source_entries",
            obligation_type="contract",
            description="Leaf source-audited final-ledger source-entry construction boundary for root replay, route node, superseded node, child-skill, evidence, and generated-resource gate families.",
            required_test_kinds=(EDGE,),
        ),
        _source_obligation(
            "terminal.requirement_trace_projection",
            obligation_type="contract",
            description="Leaf source-audited terminal requirement-trace projection boundary for route-node defaults and root-replay closure rows.",
            required_test_kinds=(EDGE,),
        ),
        _source_obligation(
            "resume.current_run_reentry",
            obligation_type="transition",
            description="Source-audited resume re-entry boundary through Router event intake, next action, and action application.",
            required_test_kinds=(HAPPY, FAILURE),
        ),
        _source_obligation(
            "role_output.registry_authority",
            obligation_type="contract",
            description="Source-audited role-output session preparation contract.",
            required_test_kinds=(HAPPY,),
        ),
        _source_obligation(
            "pm_package_disposition.semantic_identity_and_packet_outcomes",
            obligation_type="hazard",
            description="Source-audited PM package disposition boundary dedupes by package identity, treats body hash as conflict evidence, and records per-packet outcomes before aggregate absorption.",
            required_test_kinds=(EDGE, NEGATIVE),
            allow_shared_evidence=True,
        ),
        _source_obligation(
            "controller_aside.metadata_only_boundary",
            obligation_type="contract",
            description="Source-audited Controller process-aside boundary keeps brief status metadata from becoming formal evidence, decisions, progress authority, or Router events.",
            required_test_kinds=(NEGATIVE,),
        ),
        _source_obligation(
            "material_artifact_map.index_only_boundary",
            obligation_type="contract",
            description="Source-audited optional material artifact map stays absent without blocking when not explicitly created, and indexes existing ordinary evidence without reading sealed packet or result body text or changing authority when present.",
            required_test_kinds=(HAPPY, NEGATIVE, EDGE, REPLAY),
            allow_shared_evidence=True,
        ),
        _source_obligation(
            "branch_pruning.result_case_classifier",
            obligation_type="contract",
            description="Source-audited Router reconciliation branch-pruning classifier maps target branches into the shared result-case vocabulary.",
            required_test_kinds=(HAPPY, NEGATIVE),
            allow_shared_evidence=True,
        ),
        _source_obligation(
            "branch_pruning.scheduled_receipt_effect_cases",
            obligation_type="scenario",
            description="Source-audited scheduled Controller receipt branch families declare observable writes and replay gates before contraction.",
            required_test_kinds=(REPLAY, NEGATIVE),
            allow_shared_evidence=True,
        ),
        _source_obligation(
            "branch_pruning.role_output_authority_cases",
            obligation_type="hazard",
            description="Source-audited role-output branch pruning keeps not-ready and unauthorized envelopes separate from reconciled events.",
            required_test_kinds=(HAPPY, NEGATIVE),
            allow_shared_evidence=True,
        ),
        _source_obligation(
            "branch_pruning.runtime_state_resume_cases",
            obligation_type="contract",
            description="Source-audited runtime-state resume pruning remains model-only with a single owner until replay evidence justifies contraction.",
            required_test_kinds=(EDGE, NEGATIVE),
            allow_shared_evidence=True,
        ),
        _source_obligation(
            "runtime_state.stale_save_merge_boundary",
            obligation_type="contract",
            description="Leaf source-audited runtime-state stale-save merge boundary preserves append-only lists, pending-wait reminder details, foreground clears, and volatile metadata exclusion.",
            required_test_kinds=(EDGE,),
        ),
        _source_obligation(
            "runtime_state.load_save_persistence_boundary",
            obligation_type="contract",
            description="Leaf source-audited runtime-state load/save boundary preserves run-root binding, default normalization, facade return shape, and save metadata refresh.",
            required_test_kinds=(EDGE,),
        ),
        _source_obligation(
            "output_contract.packet_binding",
            obligation_type="contract",
            description="Source-audited packet output contract across packet creation, Controller relay, and result writes.",
            required_test_kinds=(HAPPY,),
        ),
        _source_obligation(
            "router_loop.packet_result_review_loop",
            obligation_type="transition",
            description="Source-audited current-node packet/result review loop boundary through Router event intake.",
            required_test_kinds=(HAPPY, FAILURE),
        ),
        _source_obligation(
            "runtime_closure.flowguard_operator_lifecycle_contract",
            obligation_type="contract",
            description="Source-audited FlowGuard operator request/result lifecycle records keep PM authority, sealed-body boundaries, and validation results explicit.",
            required_test_kinds=(HAPPY,),
        ),
        _source_obligation(
            "runtime_closure.continuation_and_final_report_contract",
            obligation_type="contract",
            description="Source-audited continuation quarantine, final user report, and route display refresh records separate current-run authority from display/report artifacts.",
            required_test_kinds=(HAPPY,),
        ),
        _source_obligation(
            "daemon.lock_status_queue_contract",
            obligation_type="contract",
            description="Source-audited daemon lock/status/tick contracts prevent duplicate writers and distinguish live, stale, stopped, and errored daemon states.",
            required_test_kinds=(HAPPY, EDGE, NEGATIVE),
        ),
        _source_obligation(
            "startup_daemon.lock_liveness_contract",
            obligation_type="contract",
            description="Source-audited startup-daemon liveness helpers classify lock freshness and heartbeat monitor requirements.",
            required_test_kinds=(HAPPY,),
        ),
        _source_obligation(
            "runtime_owner.high_priority_owner_contracts",
            obligation_type="contract",
            description="Source-audited runtime owner modules expose stable owner-boundary helpers with concrete output and failure contracts.",
            required_test_kinds=(HAPPY, NEGATIVE),
            allow_shared_evidence=True,
        ),
        _source_obligation(
            "runtime_owner.router_boundary_helpers",
            obligation_type="contract",
            description="Source-audited router owner helper modules expose stable boundaries behind the unsupported_historical facade.",
            required_test_kinds=(HAPPY,),
            allow_shared_evidence=True,
        ),
        _source_obligation(
            "runtime_owner.router_owner_external_contracts",
            obligation_type="contract",
            description="Source-audited router owner modules expose direct external contracts for action envelopes, dispatch gates, action handlers, artifact validation, card delivery, child-skill capability sync, and controller scheduler ledgers.",
            required_test_kinds=(HAPPY, NEGATIVE),
            allow_shared_evidence=True,
        ),
        _source_obligation(
            "runtime_owner.receipt_bootloader_policy_boundary",
            obligation_type="contract",
            description="Leaf source-audited Controller receipt bootloader policy boundary preserves boot action matching and startup bootloader receipt effects.",
            required_test_kinds=(EDGE,),
        ),
        _source_obligation(
            "runtime_owner.receipt_packet_fold_registry_boundary",
            obligation_type="contract",
            description="Leaf source-audited Controller receipt packet-fold registry boundary preserves registered packet/result/control-blocker action metadata and sorted action exposure.",
            required_test_kinds=(EDGE,),
        ),
        _source_obligation(
            "runtime_owner.receipt_packet_fold_lifecycle_boundary",
            obligation_type="contract",
            description="Leaf source-audited Controller receipt packet-fold lifecycle boundary maps packet/result receipt specs to only the allowed batch and PM role-work lifecycle writes.",
            required_test_kinds=(EDGE,),
        ),
        _source_obligation(
            "runtime_owner.receipt_scheduled_policy_boundary",
            obligation_type="contract",
            description="Leaf source-audited scheduled receipt policy child owns scheduler-row reconciliation lookup, backfill, pending-action clearing, and apply-result classification.",
            required_test_kinds=(EDGE,),
        ),
        _source_obligation(
            "runtime_owner.current_work_pending_policy_boundary",
            obligation_type="contract",
            description="Leaf source-audited current-work pending policy boundary preserves controller authority, scheduler lookup, durable wait clearing, and batch projection decisions.",
            required_test_kinds=(EDGE,),
        ),
        _source_obligation(
            "runtime_owner.standby_state_policy_boundary",
            obligation_type="contract",
            description="Leaf source-audited foreground Controller standby state-policy boundary maps the full terminal/user/liveness/pending/wait-condition input matrix to the only allowed standby states and foreground modes.",
            required_test_kinds=(EDGE,),
        ),
        _source_obligation(
            "runtime_owner.role_output_bridge_event_policy_boundary",
            obligation_type="contract",
            description="Leaf source-audited role-output bridge event policy boundary preserves body payload reading and durable event authority checks.",
            required_test_kinds=(EDGE,),
        ),
        _source_obligation(
            "runtime_owner.startup_intake_flowguard_capability_boundary",
            obligation_type="contract",
            description="Leaf source-audited startup intake FlowGuard capability boundary owns finite route classification, import snapshot, and portable capability snapshot writes.",
            required_test_kinds=(EDGE,),
        ),
        _source_obligation(
            "runtime_owner.lifecycle_startup_direct_helper_boundary",
            obligation_type="contract",
            description="Leaf source-audited lifecycle/startup direct helper boundary owns terminal lifecycle writes, startup run-state repair, manual resume binding, and system card commit effects.",
            required_test_kinds=(NEGATIVE,),
        ),
        _source_obligation(
            "packet_runtime.owner_helper_contracts",
            obligation_type="contract",
            description="Source-audited packet runtime owner helpers preserve schema, path, hash, contract, and audit boundaries.",
            required_test_kinds=(HAPPY,),
        ),
        _source_obligation(
            "packet_control_plane.runner_contract",
            obligation_type="contract",
            description="Source-audited packet control-plane runner returns a FlowGuard report-derived exit status.",
            required_test_kinds=(HAPPY,),
        ),
        _source_obligation(
            "card_runtime.owner_helper_contracts",
            obligation_type="contract",
            description="Source-audited card runtime owner modules preserve bundle, envelope, ledger, path, and hash contracts behind the unsupported_historical facade.",
            required_test_kinds=(HAPPY,),
            allow_shared_evidence=True,
        ),
        _source_obligation(
            "packet_runtime.runtime_owner_contracts",
            obligation_type="contract",
            description="Source-audited packet runtime owner modules preserve startup packet, holder/progress, ledger, CLI parsing, and session metadata contracts.",
            required_test_kinds=(HAPPY,),
            allow_shared_evidence=True,
        ),
        _source_obligation(
            "packet_control_plane.model_state_contract",
            obligation_type="contract",
            description="Source-audited packet control-plane model state helpers map case ids to packet boundary conditions.",
            required_test_kinds=(HAPPY,),
            allow_shared_evidence=True,
        ),
        _source_obligation(
            "role_output_runtime.owner_helper_contracts",
            obligation_type="contract",
            description="Source-audited role-output runtime owner modules preserve contract skeleton, CLI, schema boundary, and envelope recovery contracts.",
            required_test_kinds=(HAPPY,),
            allow_shared_evidence=True,
        ),
        _source_obligation(
            "runtime_path_contracts.runtime_evidence_binding",
            obligation_type="contract",
            description="Source-audited runtime-path evidence helper binds FlowPilot model obligations to FlowGuard runtime node contracts, observations, runs, and parseable progress lines.",
            required_test_kinds=(HAPPY,),
        ),
        _source_obligation(
            "workflow_step_contracts.next_step_projection",
            obligation_type="workflow_step",
            description="Source-audited FlowGuard workflow-step contract projection for FlowPilot next_step_contract records, including Controller receipts, ACK-only settlement, target-work output, stale receipt invalidation, and claim gates.",
            required_test_kinds=(HAPPY, NEGATIVE, EDGE),
            allow_shared_evidence=True,
        ),
        _source_obligation(
            "test_tiering.foreground_fast_scope",
            obligation_type="contract",
            description="Source-audited test-tier command selection boundary.",
            required_test_kinds=(NEGATIVE,),
        ),
        _source_obligation(
            "meta_parent.thin_default_and_layered_full_boundary",
            obligation_type="contract",
            description="Source-audited Meta runner entrypoint for thin-parent default evidence.",
            required_test_kinds=(HAPPY,),
        ),
        _source_obligation(
            "capability_parent.proof_reuse_and_fast_boundary",
            obligation_type="contract",
            description="Source-audited smoke fast-path entrypoint for Capability proof boundary evidence.",
            required_test_kinds=(NEGATIVE,),
        ),
    )
