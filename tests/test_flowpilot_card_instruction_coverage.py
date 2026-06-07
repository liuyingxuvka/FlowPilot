from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_KIT = ROOT / "skills" / "flowpilot" / "assets" / "runtime_kit"
sys.path.insert(0, str(ROOT / "simulations"))

import card_instruction_coverage_model as model  # noqa: E402


def _runtime_manifest_cards() -> list[dict[str, object]]:
    manifest = json.loads((RUNTIME_KIT / "manifest.json").read_text(encoding="utf-8"))
    return [card for card in manifest.get("cards", []) if isinstance(card, dict)]


def _card_path_by_id(card_id: str) -> Path:
    for card in _runtime_manifest_cards():
        if card.get("id") == card_id:
            return RUNTIME_KIT / str(card["path"])
    raise AssertionError(f"runtime kit manifest is missing card id {card_id!r}")


def _card_paths_by_id(*card_ids: str) -> list[Path]:
    return [_card_path_by_id(card_id) for card_id in card_ids]


def _card_paths_for_audience(audience: str, *, kind: str | None = None) -> list[Path]:
    paths: list[Path] = []
    for card in _runtime_manifest_cards():
        if card.get("audience") != audience:
            continue
        if kind is not None and card.get("kind") != kind:
            continue
        paths.append(RUNTIME_KIT / str(card["path"]))
    return paths


