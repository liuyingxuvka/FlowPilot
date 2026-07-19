from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest

from simulations import run_flowpilot_skillguard_contract_checks as contract_runner


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "skills" / "flowpilot"
CONTROL = TARGET / ".skillguard"
SOURCE_PATH = CONTROL / "contract-source.json"
CONTRACT_PATH = CONTROL / "compiled-contract.json"
MANIFEST_PATH = CONTROL / "check-manifest.json"
MODEL_PATH = ROOT / "simulations" / "flowpilot_skillguard_contract_model.py"

FORMER_PATHS = (
    "work-contract.json",
    "check_manifest.json",
    "skillguard_manifest.json",
    "skillguard_profile.json",
    "skillguard_skill_contract.json",
    "skillguard_evidence_rules.json",
    "skillguard_closure_policy.json",
    "skillguard_progress_ledger.jsonl",
    "checks/check_route.py",
    "checks/check_phase_order.py",
    "checks/check_evidence.py",
    "checks/check_quality_floor.py",
    "checks/check_closure.py",
)


def _load_model_module():
    spec = importlib.util.spec_from_file_location(
        "flowpilot_skillguard_contract_model_test", MODEL_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


class FlowPilotSkillGuardDeepContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_one_current_contract_trio_replaces_every_former_authority(self) -> None:
        self.assertEqual(
            self.source["schema_version"], "skillguard.contract_source.v2"
        )
        self.assertEqual(
            self.contract["schema_version"], "skillguard.compiled_contract.v2"
        )
        self.assertEqual(
            self.manifest["schema_version"], "skillguard.check_manifest.v2"
        )
        self.assertEqual(
            self.contract["contract_hash"], self.manifest["contract_hash"]
        )
        self.assertEqual(
            self.contract["check_declarations_hash"],
            self.manifest["check_declarations_hash"],
        )
        for relative in FORMER_PATHS:
            self.assertFalse((CONTROL / relative).exists(), relative)

    def test_flowpilot_remains_the_only_native_runtime_owner(self) -> None:
        self.assertEqual(self.source["integration_mode"], "native-integrated")
        self.assertEqual(
            self.source["native_route_owner"], "flowpilot_runtime_router"
        )
        self.assertFalse(self.source["may_define_parallel_execution_route"])
        self.assertFalse(self.source["may_define_skillguard_runtime_route"])
        self.assertIn(
            "without creating a SkillGuard-owned runtime",
            self.contract["claim_boundary"],
        )
        self.assertIn(
            "FlowPilot owns every domain action and native check",
            self.contract["claim_boundary"],
        )
        owners = {row["owner_id"] for row in self.contract["routes"]}
        self.assertEqual(owners, {"flowpilot_runtime_router"})

    def test_native_handoff_bindings_cover_every_existing_route_and_check(self) -> None:
        native_routes = {
            row["native_route_id"] for row in self.source["native_route_bindings"]
        }
        self.assertEqual(
            native_routes,
            {row["route_id"] for row in self.contract["routes"]},
        )
        native_checks = {
            row["native_check_id"] for row in self.source["native_check_bindings"]
        }
        self.assertEqual(
            native_checks,
            {row["check_id"] for row in self.source["checks"]},
        )
        for row in self.source["native_route_bindings"]:
            self.assertTrue((ROOT / row["source"]).is_file(), row)
            self.assertTrue(row["required_before_closure"], row)
        for row in self.source["native_check_bindings"]:
            self.assertTrue((ROOT / row["evidence_source"]).is_file(), row)
            self.assertTrue(row["required"], row)

        module = _load_model_module()
        self.assertEqual(
            module._run(module.ContractInput(native_route_bindings_current=False))[1],
            "native_route_bindings_missing",
        )
        self.assertEqual(
            module._run(module.ContractInput(native_check_bindings_current=False))[1],
            "native_check_bindings_missing",
        )

    def test_exported_flowguard_model_covers_the_four_existing_stage_owners(self) -> None:
        module = _load_model_module()
        exported = module.export_contract_model()
        self.assertEqual(
            exported["schema_version"], "skillguard.flowguard_model_export.v2"
        )
        self.assertEqual(
            {row["route_id"] for row in exported["routes"]},
            {
                "route:flowpilot-opt-in",
                "route:flowpilot-route-plan",
                "route:flowpilot-complete-workstream",
                "route:flowpilot-independent-closure",
            },
        )
        self.assertEqual(len(exported["obligations"]), 10)
        self.assertEqual(module.main(), 0)

    def test_every_required_model_obligation_has_a_check_and_monotonic_closure(self) -> None:
        obligation_ids = {
            row["obligation_id"]
            for row in self.contract["obligations"]
            if row["required"]
        }
        covered = {
            obligation_id
            for check in self.contract["checks"]
            for obligation_id in check["covers_obligation_ids"]
        }
        self.assertEqual(covered, obligation_ids)

        self.assertEqual(
            [row["profile_id"] for row in self.contract["closure_profiles"]],
            ["enforced"],
        )
        self.assertEqual(
            set(self.contract["closure_profiles"][0]["required_obligation_ids"]),
            obligation_ids,
        )

    def test_depth_profile_enforces_declared_checks_without_domain_ownership(self) -> None:
        profile = self.contract["depth_profile"]
        self.assertEqual(profile["schema_version"], "skillguard.depth_profile.v2")
        self.assertEqual(profile["enforcement_level"], "enforced")
        self.assertFalse(profile["skillguard_adds_domain_route"])
        self.assertEqual(
            profile["required_closure_profiles"],
            ["enforced"],
        )
        self.assertEqual(
            profile["provider_runtime"]["required_enrollment_status"],
            "enrolled",
        )
        self.assertTrue(
            set(profile["provider_runtime"]["readiness_check_ids"])
            <= set(profile["native_check_ids"])
        )
        self.assertIn("FlowPilot owns the meaning", profile["claim_boundary"])

    def test_final_receipt_check_is_a_read_only_consumer_not_a_second_owner(self) -> None:
        check = next(
            row
            for row in self.contract["checks"]
            if row["check_id"] == "check:flowpilot-final-receipt"
        )
        self.assertIn("--verify-background", check["args"])
        self.assertNotIn("--background", check["args"])
        self.assertNotIn("--resume", check["args"])
        self.assertTrue(
            any(
                str(value).endswith("/v0.12.0-final")
                for value in check["args"]
            )
        )

    def test_focused_flowguard_runner_closes_scenarios_progress_and_refinement(self) -> None:
        report = contract_runner.run_checks()
        self.assertTrue(report["ok"], report)
        self.assertTrue(report["scenario_review"]["ok"])
        self.assertTrue(report["progress_and_loop_review"]["ok"])
        self.assertTrue(report["contract_conformance"]["ok"])
        self.assertTrue(report["contract_refinement"]["ok"])

    def test_openspec_freshness_tracks_skillguard_sources_not_result_output(self) -> None:
        contract_text = (
            ROOT
            / "openspec"
            / "changes"
            / "restore-flowpilot-test-evidence-closure"
            / "verification-contract.yaml"
        ).read_text(encoding="utf-8")
        freshness = contract_text.split("freshness:", 1)[1]
        for relative in (
            "skills/flowpilot/.skillguard/contract-source.json",
            "skills/flowpilot/.skillguard/compiled-contract.json",
            "skills/flowpilot/.skillguard/check-manifest.json",
            "simulations/flowpilot_skillguard_contract_model.py",
            "simulations/run_flowpilot_skillguard_contract_checks.py",
            "scripts/refresh_flowpilot_skillguard_contract.py",
            "tests/test_flowpilot_skillguard_deep_contract.py",
        ):
            self.assertIn(relative, freshness)
        self.assertNotIn(
            "simulations/flowpilot_skillguard_current_contract_results.json",
            freshness,
        )


if __name__ == "__main__":
    unittest.main()
