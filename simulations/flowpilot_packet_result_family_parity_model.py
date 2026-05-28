"""FlowGuard obligation-family parity model for FlowPilot packet results."""

from __future__ import annotations

from typing import Any, Sequence

from flowguard import (
    AnalogousDefectCandidate,
    FamilyBadCaseSeed,
    ObligationFamily,
    ObligationFamilyEvidence,
    ObligationFamilyMember,
    review_analogous_defect_scan,
    review_obligation_family_parity,
)


FAMILY_ID = "flowpilot.packet_result_return_reconciliation"

MEMBERS = (
    "material_scan",
    "research",
    "current_node",
    "pm_role_work",
)

MECHANISMS = (
    "full_durable_envelope_event_fold",
    "partial_member_wait_projection",
    "stale_reminder_suppression",
    "wrong_recipient_rejection",
    "sealed_body_provenance",
)

RUNTIME_COMMAND = "python -m unittest tests.router_runtime.packet_result_family"
MODEL_COMMAND = (
    "python simulations/run_flowpilot_packet_result_family_parity_checks.py "
    "--json-out simulations/flowpilot_packet_result_family_parity_results.json"
)
MATERIAL_FULL_COMMAND = (
    "python -m unittest "
    "tests.router_runtime.packets.PacketsRuntimeTests."
    "test_material_scan_existing_results_reconcile_before_stale_wait"
)
MATERIAL_PARTIAL_COMMAND = (
    "python -m unittest "
    "tests.router_runtime.packets.PacketsRuntimeTests."
    "test_material_scan_partial_batch_status_names_missing_role"
)
MATERIAL_SEALED_COMMAND = (
    "python -m unittest "
    "tests.router_runtime.material_modeling.MaterialModelingRuntimeTests."
    "test_material_scan_result_receipt_folds_batch_lifecycle"
)
PM_ROLE_WORK_WRONG_RECIPIENT_COMMAND = (
    "python -m unittest "
    "tests.router_runtime.pm_role_work.PmRoleWorkRuntimeTests."
    "test_strict_pm_role_work_result_rejects_wrong_next_recipient"
)


def _command_for(member: str, mechanism: str) -> str:
    if member == "material_scan":
        if mechanism == "full_durable_envelope_event_fold":
            return MATERIAL_FULL_COMMAND
        if mechanism in {"partial_member_wait_projection", "stale_reminder_suppression"}:
            return MATERIAL_PARTIAL_COMMAND
        if mechanism == "sealed_body_provenance":
            return MATERIAL_SEALED_COMMAND
    if member == "pm_role_work" and mechanism == "wrong_recipient_rejection":
        return PM_ROLE_WORK_WRONG_RECIPIENT_COMMAND
    return RUNTIME_COMMAND


def build_family() -> ObligationFamily:
    return ObligationFamily(
        family_id=FAMILY_ID,
        description=(
            "Every Router-owned packet-result family must reconcile durable "
            "result envelopes into existing result-return control-plane "
            "events before waits/reminders or broad confidence claims."
        ),
        members=tuple(
            ObligationFamilyMember(
                member_id=member,
                description=f"FlowPilot packet-result reconciliation member: {member}",
                obligation_ids=(
                    f"packet_result_family.{member}.durable_event_fold",
                    f"packet_result_family.{member}.partial_wait",
                    f"packet_result_family.{member}.recipient_and_sealed_boundary",
                ),
            )
            for member in MEMBERS
        ),
        required_mechanisms=MECHANISMS,
        allowed_provenance=("runtime_test", "flowguard_model"),
        require_external_evidence=True,
        require_proof_artifacts=False,
        allow_scoped_confidence=False,
        metadata={
            "owner_boundary": "Router durable wait reconciliation",
            "controller_visibility": "metadata_only",
        },
    )


def _evidence(
    member: str,
    mechanism: str,
    *,
    evidence_id: str | None = None,
    command: str = RUNTIME_COMMAND,
    provenance: str = "runtime_test",
    current: bool = True,
    result_status: str = "passed",
    summary: str = "",
) -> ObligationFamilyEvidence:
    return ObligationFamilyEvidence(
        evidence_id=evidence_id or f"{FAMILY_ID}.{member}.{mechanism}",
        family_id=FAMILY_ID,
        member_id=member,
        mechanism_id=mechanism,
        provenance=provenance,
        result_status=result_status,
        current=current,
        assertion_scope="external_contract",
        covered_obligations=(
            f"packet_result_family.{member}.durable_event_fold",
            f"packet_result_family.{member}.partial_wait",
            f"packet_result_family.{member}.recipient_and_sealed_boundary",
        ),
        command=command,
        summary=summary or f"{member} covers {mechanism} through packet-result family tests.",
    )


def build_evidence() -> tuple[ObligationFamilyEvidence, ...]:
    rows: list[ObligationFamilyEvidence] = []
    for member in MEMBERS:
        for mechanism in MECHANISMS:
            rows.append(_evidence(member, mechanism, command=_command_for(member, mechanism)))
    rows.append(
        _evidence(
            "research",
            "full_durable_envelope_event_fold",
            evidence_id=f"{FAMILY_ID}.research.observed_regression",
            command=(
                "python -m unittest "
                "tests.router_runtime.packet_result_family.PacketResultFamilyRuntimeTests."
                "test_research_full_batch_reconciles_from_durable_results_without_manual_event"
            ),
            summary="Observed research durable-join miss is covered as a current regression.",
        )
    )
    return tuple(rows)