class FlowPilotCardInstructionCoverageTests(unittest.TestCase):
    def test_actual_runtime_cards_have_router_return_instruction_coverage(self) -> None:
        cards = model.collect_card_facts(ROOT)
        router_facts = model.collect_router_facts(ROOT)
        packet_prompts = model.collect_packet_prompt_facts(ROOT)
        state = model.State()
        steps = 0

        while state.status == "checking":
            transitions = tuple(model.next_safe_states(state, cards, router_facts, packet_prompts))
            self.assertEqual(len(transitions), 1)
            state = transitions[0].state
            steps += 1
            self.assertLessEqual(steps, len(cards) + 2)

        self.assertEqual(state.status, "complete", state.failures)
        self.assertEqual(len(state.checked), len(cards))
        self.assertFalse(model.invariant_failures(state))

    def test_hazard_cards_are_rejected(self) -> None:
        for name, card in model.hazard_cards().items():
            with self.subTest(name=name):
                self.assertTrue(model.card_failures(card))

    def test_hazard_packet_prompts_are_rejected(self) -> None:
        for name, packet_prompts in model.hazard_packet_prompts().items():
            with self.subTest(name=name):
                self.assertTrue(model.packet_prompt_failures(packet_prompts))

    def test_controller_aside_guidance_is_repeated_on_runtime_surfaces(self) -> None:
        guidance_paths = [
            RUNTIME_KIT / "prompts" / "packets" / "packet_identity_boundary.md",
            RUNTIME_KIT / "prompts" / "packets" / "result_identity_boundary.md",
            RUNTIME_KIT / "prompts" / "packets" / "output_contract_section.md",
            RUNTIME_KIT / "prompts" / "cards" / "required_return_policy.md",
            ROOT / "templates" / "flowpilot" / "packets" / "packet_body.template.md",
            ROOT / "templates" / "flowpilot" / "packets" / "result_body.template.md",
        ]
        for path in guidance_paths:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8").lower()
                self.assertIn("controller_aside", text)
                self.assertIn("process/status", text)
                self.assertIn("not", text)
                self.assertIn("evidence", text)
                self.assertIn("runtime", text)
                self.assertIn("event", text)

    def test_current_prompt_surfaces_reject_obsolete_runtime_paths(self) -> None:
        self.assertFalse(model.forbidden_current_prompt_surface_errors(ROOT))

    def test_current_reference_surfaces_reject_obsolete_startup_and_role_paths(self) -> None:
        self.assertFalse(model.forbidden_current_reference_surface_errors(ROOT))

    def test_current_packet_rows_use_lease_ack_result_authority(self) -> None:
        action_table = (RUNTIME_KIT / "prompts" / "controller" / "action_ledger_table.md").read_text(encoding="utf-8").lower()
        controller_card = _card_path_by_id("controller.core").read_text(encoding="utf-8").lower()
        for text in (action_table, controller_card):
            obsolete_relay = "flowpilot_" + "runtime.py relay-envelope"
            self.assertNotIn(obsolete_relay, text)
            self.assertNotIn("controller_relay", text)
            self.assertNotIn("flowpilot_new.py resolve-role-assignment", text)
            self.assertNotIn("flowpilot_new.py lease-agent", text)
            self.assertIn("flowpilot_new.py dispatch-current-role", text)
            self.assertIn("flowpilot_new.py role-handoff", text)
            self.assertIn("flowpilot_new.py ack", text)
            self.assertIn("flowpilot_new.py open-packet", text)
            self.assertIn("flowpilot_new.py submit-result", text)

    def test_controller_progress_fraction_guidance_is_runtime_owned(self) -> None:
        guidance_texts = [
            _card_path_by_id("controller.core").read_text(encoding="utf-8").lower(),
            _card_path_by_id("controller.resume_reentry").read_text(encoding="utf-8").lower(),
            (RUNTIME_KIT / "prompts" / "controller" / "action_ledger_table.md").read_text(encoding="utf-8").lower(),
            (ROOT / "skills" / "flowpilot" / "SKILL.md").read_text(encoding="utf-8").lower(),
        ]
        for text in guidance_texts:
            with self.subTest():
                self.assertIn("progress_fraction.display", text)
                self.assertIn("current expanded node fraction", text)
                self.assertIn("do not calculate", text)
                self.assertIn("percent", text)
                self.assertIn("sealed", text)
                self.assertIn("do not invent", text)
                self.assertIn("authority", text)

    def test_role_surface_preference_is_present_on_lease_surface(self) -> None:
        text = (ROOT / "skills" / "flowpilot" / "SKILL.md").read_text(encoding="utf-8").lower()
        self.assertIn("prefer durable, addressable role surfaces", text)
        self.assertIn("parallel-count", text)
        self.assertIn("model-capability limits", text)
        self.assertIn("when such surfaces are available", text)

    def test_pm_worker_packet_cards_carry_lightweight_dispatch_guidance(self) -> None:
        worker_packet_cards = _card_paths_by_id(
            "pm.material_scan",
            "pm.current_node_loop",
            "pm.research_package",
        )
        for path in worker_packet_cards:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertIn("Before assigning a worker packet, consider worker balance and packet shape.", text)
                self.assertIn("worker opportunities roughly balanced across the current run", text)
                self.assertIn("bounded separate packets for", text)
                self.assertIn("without overlapping files", text)
                self.assertIn("evidence duties, or review ownership", text)
                lowered = text.lower()
                self.assertNotIn("default `worker`", lowered)
                self.assertNotIn("default worker", lowered)
                self.assertNotIn("do not default", lowered)

    def test_worker_and_flowguard_operator_packets_carry_soft_pm_note_guidance(self) -> None:
        guidance_paths = [
            *_card_paths_by_id(
                "pm.material_scan",
                "pm.current_node_loop",
                "pm.research_package",
                "pm.flowguard_operator_request_report_loop",
                "worker.core",
                "worker.research_report",
                "flowguard_operator.core",
            ),
            ROOT / "templates/flowpilot/packets/packet_body.template.md",
            ROOT / "templates/flowpilot/packets/result_body.template.md",
        ]
        for path in guidance_paths:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                lowered = text.lower()
                self.assertIn("pm note", lowered)
                self.assertIn("in-scope quality choice", lowered)
                self.assertIn("pm consideration", lowered)
                self.assertIn("decision-support", lowered)

        reviewer_card = (
            _card_path_by_id("reviewer.worker_result_review")
        ).read_text(encoding="utf-8").lower()
        self.assertNotIn("pm note", reviewer_card)

        contract_text = (
            ROOT / "skills/flowpilot/assets/runtime_kit/contracts/contract_index.json"
        ).read_text(encoding="utf-8").lower()
        self.assertNotIn("pm note", contract_text)

        repair_cards = _card_paths_by_id("pm.review_repair", "pm.event.reviewer_blocked")
        for path in repair_cards:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertIn("same worker who produced the blocked result", text)
                self.assertIn("repair keeps local context", text)
                self.assertIn("fundamental", text)
                self.assertIn("separable new work", text)

    def test_role_scoped_quality_repair_prompt_boundaries(self) -> None:
        def normalized(path: Path) -> str:
            return " ".join(path.read_text(encoding="utf-8").lower().split())

        packet_template = normalized(ROOT / "templates/flowpilot/packets/packet_body.template.md")
        self.assertIn("role-scoped quality repair boundary", packet_template)
        self.assertIn("allowed reads, allowed writes, acceptance slice, role authority, and verification requirements", packet_template)
        self.assertIn("do not silently repair it", packet_template)
        self.assertIn("correct defects in your own report, model, check command", packet_template)
        self.assertIn("do not repair the artifact under review", packet_template)

        executable_worker_prompts = _card_paths_by_id(
            "pm.current_node_loop",
            "pm.review_repair",
            "pm.role_work_request",
            "worker.core",
        )
        for path in executable_worker_prompts:
            with self.subTest(path=path.name):
                text = normalized(path)
                self.assertIn("role-scoped quality repair boundary", text)
                self.assertIn("allowed reads", text)
                self.assertIn("allowed writes", text)
                self.assertIn("acceptance slice", text)
                self.assertIn("role authority", text)
                self.assertIn("rerun", text)
                self.assertIn("blocked", text)
                self.assertIn("needs_pm", text)
                self.assertIn("pm suggestion item", text)

        evidence_prompts = _card_paths_by_id(
            "pm.material_scan",
            "pm.research_package",
            "worker.research_report",
        )
        for path in evidence_prompts:
            with self.subTest(path=path.name):
                text = normalized(path)
                self.assertIn("role-scoped quality repair boundary", text)
                self.assertIn("correct defects", text)
                self.assertIn("own report", text)
                self.assertIn("must not repair target implementation", text)
                self.assertIn("pm suggestion items", text)

        flowguard_operator_prompts = _card_paths_by_id(
            "pm.flowguard_operator_request_report_loop",
            "flowguard_operator.core",
        )
        for path in flowguard_operator_prompts:
            with self.subTest(path=path.name):
                text = normalized(path)
                self.assertIn("role-scoped quality repair boundary", text)
                self.assertIn("correct defects", text)
                self.assertIn("own model", text)
                self.assertIn("formal findings", text)
                self.assertIn("pm suggestion items", text)

        reviewer_prompts = _card_paths_by_id("reviewer.core", "reviewer.worker_result_review")
        for path in reviewer_prompts:
            with self.subTest(path=path.name):
                text = normalized(path)
                self.assertIn("role-scoped quality repair boundary", text)
                self.assertIn("anti-repair", text)
                self.assertIn("do not repair", text)
                self.assertNotIn("fix in-scope defects", text)

    def test_pm_suggestion_disposition_guidance_is_unified_but_role_scoped(self) -> None:
        pm_card = (
            _card_path_by_id("pm.core")
        ).read_text(encoding="utf-8").lower()
        for required in (
            "pm_suggestion_ledger.jsonl",
            "flowpilot.pm_suggestion_item.v1",
            "current_gate_blocker",
            "defer_to_named_node",
            "reject_with_reason",
            "waive_with_authority",
            "impact triage",
            "smallest sufficient process/product",
            "flowguard modeling path",
            "no pending dispositions",
        ):
            self.assertIn(required, pm_card)

        suggestion_template = json.loads(
            (
                ROOT / "templates/flowpilot/pm_suggestion_ledger_entry.template.json"
            ).read_text(encoding="utf-8")
        )
        self.assertIn("impact_triage", suggestion_template)
        self.assertIn("impact_level", suggestion_template["impact_triage"])
        self.assertIn("flowguard_considered", suggestion_template["impact_triage"])
        self.assertIn("flowguard_decision", suggestion_template["impact_triage"])

        worker_cards = _card_paths_by_id(
            "worker.core",
            "worker.research_report",
        )
        for path in worker_cards:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8").lower()
                self.assertIn("pm suggestion items", text)
                self.assertIn("flowpilot.pm_suggestion_item.v1", text)
                self.assertIn("advisory only", text)
                self.assertIn("must not use `current_gate_blocker`", text)

        flowguard_operator_cards = _card_paths_by_id("flowguard_operator.core")
        for path in flowguard_operator_cards:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8").lower()
                self.assertIn("pm suggestion items", text)
                self.assertIn("formal model-gate", text)
                self.assertIn("current_gate_blocker", text)

        for path in _card_paths_for_audience("human_like_reviewer", kind="reviewer_gate"):
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8").lower()
                self.assertIn("flowpilot.pm_suggestion_item.v1", text)
                self.assertIn("minimum standard", text)

        packet_template = (
            ROOT / "templates/flowpilot/packets/packet_body.template.md"
        ).read_text(encoding="utf-8").lower()
        result_template = (
            ROOT / "templates/flowpilot/packets/result_body.template.md"
        ).read_text(encoding="utf-8").lower()
        contract_text = (
            ROOT / "skills/flowpilot/assets/runtime_kit/contracts/contract_index.json"
        ).read_text(encoding="utf-8").lower()
        for text in (packet_template, result_template, contract_text):
            self.assertIn("pm suggestion", text)
            self.assertIn("pm_suggestion", text)

    def test_flowguard_work_order_protocol_reaches_core_cards(self) -> None:
        prompt_policy = (
            RUNTIME_KIT / "prompts" / "cards" / "flowguard_work_order_policy.md"
        ).read_text(encoding="utf-8")
        self.assertIn("FlowGuard Work Order", prompt_policy)
        self.assertIn("FlowGuard Report", prompt_policy)
        self.assertIn("flowguard_work_order_id", prompt_policy)
        self.assertIn("flowguard_report_id", prompt_policy)
        self.assertIn("progress-only", prompt_policy)

        manifest = json.loads((RUNTIME_KIT / "prompts" / "manifest.json").read_text(encoding="utf-8"))
        prompt_ids = {entry.get("id") for entry in manifest.get("prompts", []) if isinstance(entry, dict)}
        self.assertIn("cards.flowguard_work_order_policy", prompt_ids)

        required_cards = _card_paths_by_id(
            "startup_banner",
            "controller.core",
            "controller.resume_reentry",
            "controller.break_glass_repair",
            "pm.core",
            "pm.product_architecture",
            "pm.child_skill_selection",
            "pm.child_skill_gate_manifest",
            "pm.route_skeleton",
            "pm.node_acceptance_plan",
            "pm.flowguard_operator_request_report_loop",
            "pm.current_node_loop",
            "pm.role_work_request",
            "pm.review_repair",
            "pm.final_ledger",
            "pm.closure",
            "pm.resume_decision",
            "flowguard_operator.core",
            "reviewer.core",
            "reviewer.worker_result_review",
            "reviewer.strict_gate_obligation_review",
            "reviewer.final_backward_replay",
            "worker.core",
            "worker.research_report",
            "pm.event.node_started",
            "pm.event.reviewer_report",
            "pm.event.reviewer_blocked",
        )
        for path in required_cards:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertIn("FlowGuard", text)
                self.assertTrue(
                    "flowguard_work_order_id" in text or "FlowGuard Work Order" in text,
                    f"{path} lacks work-order traceability",
                )
                self.assertTrue(
                    "flowguard_report_id" in text or "FlowGuard Report" in text,
                    f"{path} lacks report traceability",
                )

    def test_flowguard_work_order_language_preserves_role_authority(self) -> None:
        controller_text = " ".join(_card_path_by_id("controller.core").read_text(encoding="utf-8").lower().split())
        self.assertIn("controller is status-only", controller_text)
        self.assertIn("do not interpret flowguard reports", controller_text)
        self.assertIn("approve gates", controller_text)
        self.assertIn("mutate routes", controller_text)
        self.assertIn("read sealed flowguard report bodies", controller_text)

        for card_id in ("flowguard_operator.core",):
            text = " ".join(_card_path_by_id(card_id).read_text(encoding="utf-8").lower().split())
            with self.subTest(card_id=card_id):
                self.assertIn("your flowguard report supports pm and reviewer decisions", text)
                self.assertIn("does not approve gates", text)
                self.assertIn("mutate routes", text)
                self.assertIn("close nodes", text)

        for card_id in ("worker.core", "worker.research_report"):
            text = " ".join(_card_path_by_id(card_id).read_text(encoding="utf-8").lower().split())
            with self.subTest(card_id=card_id):
                self.assertIn("flowguard obligation coverage", text)
                self.assertIn("packet-scoped", text)
                self.assertTrue(
                    "does not approve gates" in text or "do not approve gates" in text
                )
                self.assertIn("mutate routes", text)
                self.assertIn("replace pm", text)

        reviewer_text = " ".join(_card_path_by_id("reviewer.core").read_text(encoding="utf-8").lower().split())
        self.assertIn("you do not have to rerun all flowguard modeling", reviewer_text)
        self.assertIn("unless pm routes that work", reviewer_text)
        self.assertIn("default to inspecting existing run outputs", reviewer_text)
        self.assertIn("rerun only targeted scripts or checks", reviewer_text)
        self.assertIn("whether the cited flowguard evidence can support this gate", reviewer_text)

    def test_reviewer_formal_package_reuses_existing_acceptance_sources(self) -> None:
        def normalized(path: Path) -> str:
            return " ".join(path.read_text(encoding="utf-8").lower().split())

        reviewer_core = normalized(_card_path_by_id("reviewer.core"))
        worker_review = normalized(_card_path_by_id("reviewer.worker_result_review"))

        for text in (reviewer_core, worker_review):
            self.assertIn("acceptance-standard schema", text)
            self.assertIn("gate_kind", text)
            self.assertIn("reviewer_review_scope", text)
            self.assertIn("acceptance slice", text)
            self.assertIn("output_contract", text)
            self.assertIn("contract self-check", text)
            self.assertIn("node_acceptance_plan", text)
            self.assertIn("blockers", text)
            self.assertIn("recommended_resolution", text)
        self.assertIn("default to inspecting existing run outputs", worker_review)
        self.assertIn("rerun only targeted scripts or checks", worker_review)

    def test_packet_open_success_requires_work_or_existing_exit(self) -> None:
        def normalized(path: Path) -> str:
            return " ".join(path.read_text(encoding="utf-8").lower().split())

        packet_runtime_text = " ".join(
            (
                normalized(ROOT / "skills/flowpilot/assets/packet_runtime.py"),
                normalized(ROOT / "skills/flowpilot/assets/packet_runtime_contracts.py"),
            )
        )
        packet_template = normalized(ROOT / "templates/flowpilot/packets/packet_body.template.md")
        pm_card = normalized(_card_path_by_id("pm.core"))
        pm_startup_intake_card = _card_path_by_id("pm.startup_intake")
        pm_verified_open_cards = _card_paths_by_id("pm.review_repair")
        ordinary_role_cards = _card_paths_by_id(
            "worker.core",
            "worker.research_report",
            "reviewer.core",
            "flowguard_operator.core",
        )

        self.assertIn("successful", packet_runtime_text)
        self.assertIn("current assignment", packet_runtime_text)
        for text in (packet_template, pm_card):
            self.assertIn("successful", text)
            self.assertNotIn("flowpilot_new.py resolve-role-assignment", text)
            self.assertNotIn("flowpilot_new.py lease-agent", text)
            self.assertIn("flowpilot_new.py dispatch-current-role", text)
            self.assertIn("flowpilot_new.py role-handoff", text)
            self.assertIn("flowpilot_new.py ack", text)
            self.assertIn("flowpilot_new.py open-packet", text)
            self.assertIn("flowpilot_new.py submit-result", text)
            self.assertIn("ordinary blocker back to pm", text)
        self.assertIn("current control-blocker repair decision", packet_template)
        self.assertIn("pm_control_blocker_repair_decision", pm_card)

        intake_text = normalized(pm_startup_intake_card)
        self.assertIn("flowpilot_new.py open-packet", intake_text)
        self.assertIn("runtime-generated", intake_text)
        self.assertIn("full `user_intake` body before runtime delivers the current pm mail item", intake_text)
        self.assertIn("ordinary blocker back to pm", intake_text)

        for path in pm_verified_open_cards:
            with self.subTest(path=path.name):
                text = normalized(path)
                self.assertIn("current", text)
                self.assertIn("lease", text)
                self.assertIn("ordinary blocker back to pm", text)

        for path in ordinary_role_cards:
            with self.subTest(path=path.name):
                text = normalized(path)
                self.assertNotIn("flowpilot_new.py resolve-role-assignment", text)
                self.assertNotIn("flowpilot_new.py lease-agent", text)
                self.assertIn("flowpilot_new.py dispatch-current-role", text)
                self.assertIn("flowpilot_new.py ack", text)
                self.assertIn("flowpilot_new.py open-packet", text)
                self.assertIn("flowpilot_new.py submit-result", text)
                self.assertIn("formal blocker", text)
                self.assertIn("pm or router can decide", text)

    def test_flowguard_test_obligation_ownership_guidance_is_role_scoped(self) -> None:
        def normalized(path: Path) -> str:
            return " ".join(path.read_text(encoding="utf-8").lower().split())

        pm_core = normalized(_card_path_by_id("pm.core"))
        for term in (
            "flowguard test obligation ownership",
            "test_obligation_matrix.pre_worker",
            "test_obligation_matrix.post_worker",
            "existing model preflight",
            "developmentprocessflow",
            "model-test alignment",
            "testmesh",
            "worker_test_packet_required",
            "missing_test_kinds",
        ):
            self.assertIn(term, pm_core)
        self.assertIn("do not let `missing_test_kinds` remain only", pm_core)
        self.assertIn("do not become the default authors or maintainers", pm_core)

        pm_node_plan = normalized(_card_path_by_id("pm.node_acceptance_plan"))
        for term in (
            "test_obligation_matrix.pre_worker",
            "test_obligation_matrix.post_worker",
            "required_test_kind",
            "freshness_rule",
            "test obligation coverage",
            "model_test_alignment_required",
            "testmesh_required",
            "undispositioned rows block pm node-completion approval",
        ):
            self.assertIn(term, pm_node_plan)

        flowguard_operator_loop = normalized(_card_path_by_id("pm.flowguard_operator_request_report_loop"))
        for term in (
            "role_skill_use_bindings",
            "flowguard child skill",
            "model-test alignment",
            "testmesh",
            "flowguard operator prose does not close a test gap",
        ):
            self.assertIn(term, flowguard_operator_loop)

        pm_role_work = normalized(_card_path_by_id("pm.role_work_request"))
        for term in (
            "test obligation coverage",
            "test_obligation_matrix",
            "maintain ordinary packet-scoped tests",
            "flowguard operators identify obligations and gaps",
        ):
            self.assertIn(term, pm_role_work)

        worker_cards = _card_paths_by_id("worker.core")
        for path in worker_cards:
            with self.subTest(path=path.name):
                text = normalized(path)
                self.assertIn("test obligation coverage", text)
                self.assertIn("required test kind", text)
                self.assertIn("freshness status", text)
                self.assertIn("testmesh", text)
                self.assertIn("model-test alignment", text)
                self.assertIn("silently expanding scope", text)

        reviewer_cards = _card_paths_by_id(
            "reviewer.worker_result_review",
            "reviewer.strict_gate_obligation_review",
            "reviewer.evidence_quality_review",
        )
        for path in reviewer_cards:
            with self.subTest(path=path.name):
                text = normalized(path)
                self.assertIn("test_obligation_matrix", text)
                self.assertIn("missing", text)
                self.assertIn("stale", text)
                self.assertIn("skipped", text)
                self.assertIn("undispositioned", text)

    def test_current_contract_staged_effect_guidance_is_role_scoped(self) -> None:
        def normalized(path: Path) -> str:
            return " ".join(path.read_text(encoding="utf-8").lower().split())

        pm_core = normalized(_card_path_by_id("pm.core"))
        self.assertIn("current-contract runtime", pm_core)
        self.assertIn("runtime owns the mechanical staged-effect record", pm_core)
        self.assertIn("do not create separate candidate ledgers", pm_core)

        pm_node_plan = normalized(_card_path_by_id("pm.node_acceptance_plan"))
        self.assertIn("top-level `node_context_package`", pm_node_plan)
        self.assertIn("commit_node_acceptance_plan", pm_node_plan)
        self.assertIn("must not claim accepted", pm_node_plan)

        reviewer_node_plan = normalized(_card_path_by_id("reviewer.node_acceptance_plan_review"))
        self.assertIn("runtime owns mechanical validation", reviewer_node_plan)
        self.assertIn("review the real node acceptance plan", reviewer_node_plan)
        self.assertIn("semantically safe to commit", reviewer_node_plan)

        flowguard_core = normalized(_card_path_by_id("flowguard_operator.core"))
        self.assertIn("when the packet includes `staged_effect`", flowguard_core)
        self.assertIn("do not require future committed fields", flowguard_core)
        self.assertIn("process/state/evidence risk review", flowguard_core)

        pm_resume = normalized(_card_path_by_id("pm.resume_decision"))
        self.assertIn("plain lifecycle resume does not clear", pm_resume)
        self.assertIn("resolve-stopped-blocker", pm_resume)
        self.assertIn("--user-requested", pm_resume)
        self.assertIn("ordinary patrol, resume, or chat-history context must not do it automatically", pm_resume)

    def test_control_plane_replayability_blocker_routes_to_existing_break_glass_before_user_stop(self) -> None:
        def normalized(path: Path) -> str:
            return " ".join(path.read_text(encoding="utf-8").lower().split())

        pm_blocked = normalized(_card_path_by_id("pm.event.reviewer_blocked"))
        pm_repair = normalized(_card_path_by_id("pm.review_repair"))
        break_glass = normalized(_card_path_by_id("controller.break_glass_repair"))

        for text in (pm_blocked, pm_repair):
            self.assertIn("non-replayable package scripts", text)
            self.assertIn("controller break-glass", text)
            self.assertIn("normal repair lane cannot form a legal next action", text)
            self.assertIn("before user stop", text)

        self.assertIn("package-produced script, checker, or evidence generator is not replayable", break_glass)
        self.assertIn("specific flowpilot packet id", break_glass)
        self.assertIn("normal pm repair cannot form a legal next action", break_glass)

    def test_flowguard_project_topology_guidance_is_role_scoped(self) -> None:
        def normalized(path: Path) -> str:
            return " ".join(path.read_text(encoding="utf-8").lower().split())

        required_cards = _card_paths_by_id(
            "pm.core",
            "pm.product_architecture",
            "pm.route_skeleton",
            "pm.node_acceptance_plan",
            "pm.closure",
            "flowguard_operator.core",
            "reviewer.core",
        )
        for path in required_cards:
            with self.subTest(path=path.name):
                text = normalized(path)
                self.assertIn("docs/flowguard_project_topology.md", text)
                self.assertTrue("background architecture" in text or "orientation" in text)
                self.assertTrue(
                    "not a flowguard report" in text
                    or "do not treat topology as a flowguard report" in text
                )
                self.assertTrue(
                    ("gate evidence" in text and ("not" in text or "cannot" in text))
                    or "cannot support a reviewer pass by itself" in text
                    or "cannot close a flowguard or validation gap" in text
                )

        pm_core = normalized(_card_path_by_id("pm.core"))
        self.assertIn("rebuild and check the topology", pm_core)
        self.assertIn("model families, tests, code surfaces, evidence summaries, and known-bad signals", pm_core)

        agents_text = normalized(ROOT / "AGENTS.md")
        self.assertIn("flowguard project topology", agents_text)
        self.assertIn("orientation only", agents_text)
        self.assertIn("python scripts/flowguard_project_topology.py build", agents_text)
        self.assertIn("python scripts/flowguard_project_topology.py check", agents_text)


if __name__ == "__main__":
    unittest.main()
