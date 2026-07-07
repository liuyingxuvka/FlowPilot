from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_KIT = ROOT / "skills" / "flowpilot" / "assets" / "runtime_kit"
FLOWPILOT_ASSETS = ROOT / "skills" / "flowpilot" / "assets"
FLOWPILOT_CORE_RUNTIME = FLOWPILOT_ASSETS / "flowpilot_core_runtime"
sys.path.insert(0, str(ROOT / "simulations"))
sys.path.insert(0, str(FLOWPILOT_ASSETS))

import card_instruction_coverage_model as model  # noqa: E402
from flowpilot_core_runtime import review_window_contracts  # noqa: E402


def _runtime_manifest_cards() -> list[dict[str, object]]:
    manifest = json.loads((RUNTIME_KIT / "manifest.json").read_text(encoding="utf-8"))
    return [card for card in manifest.get("cards", []) if isinstance(card, dict)]


def _runtime_manifest_card_ids() -> set[str]:
    return {
        str(card.get("id"))
        for card in _runtime_manifest_cards()
        if isinstance(card.get("id"), str)
    }


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


def _normalized_path(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").lower().split())


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

    def test_current_prompt_surface_scan_includes_generated_contract_sources(self) -> None:
        scanned = {path.relative_to(ROOT).as_posix() for path in model._iter_current_prompt_surface_paths(ROOT)}
        self.assertIn("skills/flowpilot/assets/flowpilot_router_payload_contracts_pm.py", scanned)
        self.assertIn("skills/flowpilot/assets/flowpilot_router_protocol_work_contracts.py", scanned)
        self.assertIn("skills/flowpilot/assets/flowpilot_router_expected_waits_actions.py", scanned)
        self.assertIn("skills/flowpilot/assets/flowpilot_router_startup_mechanical_boundary_controller.py", scanned)
        self.assertIn("skills/flowpilot/assets/role_output_runtime_contracts.py", scanned)

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

    def test_formal_result_return_defaults_to_body_file_submission(self) -> None:
        required_return = (RUNTIME_KIT / "prompts" / "cards" / "required_return_policy.md").read_text(
            encoding="utf-8"
        )
        scan_roots = (RUNTIME_KIT / "prompts", RUNTIME_KIT / "cards")
        scanned = [path for root in scan_roots for path in root.rglob("*.md")]
        legacy_body_examples = [
            str(path.relative_to(ROOT)).replace("\\", "/")
            for path in scanned
            if "--body <sealed_result_summary>" in path.read_text(encoding="utf-8")
        ]

        self.assertIn("--body-file <sealed_result_body_file>", required_return)
        self.assertEqual(legacy_body_examples, [])

    def test_controller_progress_fraction_guidance_is_runtime_owned(self) -> None:
        guidance_texts = [
            _normalized_path(_card_path_by_id("controller.core")),
            _normalized_path(_card_path_by_id("controller.resume_reentry")),
            _normalized_path(RUNTIME_KIT / "prompts" / "controller" / "action_ledger_table.md"),
            _normalized_path(ROOT / "skills" / "flowpilot" / "SKILL.md"),
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

    def test_controller_progress_fraction_guidance_reports_more_consistently_without_noise(self) -> None:
        guidance_texts = [
            _normalized_path(_card_path_by_id("controller.core")),
            _normalized_path(_card_path_by_id("controller.resume_reentry")),
            _normalized_path(RUNTIME_KIT / "prompts" / "controller" / "action_ledger_table.md"),
            _normalized_path(ROOT / "skills" / "flowpilot" / "SKILL.md"),
        ]
        for text in guidance_texts:
            with self.subTest():
                self.assertIn("normally", text)
                self.assertIn("progress_fraction.display", text)
                self.assertIn("changed active node", text)
                self.assertIn("changed runtime-owned expanded-node fraction", text)
                self.assertIn("quiet patrol", text)
                self.assertIn("ack bookkeeping", text)
                self.assertIn("process-only asides", text)

    def test_node_acceptance_plans_require_concrete_current_check_surfaces(self) -> None:
        pm_node = _normalized_path(_card_path_by_id("pm.node_acceptance_plan"))
        reviewer_node = _normalized_path(_card_path_by_id("reviewer.node_acceptance_plan_review"))

        for text in (pm_node, reviewer_node):
            self.assertIn("current executable check surface", text)
            self.assertIn("status vocabulary", text)
            self.assertIn("expected failure shape", text)
            self.assertIn("bad fixtures", text)
            self.assertIn("worker", text)
            self.assertIn("reviewer", text)

        self.assertIn("do not add new node-context fields", pm_node)
        self.assertIn("replacement parent/module", pm_node)
        self.assertIn("under-split", pm_node)
        self.assertIn("`redesign_route`", pm_node)
        self.assertIn("generic phrases such as \"run validation\"", reviewer_node)
        self.assertIn("worker inventing", reviewer_node)
        self.assertIn("node-boundary problem", reviewer_node)
        self.assertIn("do not block solely because worker artifacts", reviewer_node)

    def test_role_surface_preference_is_present_on_lease_surface(self) -> None:
        text = (ROOT / "skills" / "flowpilot" / "SKILL.md").read_text(encoding="utf-8").lower()
        self.assertIn("prefer durable, addressable role surfaces", text)
        self.assertIn("parallel-count", text)
        self.assertIn("model-capability limits", text)
        self.assertIn("when such surfaces are available", text)

    def test_role_surface_dispatch_is_runtime_disposition_driven(self) -> None:
        def normalized(path: Path) -> str:
            return " ".join(path.read_text(encoding="utf-8").lower().split())

        skill = normalized(ROOT / "skills/flowpilot/SKILL.md")
        protocol = normalized(ROOT / "skills/flowpilot/references/protocol.md")
        failure_modes = normalized(ROOT / "skills/flowpilot/references/failure_modes.md")
        lifecycle_resume = normalized(
            ROOT / "skills/flowpilot/assets/runtime_kit/prompts/startup/lifecycle_resume.md"
        )

        for term in (
            "reuse_existing_role",
            "create_new_role",
            "blocked",
            "effective_agent_id",
            "role_surface_required=true",
            "do not open a fresh ai surface",
            "runtime-provided `flowpilot_new.py dispatch-current-role` command",
        ):
            self.assertIn(term, skill)

        for text in (skill, protocol, lifecycle_resume):
            with self.subTest(surface="host-neutral"):
                self.assertIn("host-supported", text)
                self.assertIn("isolated", text)
                self.assertIn("addressable ai execution surface", text)

        for example in (
            "background agent",
            "separate thread",
            "new conversation",
            "worker",
            "independent ai session",
            "equivalent host-supported mechanism",
        ):
            self.assertIn(example, skill)
            self.assertIn(example, lifecycle_resume)

        self.assertIn("not in the controller foreground", skill)
        self.assertIn("controller must not open role-only packets", skill)
        self.assertIn("perform role work in the controller foreground", failure_modes)
        self.assertIn("controller foreground role work", protocol)

        for text in (protocol, failure_modes, lifecycle_resume):
            self.assertIn("runtime-named", text)
            self.assertIn("recovery", text)
            self.assertIn("blocker", text)

        self.assertIn("reuse_existing_role", failure_modes)
        self.assertIn("fresh same-role ai execution surface", failure_modes)
        self.assertIn("silent same-role replacement", protocol)
        self.assertIn("unless the runtime explicitly authorizes replacement", lifecycle_resume)

    def test_authorized_result_body_guidance_requires_all_related_bodies(self) -> None:
        def normalized(path: Path) -> str:
            return " ".join(path.read_text(encoding="utf-8").lower().split())

        prompt_paths = [
            RUNTIME_KIT / "prompts" / "packets" / "packet_identity_boundary.md",
            RUNTIME_KIT / "prompts" / "packets" / "output_contract_section.md",
        ]
        for path in prompt_paths:
            with self.subTest(path=path.name):
                text = normalized(path)
                self.assertIn("authorized_result_reads", text)
                self.assertIn("every", text)
                self.assertIn("delivered", text)
                self.assertIn("summaries", text)
                self.assertIn("not substitutes", text)

        role_cards = _card_paths_by_id(
            "pm.core",
            "pm.review_repair",
            "reviewer.core",
            "flowguard_operator.core",
            "worker.core",
        )
        for path in role_cards:
            with self.subTest(path=path.name):
                text = normalized(path)
                self.assertIn("authorized_result_reads", text)
                self.assertIn("read every", text)
                self.assertIn("delivered", text)
                self.assertIn("blocker", text)
                self.assertIn("target", text)
                self.assertIn("upstream", text)
                self.assertNotIn("one selected result body is enough", text)

        for card_id in ("pm.core", "pm.review_repair", "worker.core", "reviewer.core", "flowguard_operator.core"):
            with self.subTest(card_id=f"{card_id}.repair_dossier_context"):
                text = normalized(_card_path_by_id(card_id))
                self.assertIn("repair_dossier_context", text)
                self.assertIn("context", text)
                self.assertIn("authorized_result_reads", text)
                self.assertTrue("historical bodies" in text or "prior blocker bodies" in text)

        pm_text = normalized(_card_path_by_id("pm.core"))
        repair_text = normalized(_card_path_by_id("pm.review_repair"))
        flowguard_text = normalized(_card_path_by_id("flowguard_operator.core"))
        for text in (pm_text, repair_text):
            self.assertIn("repair_evidence_obligations", text)
            self.assertIn("repair_obligation_disposition", text)
            self.assertIn("every obligation id", text)
            self.assertIn("reason", text)
            self.assertIn("do not close", text)
        self.assertIn("semantic_recheck", flowguard_text)
        self.assertIn("repair obligation id named by the checklist", flowguard_text)

    def test_allowed_value_options_are_explained_on_ai_facing_contract_surfaces(self) -> None:
        def normalized(path: Path) -> str:
            return " ".join(path.read_text(encoding="utf-8").lower().split())

        prompt_paths = [
            RUNTIME_KIT / "prompts" / "packets" / "output_contract_section.md",
            ROOT / "templates" / "flowpilot" / "packets" / "packet_body.template.md",
        ]
        for path in prompt_paths:
            with self.subTest(path=path.name):
                text = normalized(path)
                self.assertIn("allowed_value_options", text)
                self.assertIn("finite menu", text)
                self.assertIn("choose exactly one listed value", text)
                self.assertIn("do not invent synonyms", text)
                self.assertIn("extra enum values", text)

        for card_id in ("pm.core", "flowguard_operator.core", "reviewer.core"):
            with self.subTest(card_id=card_id):
                text = normalized(_card_path_by_id(card_id))
                self.assertIn("allowed_value_options", text)
                self.assertIn("finite", text)
                self.assertIn("listed value", text)
                self.assertIn("do not invent", text)

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

    def test_prompt_first_quality_chain_preserves_source_intent_without_runtime_semantic_gate(self) -> None:
        def normalized(card_id: str) -> str:
            return " ".join(_card_path_by_id(card_id).read_text(encoding="utf-8").lower().split())

        pm_cards = [
            normalized("pm.core"),
            normalized("pm.startup_intake"),
            normalized("pm.product_architecture"),
            normalized("pm.root_contract"),
            normalized("pm.node_acceptance_plan"),
            normalized("pm.review_repair"),
            normalized("pm.evidence_quality_package"),
            normalized("pm.final_ledger"),
            normalized("pm.closure"),
        ]
        for text in pm_cards:
            with self.subTest(surface="pm"):
                self.assertIn("source-intent", text)
                self.assertTrue("generic" in text or "vague" in text)

        reviewer_cards = [
            normalized("reviewer.core"),
            normalized("reviewer.root_contract_challenge"),
            normalized("reviewer.node_acceptance_plan_review"),
            normalized("reviewer.worker_result_review"),
            normalized("reviewer.evidence_quality_review"),
            normalized("reviewer.final_backward_replay"),
        ]
        for text in reviewer_cards:
            with self.subTest(surface="reviewer"):
                self.assertIn("source-intent", text)
                self.assertTrue("block" in text or "blocker" in text)

        child_skill_cards = [
            normalized("pm.child_skill_selection"),
            normalized("pm.child_skill_gate_manifest"),
            normalized("pm.node_acceptance_plan"),
            normalized("reviewer.node_acceptance_plan_review"),
        ]
        for text in child_skill_cards:
            with self.subTest(surface="child-skill"):
                self.assertTrue("standards lens" in text or "skill_standard_projection" in text)
                self.assertTrue("theme" in text or "generic phrase" in text or "silent weakening" in text)

        flowguard_core = normalized("flowguard_operator.core")
        self.assertIn("process/model/state evidence", flowguard_core)
        self.assertIn("not product-quality proof by itself", flowguard_core)
        self.assertIn("reviewer still owns the semantic pass/block judgement", flowguard_core)
        self.assertIn("pm owns repair", flowguard_core)

        runtime_text = " ".join(
            (
                (ROOT / "skills/flowpilot/assets/flowpilot_core_runtime/runtime.py").read_text(encoding="utf-8").lower(),
                (ROOT / "skills/flowpilot/assets/flowpilot_core_runtime/control_surface.py").read_text(
                    encoding="utf-8"
                ).lower(),
            )
        )
        self.assertNotIn("source-intent comparison", runtime_text)
        self.assertNotIn("generic user-goal wording", runtime_text)
        self.assertNotIn("semantic dilution", runtime_text)

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

        pm_event_and_repair_text = " ".join(
            path.read_text(encoding="utf-8").lower()
            for path in (
                _card_path_by_id("pm.core"),
                _card_path_by_id("pm.event.reviewer_report"),
                _card_path_by_id("pm.event.reviewer_blocked"),
                _card_path_by_id("pm.review_repair"),
            )
        )
        for forbidden in (
            "continue, optimize, defer",
            "whether to continue, defer",
            "mutate, defer, reject",
            "defer a suggestion as vague later work",
        ):
            self.assertNotIn(forbidden, pm_event_and_repair_text)

    def test_review_flow_stage_challenge_bindings_cover_all_declared_review_windows(self) -> None:
        bindings = review_window_contracts.review_flow_stage_challenge_bindings()
        self.assertEqual(set(bindings), set(review_window_contracts.review_flow_ids()))

        manifest_card_ids = _runtime_manifest_card_ids()
        for flow_id, binding in sorted(bindings.items()):
            with self.subTest(flow_id=flow_id):
                card_id = binding["reviewer_card_id"]
                self.assertIn(card_id, manifest_card_ids)
                self.assertTrue(card_id.startswith("reviewer."))
                self.assertNotEqual(card_id, "reviewer.core")
                self.assertNotEqual(card_id, "reviewer.strict_gate_obligation_review")

                rule = review_window_contracts.review_flow_stage_challenge_rule(flow_id).lower()
                self.assertIn("fixed reviewer stage card", rule)
                self.assertIn(card_id.lower(), rule)
                self.assertIn("stage focus", rule)
                self.assertIn("weakest", rule)
                self.assertIn("hypothesis", rule)
                self.assertIn("pm", rule)
                self.assertIn("use existing review result fields only", rule)
                self.assertIn("do not add fields", rule)
                self.assertIn("fallback", rule)

                card_text = _normalized_path(_card_path_by_id(card_id))
                for required in (
                    "weakest evidence",
                    "failure hypothesis",
                    "no-hypothesis rationale",
                    "thin-success",
                    "adopt/reject/no-action",
                    "generic `9/10` optimization advice",
                ):
                    self.assertIn(required, card_text)

        self.assertEqual(
            bindings["pm_flowguard_acceptance_review"]["reviewer_card_id"],
            "reviewer.pm_flowguard_acceptance_review",
        )

    def test_reviewer_and_pm_prompt_surfaces_reject_weak_mechanical_review_templates(self) -> None:
        prompt_paths = [
            FLOWPILOT_CORE_RUNTIME / "packet_result_contracts.py",
            FLOWPILOT_CORE_RUNTIME / "role_handoff.py",
            ROOT / "templates" / "flowpilot" / "packets" / "packet_body.template.md",
            _card_path_by_id("reviewer.core"),
            _card_path_by_id("reviewer.worker_result_review"),
            _card_path_by_id("reviewer.material_sufficiency"),
            _card_path_by_id("pm.core"),
            _card_path_by_id("pm.event.reviewer_report"),
            _card_path_by_id("pm.event.reviewer_blocked"),
            _card_path_by_id("pm.review_repair"),
        ]
        forbidden_fragments = (
            "current minimum gate passes; consider whether",
            "include at least one higher-standard suggestion",
            "include at least one source-quality",
            "pm may consider whether a 9/10 quality optimization pass is useful",
        )
        for path in prompt_paths:
            text = path.read_text(encoding="utf-8").lower()
            with self.subTest(path=path.relative_to(ROOT).as_posix()):
                for fragment in forbidden_fragments:
                    self.assertNotIn(fragment, text)

        packet_template = (
            ROOT / "templates" / "flowpilot" / "packets" / "packet_body.template.md"
        ).read_text(encoding="utf-8").lower()
        for required in (
            "mechanical field checklists, not answer templates",
            "weakest evidence",
            "concrete failure hypothesis",
            "thin-success",
            "pm-actionable adopt/reject/no-action rationale",
        ):
            self.assertIn(required, packet_template)

    def test_reviewer_card_blocks_shallow_flowguard_with_pm_recheck_guidance(self) -> None:
        text = _normalized_path(_card_path_by_id("reviewer.core"))

        for required in (
            "mechanically passed flowguard report is not enough",
            "field shape",
            "current-contract mechanics",
            "target risk",
            "passed: false",
            "flowguard_failure",
            "pm_suggestion_items",
            "focused flowguard repair or recheck",
        ):
            self.assertIn(required, text)

    def test_reviewer_quality_score_rubric_reaches_pm_worker_and_reviewer_cards(self) -> None:
        reviewer_core = _normalized_path(_card_path_by_id("reviewer.core"))
        reviewer_worker = _normalized_path(_card_path_by_id("reviewer.worker_result_review"))
        reviewer_node = _normalized_path(_card_path_by_id("reviewer.node_acceptance_plan_review"))
        pm_core = _normalized_path(_card_path_by_id("pm.core"))
        pm_repair = _normalized_path(_card_path_by_id("pm.review_repair"))
        pm_reviewer_report = _normalized_path(_card_path_by_id("pm.event.reviewer_report"))
        pm_reviewer_blocked = _normalized_path(_card_path_by_id("pm.event.reviewer_blocked"))
        worker_core = _normalized_path(_card_path_by_id("worker.core"))

        for text in (reviewer_core, reviewer_worker, reviewer_node):
            with self.subTest(surface="reviewer"):
                self.assertIn("quality score: x/10; target: 9/10; minimum hard gate passed: true|false", text)
                self.assertIn("6/10", text)
                self.assertIn("minimum user standard", text)
                self.assertIn("9/10", text)
                self.assertIn("10/10", text)
                self.assertIn("substantially exceeds", text)
                self.assertIn("quantitative", text)
                self.assertIn("required, delivered, gap", text)
                self.assertIn("pm decision-support", text)
                self.assertIn("not a blocker by itself", text)

        for text in (pm_core, pm_repair, pm_reviewer_report, pm_reviewer_blocked):
            with self.subTest(surface="pm"):
                self.assertTrue(
                    "reviewer score interpretation" in text
                    or "reviewer score rubric" in text
                )
                self.assertIn("quality score: x/10; target: 9/10; minimum hard gate passed: true|false", text)
                self.assertIn("6/10", text)
                self.assertIn("minimum user standard", text)
                self.assertIn("9/10", text)
                self.assertIn("10/10", text)
                self.assertIn("pm always owns the optimization choice", text)
                self.assertIn("even when reviewer reports no blocker", text)
                self.assertIn("quantitative", text)
                self.assertIn("required/delivered/gap", text)

        self.assertIn("quality score: x/10; target: 9/10; minimum hard gate passed: true|false", worker_core)
        self.assertIn("authorized materials", worker_core)
        self.assertIn("9/10", worker_core)
        self.assertIn("quantitative gap", worker_core)
        self.assertIn("blocked", worker_core)
        self.assertIn("needs_pm", worker_core)

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

    def test_route_depth_cards_use_single_canonical_tree_and_derived_display_projection(self) -> None:
        def normalized(card_id: str) -> str:
            return " ".join(_card_path_by_id(card_id).read_text(encoding="utf-8").lower().split())

        route_card = normalized("pm.route_skeleton")
        controller_card = normalized("controller.core")
        flowguard_card = normalized("flowguard_operator.route_process_check")
        reviewer_card = normalized("reviewer.route_challenge")
        node_plan_card = normalized("reviewer.node_acceptance_plan_review")
        controller_text = controller_card

        self.assertIn("one canonical executable route tree", route_card)
        self.assertIn("router-derived", route_card)
        self.assertIn("not separate pm route authority", route_card)
        self.assertIn("route decomposition quality is semantic, not field count", route_card)
        self.assertIn("do not add broad per-node explanation fields", route_card)
        self.assertIn("canonical executable route tree and current frontier", controller_card)
        self.assertIn("pm authored one canonical executable route tree", flowguard_card)
        self.assertIn("parent backward review after all child nodes complete", flowguard_card)
        self.assertIn("worker-decision leakage", flowguard_card)
        self.assertIn("not one tree for execution plus a second pm-maintained display plan", reviewer_card)
        self.assertIn("reviewer is the semantic decomposition quality gate", reviewer_card)
        self.assertIn("concrete pm-actionable split recommendation", reviewer_card)
        self.assertIn("worker replanning is not an acceptable substitute for route depth", reviewer_card)
        self.assertIn("must not override the canonical route node shape", node_plan_card)
        self.assertIn("route-depth safety gate", node_plan_card)
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

    def test_route_redesign_cards_block_flat_leaf_and_peer_appended_splits(self) -> None:
        def normalized(card_id: str) -> str:
            return " ".join(_card_path_by_id(card_id).read_text(encoding="utf-8").lower().split())

        pm_route = normalized("pm.route_skeleton")
        pm_node = normalized("pm.node_acceptance_plan")
        pm_core = normalized("pm.core")
        reviewer_route = normalized("reviewer.route_challenge")
        reviewer_node = normalized("reviewer.node_acceptance_plan_review")
        flowguard_route = normalized("flowguard_operator.route_process_check")

        self.assertIn("complex flat all-leaf route plan", pm_route)
        self.assertIn("replacement parent/module node", pm_route)
        self.assertIn("flat peer leaves", pm_node)
        self.assertIn("replacement parent/module scope", pm_core)
        self.assertIn("complex flat all-leaf route plan", reviewer_route)
        self.assertIn("peer-appended split", reviewer_node)
        self.assertIn("complex flat all-leaf route plan", flowguard_route)
        self.assertIn("node-entry redesign did not promote active scope", flowguard_route)

    def test_route_cards_check_producer_before_consumer_order(self) -> None:
        def normalized(card_id: str) -> str:
            return " ".join(_card_path_by_id(card_id).read_text(encoding="utf-8").lower().split())

        pm_route = normalized("pm.route_skeleton")
        flowguard_route = normalized("flowguard_operator.route_process_check")
        reviewer_route = normalized("reviewer.route_challenge")
        pm_node = normalized("pm.node_acceptance_plan")
        reviewer_node = normalized("reviewer.node_acceptance_plan_review")

        self.assertIn("producer-before-consumer route order", pm_route)
        self.assertIn("do not add a dependency ledger or extra route-node fields", pm_route)
        self.assertIn("producer-before-consumer order", flowguard_route)
        self.assertIn("dependency-order inversion", flowguard_route)
        self.assertIn("not viable as drafted", flowguard_route)
        self.assertIn("producer-before-consumer dependency direction", reviewer_route)
        self.assertIn("unfinished producer", reviewer_route)
        self.assertIn("consumer of future route output", pm_node)
        self.assertIn('`decision: "redesign_route"`', pm_node)
        self.assertIn("do not demand future-stage evidence", pm_node)
        self.assertIn("producer-before-consumer order at node entry", reviewer_node)
        self.assertIn("later unfinished route node", reviewer_node)
        self.assertIn("do not require future-stage worker artifacts", reviewer_node)

    def test_system_integration_duty_is_prompt_owned_without_runtime_shape_expansion(self) -> None:
        def normalized(card_id: str) -> str:
            return " ".join(_card_path_by_id(card_id).read_text(encoding="utf-8").lower().split())

        pm_core = normalized("pm.core")
        reviewer_core = normalized("reviewer.core")
        flowguard_core = normalized("flowguard_operator.core")
        worker_core = normalized("worker.core")
        pm_product = normalized("pm.product_architecture")
        pm_route = normalized("pm.route_skeleton")
        pm_node = normalized("pm.node_acceptance_plan")
        reviewer_node = normalized("reviewer.node_acceptance_plan_review")
        pm_current_node = normalized("pm.current_node_loop")
        parent_replay = normalized("reviewer.parent_backward_replay")
        final_replay = normalized("reviewer.final_backward_replay")
        pm_final_ledger = normalized("pm.final_ledger")
        pm_model_miss = normalized("pm.model_miss_triage")
        flowguard_route = normalized("flowguard_operator.route_process_check")

        self.assertIn("system integration owner", pm_core)
        self.assertIn("not a new role, runtime hard blocker, ledger, packet family, or self-stop", pm_core)
        self.assertIn("scattered local-pass/global-incoherent output", pm_core)
        self.assertIn("whole-output composition", reviewer_core)
        self.assertIn("pm decision-support", reviewer_core)
        self.assertIn("scattered local-pass/global-incoherent output as a process or state hazard", flowguard_core)
        self.assertIn("you are not the system integrator", worker_core)
        self.assertIn("do not silently redesign the route", worker_core)
        self.assertIn("suggestions must not use `current_gate_blocker`", worker_core)

        self.assertIn("system_integration_intent", pm_product)
        self.assertIn("system_integration_intent", pm_route)
        self.assertIn("flat checklist of unrelated local completions", pm_route)
        self.assertIn("integration_touchpoint", pm_node)
        self.assertIn("not a runtime-expanded node context field", pm_node)
        self.assertIn("integration_touchpoint", reviewer_node)
        self.assertIn("integration_touchpoint", pm_current_node)
        self.assertIn("existing disposition vocabulary", pm_current_node)
        self.assertIn("locally passing child outputs", parent_replay)
        self.assertIn("coherent as one whole artifact or system", final_replay)
        self.assertIn("whole-output composition closure", pm_final_ledger)
        self.assertIn("local packets passed but the parent/final output is globally incoherent", pm_model_miss)
        self.assertIn("scattered local-pass outputs", flowguard_route)

        node_template = json.loads((ROOT / "templates/flowpilot/node_acceptance_plan.template.json").read_text(encoding="utf-8"))
        self.assertIn("integration_touchpoint", node_template)
        self.assertEqual(
            set(node_template["node_context_package"]),
            {
                "purpose",
                "acceptance_criteria",
                "relevant_references",
                "known_risks",
                "acceptance_item_projection",
            },
        )
        self.assertNotIn("integration_touchpoint", node_template["node_context_package"])

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
            "flowguard and test gap ownership",
            "pm does not pre-fill large model/test matrices",
            "existing model preflight",
            "developmentprocessflow",
            "model-test alignment",
            "testmesh",
            "current_required_fields",
            "allowed_value_options",
        ):
            self.assertIn(term, pm_core)
        self.assertIn("let flowguard record it in evidence", pm_core)
        self.assertIn("do not turn it into a required pm node-plan field", pm_core)

        pm_node_plan = normalized(_card_path_by_id("pm.node_acceptance_plan"))
        for term in (
            "`purpose`",
            "`acceptance_criteria`",
            "`relevant_references`",
            "`known_risks`",
            "`acceptance_item_projection`",
            "do not add pm-only pre-worker test matrices",
            "flowguard operator, reviewer, worker, and testmesh each expand their own checks",
        ):
            self.assertIn(term, pm_node_plan)
        self.assertNotIn("test_obligation_matrix", pm_node_plan)
        self.assertNotIn("work_packet_projection", pm_node_plan)

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
            "current evidence obligation ids",
            "test obligation coverage",
            "maintain ordinary packet-scoped tests",
            "flowguard operators identify obligations and gaps",
        ):
            self.assertIn(term, pm_role_work)
        self.assertNotIn("test_obligation_matrix", pm_role_work)

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
                self.assertIn("current evidence", text)
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
        self.assertIn("`decision`", pm_node_plan)
        self.assertIn('`decision: "pass"`', pm_node_plan)
        self.assertIn('`decision: "redesign_route"`', pm_node_plan)
        self.assertIn("ordinary node entry does not issue a separate pre-worker flowguard packet", pm_node_plan)
        self.assertIn("pm_flowguard_acceptance", pm_node_plan)
        self.assertIn("commit_node_acceptance_plan", pm_node_plan)
        self.assertIn("runtime stages the route effect", pm_node_plan)

        reviewer_node_plan = normalized(_card_path_by_id("reviewer.node_acceptance_plan_review"))
        self.assertIn("runtime owns mechanical validation", reviewer_node_plan)
        self.assertIn("review the real node acceptance plan", reviewer_node_plan)
        self.assertIn("semantically safe to commit", reviewer_node_plan)
        self.assertIn("plan-stage review", reviewer_node_plan)
        self.assertIn("do not block solely because worker artifacts", reviewer_node_plan)

        flowguard_core = normalized(_card_path_by_id("flowguard_operator.core"))
        self.assertIn("current subject simulation boundary", flowguard_core)
        self.assertIn("route traversal", flowguard_core)
        self.assertIn("work dispatch", flowguard_core)
        self.assertIn("validation/check path", flowguard_core)
        self.assertIn("blocker/failure path", flowguard_core)
        self.assertIn("repair return path", flowguard_core)
        self.assertIn("when the packet includes `staged_effect`", flowguard_core)
        self.assertIn("do not require future committed fields", flowguard_core)
        self.assertIn("process/state/evidence risk review", flowguard_core)

        reviewer_core = normalized(_card_path_by_id("reviewer.core"))
        self.assertIn("ordinary `node_acceptance_plan` pass branch", reviewer_core)
        self.assertIn("do not invent a pre-worker flowguard requirement", reviewer_core)
        self.assertIn("plan-stage review", reviewer_core)
        self.assertIn("do not block solely because worker artifacts", reviewer_core)
        self.assertIn("structural_pm_flowguard_acceptance_gate", reviewer_core)
        self.assertIn("pm actually absorbed the current flowguard result", reviewer_core)

        pm_resume = normalized(_card_path_by_id("pm.resume_decision"))
        self.assertIn("plain lifecycle resume does not clear", pm_resume)
        self.assertIn("resolve-stopped-blocker", pm_resume)
        self.assertIn("--user-requested", pm_resume)
        self.assertIn("ordinary patrol, resume, or chat-history context must not do it automatically", pm_resume)

    def test_pm_stop_options_distinguish_user_stop_from_break_glass(self) -> None:
        def normalized(path: Path) -> str:
            return " ".join(path.read_text(encoding="utf-8").lower().split())

        pm_core = normalized(_card_path_by_id("pm.core"))
        pm_repair = normalized(_card_path_by_id("pm.review_repair"))
        pm_resume = normalized(_card_path_by_id("pm.resume_decision"))
        pm_model_miss = normalized(_card_path_by_id("pm.model_miss_triage"))
        pm_flowguard_loop = normalized(_card_path_by_id("pm.flowguard_operator_request_report_loop"))

        for text in (pm_core, pm_repair, pm_resume, pm_model_miss, pm_flowguard_loop):
            self.assertIn("break_glass", text)
            self.assertTrue("control-plane" in text or "control plane" in text)

        for text in (pm_repair, pm_model_miss, pm_flowguard_loop):
            self.assertTrue("use `stop_for_user` only" in text or "choose `stop_for_user` only" in text)
            self.assertIn("substantive", text)
            self.assertIn("user", text)

        self.assertIn("use `stop_for_user_or_environment` only", pm_resume)
        self.assertIn("create_repair_or_route_mutation_node", pm_resume)
        self.assertIn("request_sender_reissue", pm_resume)

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

    def test_repair_loop_threshold_routes_to_break_glass_guidance(self) -> None:
        def normalized(path: Path) -> str:
            return " ".join(path.read_text(encoding="utf-8").lower().split())

        pm_repair = normalized(_card_path_by_id("pm.review_repair"))
        controller = normalized(_card_path_by_id("controller.core"))
        break_glass = normalized(_card_path_by_id("controller.break_glass_repair"))
        flowguard_process = normalized(_card_path_by_id("flowguard_operator.route_process_check"))
        worker_review = normalized(_card_path_by_id("reviewer.worker_result_review"))
        node_plan_review = normalized(_card_path_by_id("reviewer.node_acceptance_plan_review"))

        self.assertIn("same repair dossier under the same parent has reached five consecutive repair nodes", pm_repair)
        self.assertIn("does not require the same blocker class", pm_repair)
        self.assertIn("repair_dossier_context", pm_repair)
        self.assertIn("do not issue another ordinary pm repair decision packet", pm_repair)
        self.assertIn("terminal supplemental repair contracts use the runtime's separate three-round cap", pm_repair)
        self.assertIn("after the third round, pm must choose a legal terminal disposition", pm_repair)
        self.assertIn("route a new pm decision from the current blocker context", pm_repair)
        self.assertIn("repair_loop_break_glass_review", controller)
        self.assertIn("same repair dossier under the same parent has reached five consecutive repair nodes", controller)
        self.assertIn("similar blocker classes spread across different route nodes are ordinary repair evidence", controller)
        self.assertIn("same repair dossier under the same parent has reached five consecutive repair nodes", break_glass)
        self.assertIn("false alarm", break_glass)
        self.assertIn("mechanical progress from semantic repair progress", flowguard_process)
        self.assertIn("five consecutive same-dossier repair nodes", flowguard_process)
        self.assertIn("reuse the prior `blocker_class`", worker_review)
        self.assertIn("runtime break-glass threshold counts same-dossier repair continuity", worker_review)
        self.assertIn("reuse the prior `blocker_class`", node_plan_review)
        self.assertIn("runtime break-glass threshold counts same-dossier repair continuity", node_plan_review)

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