def build_bad_case_seed() -> FamilyBadCaseSeed:
    return FamilyBadCaseSeed(
        seed_id="research_joined_without_return_event",
        family_id=FAMILY_ID,
        source_member_id="research",
        mechanism_id="full_durable_envelope_event_fold",
        failure_mode="durable_result_joined_but_router_event_absent",
        description=(
            "A research packet batch had durable joined results, but Router "
            "did not fold them into worker_research_report_returned before "
            "waiting/reminding."
        ),
        source_case_id="openspec.reconcile-research-batch-results",
        metadata={"observed_date": "2026-05-28"},
    )


def build_scan_candidates() -> tuple[AnalogousDefectCandidate, ...]:
    seed = build_bad_case_seed()
    return tuple(
        AnalogousDefectCandidate(
            candidate_id=f"{seed.seed_id}:{member}:{seed.mechanism_id}:scan",
            family_id=FAMILY_ID,
            member_id=member,
            mechanism_id=seed.mechanism_id,
            failure_mode=seed.failure_mode,
            radius="must_scan",
            description=f"{member} sibling scan for durable-envelope event fold.",
            disposition="covered_current",
            disposition_reason="Covered by the packet-result family runtime suite and parity evidence.",
            evidence_ids=(f"{FAMILY_ID}.{member}.{seed.mechanism_id}",),
            source="explicit_sibling_review",
        )
        for member in MEMBERS
        if member != seed.source_member_id
    )


def _known_bad_cases(family: ObligationFamily) -> list[dict[str, Any]]:
    evidence = list(build_evidence())
    missing_current_node = [
        row
        for row in evidence
        if not (
            row.member_id == "current_node"
            and row.mechanism_id == "full_durable_envelope_event_fold"
        )
    ]
    stale_research = [
        (
            _evidence(
                row.member_id,
                row.mechanism_id,
                evidence_id=row.evidence_id,
                command=row.command,
                provenance=row.provenance,
                current=False,
                result_status=row.result_status,
                summary=row.summary,
            )
            if row.member_id == "research"
            and row.mechanism_id == "full_durable_envelope_event_fold"
            else row
        )
        for row in evidence
    ]
    wrong_provenance = [
        (
            _evidence(
                row.member_id,
                row.mechanism_id,
                evidence_id=row.evidence_id,
                command=row.command,
                provenance="internal_note",
                current=row.current,
                result_status=row.result_status,
                summary=row.summary,
            )
            if row.member_id == "pm_role_work"
            and row.mechanism_id == "wrong_recipient_rejection"
            else row
        )
        for row in evidence
    ]
    return [
        {
            "name": "missing_sibling_mechanism_evidence",
            "report": review_obligation_family_parity((family,), missing_current_node),
            "expected_codes": {"missing_family_member_mechanism_evidence"},
        },
        {
            "name": "stale_sibling_mechanism_evidence",
            "report": review_obligation_family_parity((family,), stale_research),
            "expected_codes": {"stale_family_evidence"},
        },
        {
            "name": "wrong_family_evidence_provenance",
            "report": review_obligation_family_parity((family,), wrong_provenance),
            "expected_codes": {"invalid_family_evidence_provenance"},
        },
    ]


def _known_bad_report(case: dict[str, Any]) -> dict[str, Any]:
    report = case["report"]
    finding_codes = sorted({finding.code for finding in report.findings})
    expected = set(case["expected_codes"])
    return {
        "name": case["name"],
        "ok": (not report.ok) and expected.issubset(finding_codes),
        "expected_codes": sorted(expected),
        "finding_codes": finding_codes,
        "report": report.to_dict(),
    }


def build_report() -> dict[str, Any]:
    family = build_family()
    evidence = build_evidence()
    seed = build_bad_case_seed()
    parity_report = review_obligation_family_parity((family,), evidence, (seed,))
    scan_report = review_analogous_defect_scan((family,), seed, build_scan_candidates())
    unreviewed_scan = review_analogous_defect_scan((family,), seed)
    known_bad = [_known_bad_report(case) for case in _known_bad_cases(family)]
    analogous_known_bad = {
        "name": "unreviewed_analogous_sibling_candidates",
        "ok": (not unreviewed_scan.ok)
        and "unreviewed_analogous_defect_candidate" in {finding.code for finding in unreviewed_scan.findings},
        "expected_codes": ["unreviewed_analogous_defect_candidate"],
        "finding_codes": sorted({finding.code for finding in unreviewed_scan.findings}),
        "report": unreviewed_scan.to_dict(),
    }
    known_bad.append(analogous_known_bad)
    return {
        "ok": parity_report.ok and scan_report.ok and all(case["ok"] for case in known_bad),
        "result_type": "flowpilot_packet_result_family_parity",
        "family_id": FAMILY_ID,
        "members": list(MEMBERS),
        "required_mechanisms": list(MECHANISMS),
        "model_command": MODEL_COMMAND,
        "runtime_command": RUNTIME_COMMAND,
        "parity_ok": parity_report.ok,
        "analogous_scan_ok": scan_report.ok,
        "known_bad_ok": all(case["ok"] for case in known_bad),
        "parity_report": parity_report.to_dict(),
        "analogous_scan_report": scan_report.to_dict(),
        "known_bad_cases": known_bad,
        "family": family.to_dict(),
        "evidence": [row.to_dict() for row in evidence],
    }


def compact_status(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": bool(report.get("ok")),
        "family_id": report.get("family_id"),
        "parity_ok": bool(report.get("parity_ok")),
        "analogous_scan_ok": bool(report.get("analogous_scan_ok")),
        "known_bad_ok": bool(report.get("known_bad_ok")),
        "members": report.get("members"),
        "required_mechanisms": report.get("required_mechanisms"),
    }
