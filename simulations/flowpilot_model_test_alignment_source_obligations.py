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
            "startup.questions.pause_before_work",
            obligation_type="contract",
            description="Source-audited startup boundary for run-until-wait, action application, and next-action answer handling.",
            required_test_kinds=(HAPPY, NEGATIVE),
        ),
        _source_obligation(
            "startup.run_isolation_and_activation",
            obligation_type="scenario",
            description="Source-audited startup activation failure boundary through recorded external events.",
            required_test_kinds=(FAILURE,),
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
            description="Source-audited route mutation precondition boundary through Router events and packet issuance.",
            required_test_kinds=(NEGATIVE,),
        ),
        _source_obligation(
            "route_mutation.sibling_replacement_stales_old_evidence",
            obligation_type="hazard",
            description="Source-audited sibling replacement boundary through Router events, packet issuance, and route-sign output.",
            required_test_kinds=(EDGE, NEGATIVE),
        ),
        _source_obligation(
            "terminal.final_ledger_and_backward_replay",
            obligation_type="invariant",
            description="Source-audited terminal replay/final-ledger boundary through Router event intake.",
            required_test_kinds=(HAPPY, NEGATIVE),
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
            "runtime_closure.officer_lifecycle_contract",
            obligation_type="contract",
            description="Source-audited officer request/result lifecycle records keep PM authority, sealed-body boundaries, and validation results explicit.",
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
            description="Source-audited router owner helper modules expose stable boundaries behind the compatibility facade.",
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
            description="Source-audited card runtime owner modules preserve bundle, envelope, ledger, path, and hash contracts behind the compatibility facade.",
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
