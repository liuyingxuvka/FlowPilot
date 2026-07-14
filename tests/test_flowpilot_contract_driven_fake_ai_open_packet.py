from __future__ import annotations

from copy import deepcopy
import importlib
from pathlib import Path
import sys
import tempfile
import unittest

from simulations import flowpilot_contract_driven_fake_ai as fake_ai
from skills.flowpilot.assets.flowpilot_core_runtime import packet_result_contracts


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "skills" / "flowpilot" / "assets"
if str(ASSETS) not in sys.path:
    sys.path.insert(0, str(ASSETS))

flowpilot_new = importlib.import_module("flowpilot_new")


def _open_packet_result(*, family_id: str = "review.any_current_subject") -> dict[str, object]:
    effective = packet_result_contracts.effective_result_contract_for_family(family_id)
    report_contract = {
        "output_contract": {"contract_family_id": family_id},
        "result_contract_profile_ids": list(effective["result_contract_profile_ids"]),
        "result_contract_profile_bindings": deepcopy(effective["result_contract_profile_bindings"]),
        "required_result_body_fields": list(effective["required_fields"]),
        "required_child_fields": list(effective["required_child_fields"]),
        "explicit_array_fields": list(effective["explicit_array_fields"]),
        "non_empty_array_fields": list(effective["non_empty_array_fields"]),
        "allowed_value_options": deepcopy(effective["allowed_value_options"]),
        "field_type_requirements": deepcopy(effective["field_type_requirements"]),
        "forbidden_fields": list(effective["forbidden_fields"]),
        "forbidden_aliases": deepcopy(effective["forbidden_aliases"]),
        "minimal_valid_shape": deepcopy(effective["minimal_valid_shape"]),
        "branch_valid_shapes": deepcopy(effective["branch_valid_shapes"]),
        "stage_evidence_matrix": {},
        "validator": str(effective["validator"]),
    }
    review_window = {
        "schema_version": "flowpilot.review_window.v1",
        "review_flow_id": "runtime-delivered-custom-review-flow",
        "review_window_coverage_status": "declared",
        "subject_lifecycle_stage": "current_stage",
        "required_authorized_result_read_ids_before_submit": ["result-required-001"],
        "review_depth_rule": (
            "Fixed Reviewer stage card: reviewer.runtime-delivered. "
            "Stage focus: the actual current artifact. "
            "Independently challenge the weakest evidence and a failure hypothesis. "
            "Also challenge core deliverable non-downgrade."
        ),
    }
    handoff = {
        "schema_version": fake_ai.CURRENT_HANDOFF_CONTRACT_SCHEMA_VERSION,
        "contract_id": fake_ai.CURRENT_HANDOFF_CONTRACT_SCHEMA_VERSION,
        "packet_id": "packet-current-001",
        "packet_kind": "review",
        "route_scope": "node_result_review",
        "recipient_responsibility": "reviewer",
        "contract_family_id": family_id,
        "current_run_only": True,
        "route_version": 7,
        "source_generation": 11,
        "required_report_contract": report_contract,
        "input_material_manifest": {
            "authorized_result_read_ids": ["result-required-001"],
            "required_authorized_reads_before_submit": ["result-required-001"],
            "required_authorized_read_count": 1,
            "all_required_authorized_result_bodies_must_be_opened_before_submit": True,
        },
        "review_window": review_window,
    }
    checklist = {
        "schema_version": fake_ai.SUBMISSION_CHECKLIST_SCHEMA_VERSION,
        "source": "current_handoff_contract",
        "run_id": "run-current-001",
        "packet_id": "packet-current-001",
        "lease_id": "lease-current-001",
        "route_version": 7,
        "source_generation": 11,
        "contract_family_id": family_id,
        "current_packet_body_inspected": False,
        "current_handoff_contract_inspected": True,
        "required_result_body_fields": deepcopy(report_contract["required_result_body_fields"]),
        "required_child_fields": deepcopy(report_contract["required_child_fields"]),
        "explicit_array_fields": deepcopy(report_contract["explicit_array_fields"]),
        "non_empty_array_fields": deepcopy(report_contract["non_empty_array_fields"]),
        "allowed_value_options": deepcopy(report_contract["allowed_value_options"]),
        "field_type_requirements": deepcopy(report_contract["field_type_requirements"]),
        "forbidden_fields": deepcopy(report_contract["forbidden_fields"]),
        "forbidden_aliases": deepcopy(report_contract["forbidden_aliases"]),
        "result_skeleton": deepcopy(report_contract["minimal_valid_shape"]),
        "branch_valid_shapes": deepcopy(report_contract["branch_valid_shapes"]),
        "input_material_manifest": deepcopy(handoff["input_material_manifest"]),
        "authorized_input_materials_count": 1,
        "required_authorized_input_materials_count": 1,
        "authorized_result_read_ids": ["result-required-001"],
        "required_authorized_result_read_ids": ["result-required-001"],
        "required_authorized_read_count": 1,
        "all_required_authorized_result_bodies_must_be_opened_before_submit": True,
    }
    checklist["contract_fingerprint"] = fake_ai._fingerprint_for_payload(
        fake_ai._fingerprint_payload(
            run_id="run-current-001",
            packet_id="packet-current-001",
            lease_id="lease-current-001",
            route_version=7,
            source_generation=11,
            contract_family_id=family_id,
            required_report_contract=report_contract,
            review_window=review_window,
        )
    )
    return {
        "ok": True,
        "schema_version": fake_ai.OPEN_PACKET_RESULT_SCHEMA_VERSION,
        "run_id": "run-current-001",
        "packet": {
            "packet_id": "packet-current-001",
            "packet_kind": "review",
            "responsibility": "reviewer",
            "route_version": 7,
            "body_hash": "body-hash-current-001",
            "current_handoff_contract": handoff,
        },
        "lease": {
            "lease_id": "lease-current-001",
            "responsibility": "reviewer",
            "ack_received": True,
        },
        "sealed_packet_body": (
            '{"current_handoff_contract":{"schema_version":"obsolete"},'
            '"minimal_valid_shape":{"decision":"body-bypass"}}'
        ),
        "authorized_input_materials": [
            {"result_id": "result-required-001", "required_before_submit": True}
        ],
        "authorized_input_materials_delivered": True,
        "submission_checklist": checklist,
        "open_receipt": {
            "event_type": "sealed_packet_body_opened",
            "packet_id": "packet-current-001",
            "lease_id": "lease-current-001",
            "body_hash": "body-hash-current-001",
        },
    }


