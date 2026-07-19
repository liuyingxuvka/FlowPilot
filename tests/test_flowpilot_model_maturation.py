from __future__ import annotations

from flowguard import MODEL_MATURATION_DECISION_CURRENT

from simulations import flowpilot_model_maturation_model as model


def test_known_bad_maturation_cases_require_actions() -> None:
    reports = [model.known_bad_report(case) for case in model.known_bad_cases()]

    assert reports
    assert all(report["ok"] for report in reports)
    assert {
        "ack_only_closure",
        "undisposed_replacement_packet",
        "prompt_contract_gap",
        "stale_evidence",
        "oversized_parent_masks_child_gap",
        "progress_only_background_evidence",
        "singleton_duplicate_authority_gap",
        "unified_repair_conformance_open",
    } == {str(report["name"]) for report in reports}


def test_current_plan_has_named_flowpilot_maturation_signals() -> None:
    signals = model.current_signals()

    assert len(signals) >= 11
    assert {signal.signal_id for signal in signals} >= {
        "maturation_gate_registered",
        "ack_settlement_vs_output_completion",
        "route_replacement_disposes_old_packets",
        "prompt_assets_are_contract_inputs",
        "background_evidence_final_artifact_bound",
        "singleton_identity_authority_current",
        "unified_repair_runtime_test_conformance_current",
    }


def test_unified_repair_maturation_gate_stays_red_until_native_conformance() -> None:
    gate = next(
        gate
        for gate in model.evidence_gates()
        if gate.signal_id == "unified_repair_runtime_test_conformance_current"
    )
    signal = model._gate_signal(gate)
    contract = signal.metadata["unified_repair_contract"]

    assert gate.require_unified_repair_conformance
    assert not signal.resolved
    assert not contract["ok"]
    assert "unified_conformance_not_green" in contract["findings"]
    assert "unified_required_conformance_skipped" in contract["findings"]
    assert not contract["native_owner_receipt_synthesized"]

    report = model.build_report()
    assert not report["ok"]
    assert report["decision"] == "current_runtime_gap"
    assert report["blocking_signal_ids"] == [
        "unified_repair_runtime_test_conformance_current"
    ]


def test_current_report_shape_is_flowguard_maturation_report() -> None:
    payload = model.current_report_dict()

    assert payload["decision"] in {
        MODEL_MATURATION_DECISION_CURRENT,
        "model_maturation_scoped_claim",
        "model_maturation_upgrade_required",
        "model_maturation_blocked",
    }
    assert payload["signal_count"] >= 11
    assert isinstance(payload["recommended_actions"], list)