class ContractDrivenFakeAIOpenPacketTests(unittest.TestCase):
    def test_real_public_open_packet_result_passes_strict_consumer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            started = flowpilot_new.start_run(
                root,
                run_id="run-real-open-responder",
                headless_startup_text="Exercise strict fake AI open-packet consumption.",
                require_formal_ui=False,
            )
            next_action = started["next_action"]
            packet_id = str(next_action["subject_id"])
            responsibility = str(next_action["responsibility"])
            dispatched = flowpilot_new.dispatch_current_role(
                root,
                packet_id=packet_id,
                responsibility=responsibility,
                host_kind="fake",
                agent_id="strict-open-responder-agent",
            )
            self.assertTrue(dispatched["ok"], dispatched)
            lease_id = str(dispatched["lease_id"])
            flowpilot_new.ack(root, lease_id=lease_id, packet_id=packet_id)
            opened = flowpilot_new.open_packet(
                root,
                lease_id=lease_id,
                packet_id=packet_id,
            )

            responder = fake_ai.ContractDrivenFakeAIResponder.from_open_packet_result(opened)

            self.assertEqual(responder.open_packet_identity["run_id"], "run-real-open-responder")
            self.assertEqual(responder.open_packet_identity["packet_id"], packet_id)
            self.assertEqual(responder.open_packet_identity["lease_id"], lease_id)
            self.assertEqual(
                responder.forbidden_fields,
                opened["submission_checklist"]["forbidden_fields"],
            )

    def test_strict_open_result_is_the_only_runtime_contract_authority(self) -> None:
        opened = _open_packet_result()
        responder = fake_ai.ContractDrivenFakeAIResponder.from_open_packet_result(opened)

        expected_forbidden = opened["submission_checklist"]["forbidden_fields"]
        self.assertTrue(expected_forbidden)
        self.assertEqual(responder.forbidden_fields, expected_forbidden)
        self.assertNotEqual(responder.legal_payload().get("decision"), "body-bypass")
        self.assertFalse(hasattr(fake_ai.ContractDrivenFakeAIResponder, "from_packet"))
        self.assertFalse(hasattr(fake_ai.ContractDrivenFakeAIResponder, "from_reissue_body"))

    def test_identity_route_generation_and_projection_mismatches_fail_closed(self) -> None:
        mutations = {
            "run": lambda row: row["submission_checklist"].__setitem__("run_id", "run-stale"),
            "packet": lambda row: row["submission_checklist"].__setitem__("packet_id", "packet-stale"),
            "lease": lambda row: row["submission_checklist"].__setitem__("lease_id", "lease-stale"),
            "route": lambda row: row["submission_checklist"].__setitem__("route_version", 6),
            "generation": lambda row: row["submission_checklist"].__setitem__("source_generation", 10),
            "forbidden_projection": lambda row: row["submission_checklist"].__setitem__("forbidden_fields", []),
            "alias_projection": lambda row: row["submission_checklist"].__setitem__(
                "forbidden_aliases", {"legacy_alias": "decision"}
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                opened = _open_packet_result()
                mutate(opened)
                with self.assertRaises(ValueError):
                    fake_ai.ContractDrivenFakeAIResponder.from_open_packet_result(opened)

    def test_fingerprint_covers_the_delivered_review_depth_rule(self) -> None:
        opened = _open_packet_result()
        opened["packet"]["current_handoff_contract"]["review_window"]["review_depth_rule"] += " Tampered."
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            fake_ai.ContractDrivenFakeAIResponder.from_open_packet_result(opened)

    def test_reviewer_consumes_delivered_rule_without_static_flow_lookup(self) -> None:
        opened = _open_packet_result()
        delivered_rule = opened["packet"]["current_handoff_contract"]["review_window"]["review_depth_rule"]
        responder = fake_ai.ContractDrivenFakeAIResponder.from_open_packet_result(opened)

        payload = responder.review_window_behavior_payload(
            "reviewer_stage_specific_challenge_pass"
        )

        self.assertEqual(
            payload["review_window_trace"]["review_depth_rule_consumed"],
            delivered_rule,
        )
        self.assertEqual(
            payload["review_window_trace"]["review_flow_id"],
            "runtime-delivered-custom-review-flow",
        )

    def test_missing_or_incomplete_review_depth_rule_is_rejected(self) -> None:
        for replacement in (None, "", "generic review"):
            with self.subTest(replacement=replacement):
                opened = _open_packet_result()
                window = opened["packet"]["current_handoff_contract"]["review_window"]
                if replacement is None:
                    window.pop("review_depth_rule")
                else:
                    window["review_depth_rule"] = replacement
                with self.assertRaises(ValueError):
                    fake_ai.ContractDrivenFakeAIResponder.from_open_packet_result(opened)

    def test_unknown_contract_family_is_rejected(self) -> None:
        opened = _open_packet_result()
        opened["packet"]["current_handoff_contract"]["contract_family_id"] = "unknown.family"
        opened["submission_checklist"]["contract_family_id"] = "unknown.family"
        with self.assertRaisesRegex(ValueError, "unknown current contract family"):
            fake_ai.ContractDrivenFakeAIResponder.from_open_packet_result(opened)

    def test_unacked_or_unbound_open_receipt_is_rejected(self) -> None:
        opened = _open_packet_result()
        opened["lease"]["ack_received"] = False
        with self.assertRaisesRegex(ValueError, "ACKed"):
            fake_ai.ContractDrivenFakeAIResponder.from_open_packet_result(opened)

        opened = _open_packet_result()
        opened["open_receipt"]["lease_id"] = "lease-other"
        with self.assertRaisesRegex(ValueError, "open_receipt"):
            fake_ai.ContractDrivenFakeAIResponder.from_open_packet_result(opened)


if __name__ == "__main__":
    unittest.main()
