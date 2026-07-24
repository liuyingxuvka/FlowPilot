from __future__ import annotations

import copy
import importlib
import hashlib
import json
import tempfile
import unittest
from unittest import mock
from pathlib import Path

import scripts.compile_flowpilot_acceptance_testmesh_evidence as evidence_compiler

acceptance_model = importlib.import_module("simulations.flowpilot_acceptance_testmesh_model")
acceptance_runner = importlib.import_module("simulations.run_flowpilot_acceptance_testmesh_checks")
evidence_truth = importlib.import_module("simulations.flowpilot_evidence_truth")
test_tier_runner = importlib.import_module("scripts.run_test_tier")
impact_resolution = importlib.import_module("scripts.test_tier.impact_resolution")
evidence_v5 = importlib.import_module("scripts.test_tier.evidence_v5")
background_supervisor = importlib.import_module(
    "scripts.test_tier.background_supervisor"
)
evidence_validation = importlib.import_module(
    evidence_compiler.validated_tier.__module__
)
checkpoint_manifest = importlib.import_module(
    evidence_compiler._compile_owner_checkpoint_manifest.__module__
)
_ORIGINAL_COMMANDS_FOR_TIER = test_tier_runner.commands_for_tier


class FlowPilotAcceptanceTestMeshTests(unittest.TestCase):
    _tier_fixture_cache: dict[str, dict[str, object]] = {}

    @staticmethod
    def fixture_commands_for_tier(tier: str):
        commands = _ORIGINAL_COMMANDS_FOR_TIER(tier)
        if tier != "all":
            return commands
        required_owner_ids: set[str] = set()
        for config in acceptance_runner.BACKGROUND_CHILD_SUITES.values():
            required_owner_ids.update(config["expected"])
        return tuple(
            command
            for command in commands
            if command.name in required_owner_ids
        )

    def setUp(self) -> None:
        # These tests exercise V5 compilation and fail-closed consumption, not
        # the separate full owner-inventory contract. Keep exactly the owners
        # consumed by the acceptance mesh so each case does not rebuild 220
        # unrelated proofs.
        self._command_patchers = [
            mock.patch.object(
                test_tier_runner,
                "commands_for_tier",
                side_effect=self.fixture_commands_for_tier,
            ),
            mock.patch.object(
                evidence_validation,
                "commands_for_tier",
                side_effect=self.fixture_commands_for_tier,
            ),
            mock.patch.object(
                checkpoint_manifest,
                "commands_for_tier",
                side_effect=self.fixture_commands_for_tier,
            ),
        ]
        for patcher in self._command_patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def write_tier_proof_root(self, root: Path, tier: str) -> None:
        root.mkdir(parents=True, exist_ok=True)
        commands = test_tier_runner.commands_for_tier(tier)
        cached = self._tier_fixture_cache.get(tier)
        if cached is None:
            contracts = {
                contract.owner_id: contract
                for contract in impact_resolution.build_owner_contracts(commands)
            }
            snapshot = evidence_compiler.source_snapshot()
            decisions = []
            for command in commands:
                contract = contracts[command.name]
                identity = impact_resolution.owner_identity(contract).to_dict()
                decisions.append(
                    {
                        "owner_id": command.name,
                        "action": "execute",
                        "reason_codes": ["fixture_current_execution"],
                        "identity": identity,
                        "previous_proof_artifact_id": "",
                        "previous_proof_ref": None,
                        "reuse_ticket_identity": "",
                    }
                )
            cached = {
                "contracts": contracts,
                "snapshot": snapshot,
                "decisions": decisions,
            }
            self._tier_fixture_cache[tier] = cached
        fixture = copy.deepcopy(cached)
        contracts = fixture["contracts"]
        snapshot = fixture["snapshot"]
        decisions = fixture["decisions"]
        plan_id = f"fixture-plan-{tier}"
        owner_ids = sorted(command.name for command in commands)
        plan = {
            "schema_version": impact_resolution.IMPACT_PLAN_SCHEMA_VERSION,
            "plan_id": plan_id,
            "requested_scope": tier,
            "snapshot": snapshot,
            "previous_manifest": {"path": "", "sha256": ""},
            "seed_baseline": True,
            "contracts": [
                contract.to_dict() for contract in contracts.values()
            ],
            "decisions": decisions,
            "blockers": [],
            "execute_owner_ids": owner_ids,
            "reuse_owner_ids": [],
        }
        control_paths = background_supervisor.supervisor_control_paths(root, tier)
        control_paths["impact_plan"].write_text(
            json.dumps(plan, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        plan_ref = {
            **evidence_v5.path_reference(
                control_paths["impact_plan"],
                root=evidence_compiler.ROOT,
            ),
            "plan_id": plan_id,
        }
        owners = {}
        for command in commands:
            identity = next(
                row["identity"]
                for row in decisions
                if row["owner_id"] == command.name
            )
            paths = test_tier_runner.artifact_paths(root, command.name)
            paths["out"].write_text("fixture stdout proof\n", encoding="utf-8")
            paths["err"].write_text("", encoding="utf-8")
            paths["exit"].write_text("0\n", encoding="utf-8")
            stdout = evidence_v5.stream_descriptor(
                paths["out"],
                path_value=str(paths["out"].resolve()),
            )
            stderr = evidence_v5.stream_descriptor(
                paths["err"],
                path_value=str(paths["err"].resolve()),
            )
            result_fingerprint = evidence_v5.background_result_fingerprint_v2(
                stdout=stdout,
                stderr=stderr,
                exit_code=0,
                status="passed",
                descendant_zero_confirmed=True,
                cleanup_reason="fixture_no_process",
            )
            paths["combined"].write_bytes(
                evidence_v5.terminal_stream_index_bytes(
                    name=command.name,
                    status="passed",
                    exit_code=0,
                    start_time="2026-07-10T00:00:00+00:00",
                    end_time="2026-07-10T00:00:01+00:00",
                    stdout=stdout,
                    stderr=stderr,
                    descendant_zero_confirmed=True,
                    cleanup_reason="fixture_no_process",
                    result_fingerprint=result_fingerprint,
                )
            )
            meta = {
                "schema_version": evidence_v5.BACKGROUND_CHILD_META_SCHEMA_VERSION,
                "name": command.name,
                "owner_id": command.name,
                "command": list(command.command),
                "status": "passed",
                "start_time": "2026-07-10T00:00:00+00:00",
                "end_time": "2026-07-10T00:00:01+00:00",
                "exit_code": 0,
                "impact_plan_ref": {
                    **plan_ref,
                    "owner_id": command.name,
                },
                "owner_identity_sha256": evidence_v5.sha256_json(identity),
                "inputs_current": True,
                "descendant_zero_confirmed": True,
                "cleanup_proof": {
                    "cleanup_confirmed": True,
                    "descendant_zero_confirmed": True,
                    "reason": "fixture_no_process",
                },
                "stream_artifacts": {
                    "stdout": stdout,
                    "stderr": stderr,
                },
                "combined_artifact": {
                    **evidence_v5.path_reference(
                        paths["combined"],
                        root=evidence_compiler.ROOT,
                    ),
                    "kind": "terminal_stream_index",
                    "max_bytes": evidence_v5.COMBINED_INDEX_MAX_BYTES,
                },
                "combined_kind": "terminal_stream_index",
                "result_fingerprint_schema_version": (
                    evidence_v5.BACKGROUND_RESULT_FINGERPRINT_SCHEMA_VERSION
                ),
                "result_fingerprint": result_fingerprint,
                "artifacts": {
                    key: str(value) for key, value in paths.items()
                },
            }
            paths["meta"].write_text(
                json.dumps(meta, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            owners[command.name] = (
                impact_resolution.owner_reference_from_child_meta(
                    owner_id=command.name,
                    meta_path=paths["meta"],
                    meta=meta,
                )
            )
        owner_index = {
            "schema_version": evidence_v5.BACKGROUND_OWNER_INDEX_SCHEMA_VERSION,
            "tier": tier,
            "impact_plan_id": plan_id,
            "impact_plan_sha256": plan_ref["sha256"],
            "status": "passed",
            "expected_owner_ids": owner_ids,
            "owner_count": len(owner_ids),
            "execute_count": len(owner_ids),
            "reuse_count": 0,
            "owners": [owners[owner_id] for owner_id in owner_ids],
            "snapshot_end_fingerprint": snapshot["fingerprint"],
            "final_impact_failures": [],
        }
        control_paths["owner_index"].write_text(
            json.dumps(owner_index, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        progress = {
            "schema_version": (
                evidence_v5.BACKGROUND_SUPERVISOR_PROGRESS_SCHEMA_VERSION
            ),
            "tier": tier,
            "impact_plan_id": plan_id,
            "status": "passed",
            "updated_at": "2026-07-10T00:00:01+00:00",
            "counts": {
                "owner": len(owner_ids),
                "execute": len(owner_ids),
                "reuse": 0,
                "pending": 0,
                "running": 0,
                "terminal": len(owner_ids),
            },
            "pending_owner_count": 0,
            "running_owner_ids": [],
            "recent_terminal": [],
        }
        control_paths["progress"].write_text(
            json.dumps(progress, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        supervisor_paths = test_tier_runner.artifact_paths(
            root,
            test_tier_runner.background_supervisor_name(tier),
        )
        supervisor_paths["out"].write_text(
            "fixture supervisor proof\n",
            encoding="utf-8",
        )
        supervisor_paths["err"].write_text("", encoding="utf-8")
        supervisor_meta = {
            "schema_version": evidence_v5.BACKGROUND_SUPERVISOR_META_SCHEMA_VERSION,
            "name": test_tier_runner.background_supervisor_name(tier),
            "tier": tier,
            "status": "passed",
            "exit_code": 0,
            "start_time": "2026-07-10T00:00:00+00:00",
            "end_time": "2026-07-10T00:00:01+00:00",
            "command_count": len(commands),
            "execute_count": len(commands),
            "reuse_count": 0,
            "running_owner_count": 0,
            "terminal_owner_count": len(commands),
            "snapshot_start_fingerprint": snapshot["fingerprint"],
            "snapshot_end_fingerprint": snapshot["fingerprint"],
            "impact_plan_ref": plan_ref,
            "progress_ref": evidence_v5.path_reference(
                control_paths["progress"],
                root=evidence_compiler.ROOT,
            ),
            "owner_index_ref": evidence_v5.path_reference(
                control_paths["owner_index"],
                root=evidence_compiler.ROOT,
            ),
            "artifacts": {
                key: str(value) for key, value in supervisor_paths.items()
            },
        }
        background_supervisor._finalize_supervisor(
            supervisor_paths,
            supervisor_meta,
            exit_code=0,
        )

    def current_routine_evidence(self, root: Path) -> dict[str, dict[str, object]]:
        root.mkdir(parents=True, exist_ok=True)
        declared = acceptance_model.build_testmesh_plan()
        router_ids = {
            "acceptance_router_quality_gate_children",
            "acceptance_router_packet_tier",
            "acceptance_router_route_tier",
            "acceptance_router_terminal_tier",
            "acceptance_router_release_tiers",
        }
        evidence: dict[str, dict[str, object]] = {}
        for suite in declared.child_suites:
            if suite.suite_id in router_ids:
                continue
            artifact = root / f"{suite.suite_id}.result.json"
            artifact.write_text(
                json.dumps({"suite_id": suite.suite_id, "status": "passed"}, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            fingerprint = hashlib.sha256(artifact.read_bytes()).hexdigest()
            covered_obligation_ids = evidence_truth.testmesh_receipt_obligation_ids(
                declared,
                suite,
            )
            proof = {
                "artifact_id": f"proof.{suite.suite_id}",
                "producer_route": "flowguard-test-mesh-test-fixture",
                "command": suite.command,
                "result_path": str(artifact),
                "result_status": "passed",
                "exit_code": 0,
                "artifact_fingerprints": {str(artifact): fingerprint},
                "covered_obligation_ids": list(covered_obligation_ids),
                "assertion_scope": "external_contract",
                "current": True,
                "route_evidence_current": True,
            }
            evidence[suite.suite_id] = {
                "result_status": "passed",
                "evidence_tier": "external_contract",
                "evidence_current": True,
                "test_count": 1,
                "selected_count": 1,
                "exit_code": 0,
                "result_path": str(artifact),
                "has_exit_artifact": True,
                "has_result_artifact": True,
                "proof_artifact": proof,
                **evidence_truth.testmesh_final_receipt_fields(
                    proof,
                    covered_obligation_ids=covered_obligation_ids,
                ),
            }
        return evidence

    def release_proof(self, root: Path) -> dict[str, object]:
        artifact = root / "release.result.json"
        artifact.write_text('{"status":"passed"}\n', encoding="utf-8")
        return {
            "artifact_id": "proof.acceptance_router_release_tiers",
            "producer_route": "flowguard-test-mesh-test-fixture",
            "command": "python scripts/run_test_tier.py --tier release --background",
            "result_path": str(artifact),
            "result_status": "passed",
            "exit_code": 0,
            "artifact_fingerprints": {str(artifact): hashlib.sha256(artifact.read_bytes()).hexdigest()},
            "covered_obligation_ids": list(acceptance_model.RELEASE_EVIDENCE_CELLS),
            "assertion_scope": "external_contract",
            "current": True,
            "route_evidence_current": True,
        }

    def write_background_artifacts(
        self,
        root: Path,
        suite_id: str,
        *,
        failing_children: set[str] | None = None,
        running_children: set[str] | None = None,
        missing_children: set[str] | None = None,
    ) -> None:
        failing_children = failing_children or set()
        running_children = running_children or set()
        missing_children = missing_children or set()
        root.mkdir(parents=True, exist_ok=True)
        for old_artifact in root.glob("*"):
            if old_artifact.is_file():
                old_artifact.unlink()
        for name in acceptance_runner.BACKGROUND_CHILD_SUITES[suite_id]["expected"]:
            if name in missing_children:
                continue
            (root / f"{name}.combined.txt").write_text(f"{name} output\n", encoding="utf-8")
            (root / f"{name}.meta.json").write_text(
                json.dumps({"status": "running" if name in running_children else "finished", "duration_seconds": 1.0}),
                encoding="utf-8",
            )
            if name not in running_children:
                (root / f"{name}.exit.txt").write_text("1\n" if name in failing_children else "0\n", encoding="utf-8")

    def passed_router_background_dirs(self, root: Path) -> dict[str, Path]:
        dirs = {
            "router_quality_background_dir": root / "quality",
            "router_packets_background_dir": root / "packets",
            "router_route_background_dir": root / "route",
            "router_terminal_background_dir": root / "terminal",
        }
        suite_by_arg = {
            "router_quality_background_dir": "acceptance_router_quality_gate_children",
            "router_packets_background_dir": "acceptance_router_packet_tier",
            "router_route_background_dir": "acceptance_router_route_tier",
            "router_terminal_background_dir": "acceptance_router_terminal_tier",
        }
        for arg_name, suite_id in suite_by_arg.items():
            self.write_background_artifacts(dirs[arg_name], suite_id)
        return dirs

    def test_acceptance_testmesh_routine_gate_passes_without_hiding_release_gap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = acceptance_runner.run_checks(
                release_evidence=False,
                routine_evidence_overrides=self.current_routine_evidence(Path(tmp) / "routine"),
                **self.passed_router_background_dirs(Path(tmp)),
            )

        self.assertTrue(result["ok"], result)
        self.assertTrue(result["test_mesh"]["routine_gate"]["ok"])
        self.assertTrue(result["routine_router_gate"]["ok"])
        self.assertFalse(result["release_gate"]["ok"])
        self.assertEqual(result["missing_payload_cells"], [])
        self.assertEqual(result["release_gate"]["deferred_suites"][0]["suite_id"], "acceptance_router_release_tiers")
        self.assertEqual(result["release_gate"]["deferred_suites"][0]["status"], "not_run")

    def test_acceptance_testmesh_release_evidence_can_close_release_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = acceptance_runner.run_checks(
                release_evidence=True,
                routine_evidence_overrides=self.current_routine_evidence(Path(tmp) / "routine"),
                release_proof_artifact=self.release_proof(Path(tmp)),
                **self.passed_router_background_dirs(Path(tmp)),
            )

        self.assertTrue(result["ok"], result)
        self.assertTrue(result["release_gate"]["ok"])
        self.assertEqual(result["release_gate"]["deferred_suites"], [])

    def test_background_evidence_compiler_emits_current_fingerprinted_proofs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            all_root = root / "all"
            adversarial_root = root / "adversarial"
            release_root = root / "release"
            closure_root = root / "closure"
            self.write_tier_proof_root(all_root, "all")
            self.write_tier_proof_root(adversarial_root, "formal-submit-adversarial")
            self.write_tier_proof_root(release_root, "release")
            self.write_tier_proof_root(closure_root, "evidence-closure")

            manifest = evidence_compiler.compile_manifest(
                all_root=all_root,
                adversarial_root=adversarial_root,
                release_root=release_root,
                closure_root=closure_root,
            )
            strict_result = acceptance_runner.run_checks(
                release_evidence=True,
                release_background=True,
                routine_evidence_overrides=manifest["routine"],
                release_proof_artifact=manifest["release"]["proof_artifact"],
                release_test_count=manifest["release"]["test_count"],
                release_selected_count=manifest["release"]["selected_count"],
            )

        self.assertTrue(manifest["snapshot"]["fingerprint"])
        self.assertEqual(manifest["phase"], "final")
        self.assertEqual(
            manifest["schema_version"],
            evidence_compiler.MANIFEST_SCHEMA_VERSION,
        )
        self.assertEqual(
            set(manifest["routine"]),
            {
                suite.suite_id
                for suite in acceptance_model.build_testmesh_plan().child_suites
                if suite.suite_id != "acceptance_router_release_tiers"
            },
        )
        self.assertTrue(strict_result["ok"])
        self.assertTrue(strict_result["routine_router_gate"]["ok"])
        final_receipt_fields = {
            "run_id",
            "terminal_status",
            "result_fingerprint",
            "covered_obligation_ids",
            "artifact_version",
            "verifier_version",
        }
        for row in (*manifest["routine"].values(), manifest["release"]):
            self.assertTrue(final_receipt_fields.issubset(row), row)
            self.assertEqual(row["terminal_status"], "passed")
            self.assertTrue(row["result_fingerprint"])
            self.assertEqual(
                row["covered_obligation_ids"],
                row["proof_artifact"]["covered_obligation_ids"],
            )
            self.assertTrue(row["artifact_version"])
            self.assertIn("flowguard-testmesh/", row["verifier_version"])
        packet_proof = manifest["routine"]["acceptance_router_packet_tier"]
        self.assertEqual(
            packet_proof["test_count"],
            len(
                acceptance_runner.BACKGROUND_CHILD_SUITES[
                    "acceptance_router_packet_tier"
                ]["expected"]
            ),
        )
        self.assertTrue(
            manifest["routine"]["acceptance_contract_runtime_tests"]["proof_artifact"]["artifact_fingerprints"]
        )
        self.assertEqual(manifest["release"]["proof_artifact"]["result_status"], "passed")
        self.assertEqual(
            manifest["release"]["test_count"],
            manifest["release"]["proof_artifact"]["metadata"]["proof_backed_child_command_count"],
        )
        self.assertEqual(
            manifest["release"]["selected_count"],
            manifest["release"]["proof_artifact"]["metadata"]["selected_child_command_count"],
        )
        self.assertEqual(
            manifest["release"]["proof_artifact"]["metadata"]["covered_tiers"],
            ["all", "formal-submit-adversarial", "release", "evidence-closure"],
        )
        self.assertNotIn(
            "final-confidence",
            manifest["release"]["proof_artifact"]["metadata"]["covered_tiers"],
        )

    def test_owner_checkpoint_retains_current_rows_and_rejects_only_stale_owner(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            all_root = Path(tmp) / "all"
            self.write_tier_proof_root(all_root, "all")
            owner_index_path = background_supervisor.supervisor_control_paths(
                all_root,
                "all",
            )["owner_index"]
            owner_index = json.loads(
                owner_index_path.read_text(encoding="utf-8")
            )
            stale_owner_id = sorted(
                row["owner_id"] for row in owner_index["owners"]
            )[0]
            stale_meta_path = test_tier_runner.artifact_paths(
                all_root,
                stale_owner_id,
            )["meta"]
            stale_meta = json.loads(
                stale_meta_path.read_text(encoding="utf-8")
            )
            stale_meta["inputs_current"] = False
            stale_meta_path.write_text(
                json.dumps(stale_meta),
                encoding="utf-8",
            )

            manifest = evidence_compiler.compile_owner_checkpoint_manifest(
                all_root=all_root,
            )

        self.assertEqual(
            manifest["schema_version"],
            evidence_compiler.MANIFEST_SCHEMA_VERSION,
        )
        self.assertEqual(manifest["phase"], "checkpoint")
        self.assertEqual(manifest["claim_scope"], "owner_reuse_only")
        self.assertNotIn(stale_owner_id, manifest["owners"])
        self.assertEqual(
            set(manifest["rejected_owner_ids"]),
            {stale_owner_id},
        )
        self.assertEqual(
            manifest["source_supervisor"]["current_owner_count"],
            len(test_tier_runner.commands_for_tier("all")) - 1,
        )
        self.assertEqual(
            manifest["source_supervisor"]["rejected_owner_count"],
            1,
        )

    def test_owner_checkpoint_rejects_nonterminal_supervisor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            all_root = Path(tmp) / "all"
            self.write_tier_proof_root(all_root, "all")
            meta_path = all_root / "all_background_supervisor.meta.json"
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            meta["status"] = "running"
            meta["running"] = ["test_tier_runner"]
            meta_path.write_text(json.dumps(meta), encoding="utf-8")

            with self.assertRaisesRegex(
                ValueError,
                "not a terminal pass",
            ):
                evidence_compiler.compile_owner_checkpoint_manifest(
                    all_root=all_root,
                )

    def test_final_manifest_missing_receipt_fields_are_rejected_as_one_class(self) -> None:
        expected_codes = {
            "run_id": "final_receipt_run_id_missing",
            "terminal_status": "final_receipt_terminal_status_missing",
            "result_fingerprint": "final_receipt_result_fingerprint_missing",
            "covered_obligation_ids": "final_receipt_coverage_incomplete",
            "artifact_version": "final_receipt_artifact_version_missing",
            "verifier_version": "final_receipt_verifier_version_missing",
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            all_root = root / "all"
            adversarial_root = root / "adversarial"
            release_root = root / "release"
            closure_root = root / "closure"
            self.write_tier_proof_root(all_root, "all")
            self.write_tier_proof_root(adversarial_root, "formal-submit-adversarial")
            self.write_tier_proof_root(release_root, "release")
            self.write_tier_proof_root(closure_root, "evidence-closure")
            manifest = evidence_compiler.compile_manifest(
                all_root=all_root,
                adversarial_root=adversarial_root,
                release_root=release_root,
                closure_root=closure_root,
            )

            for field_name, expected_code in expected_codes.items():
                with self.subTest(field_name=field_name):
                    routine = {
                        suite_id: dict(row)
                        for suite_id, row in manifest["routine"].items()
                    }
                    routine["acceptance_complete_workstream_profiles"].pop(field_name)
                    result = acceptance_runner.run_checks(
                        release_evidence=False,
                        routine_evidence_overrides=routine,
                    )
                    finding_codes = {
                        finding["code"] for finding in result["report"]["findings"]
                    }
                    self.assertFalse(result["ok"])
                    self.assertIn(expected_code, finding_codes)

    def test_background_evidence_compiler_does_not_persist_machine_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            all_root = root / "all"
            adversarial_root = root / "adversarial"
            release_root = root / "release"
            closure_root = root / "closure"
            self.write_tier_proof_root(all_root, "all")
            self.write_tier_proof_root(adversarial_root, "formal-submit-adversarial")
            self.write_tier_proof_root(release_root, "release")
            self.write_tier_proof_root(closure_root, "evidence-closure")

            manifest = evidence_compiler.compile_manifest(
                all_root=all_root.resolve(),
                adversarial_root=adversarial_root.resolve(),
                release_root=release_root.resolve(),
                closure_root=closure_root.resolve(),
            )
            serialized = json.dumps(manifest, sort_keys=True)

        self.assertNotIn(str(root.resolve()), serialized)
        self.assertNotIn("\\\\Users\\\\", serialized)
        self.assertIn("<external>/all", serialized)
        self.assertIn("<external>/adversarial", serialized)
        self.assertIn("<external>/release", serialized)
        self.assertIn("<external>/closure", serialized)

    def test_direct_background_overrides_do_not_persist_machine_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = acceptance_runner.run_checks(
                release_evidence=False,
                **self.passed_router_background_dirs(root),
            )
            serialized = json.dumps(result, sort_keys=True)

        self.assertNotIn(str(root.resolve()), serialized)
        self.assertNotIn("\\\\Users\\\\", serialized)
        self.assertIn("<external>/quality", serialized)
        self.assertIn("<external>/packets", serialized)
        self.assertIn("<external>/route", serialized)
        self.assertIn("<external>/terminal", serialized)

    def test_background_evidence_compiler_rejects_owner_input_changed_during_tier(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            all_root = root / "all"
            adversarial_root = root / "adversarial"
            release_root = root / "release"
            closure_root = root / "closure"
            self.write_tier_proof_root(all_root, "all")
            self.write_tier_proof_root(adversarial_root, "formal-submit-adversarial")
            self.write_tier_proof_root(release_root, "release")
            self.write_tier_proof_root(closure_root, "evidence-closure")
            owner_index_path = background_supervisor.supervisor_control_paths(
                all_root,
                "all",
            )["owner_index"]
            owner_index = json.loads(
                owner_index_path.read_text(encoding="utf-8")
            )
            owner_id = sorted(
                row["owner_id"] for row in owner_index["owners"]
            )[0]
            child_meta_path = test_tier_runner.artifact_paths(
                all_root,
                owner_id,
            )["meta"]
            child_meta = json.loads(
                child_meta_path.read_text(encoding="utf-8")
            )
            child_meta["inputs_current"] = False
            child_meta_path.write_text(
                json.dumps(child_meta),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "current owner evidence is invalid"):
                evidence_compiler.compile_manifest(
                    all_root=all_root,
                    adversarial_root=adversarial_root,
                    release_root=release_root,
                    closure_root=closure_root,
                )

    def test_background_evidence_compiler_rejects_missing_router_child(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            all_root = root / "all"
            adversarial_root = root / "adversarial"
            release_root = root / "release"
            closure_root = root / "closure"
            self.write_tier_proof_root(all_root, "all")
            self.write_tier_proof_root(adversarial_root, "formal-submit-adversarial")
            self.write_tier_proof_root(release_root, "release")
            self.write_tier_proof_root(closure_root, "evidence-closure")
            (all_root / "router_packets_generic_ack_mail.meta.json").unlink()
            (all_root / "router_packets_generic_ack_mail.exit.txt").unlink()

            with self.assertRaisesRegex(
                ValueError,
                "current owner evidence is invalid",
            ):
                evidence_compiler.compile_manifest(
                    all_root=all_root,
                    adversarial_root=adversarial_root,
                    release_root=release_root,
                    closure_root=closure_root,
                )

    def test_missing_router_background_artifacts_block_broad_routine_gate(self) -> None:
        result = acceptance_runner.run_checks(release_evidence=False)

        self.assertFalse(result["ok"])
        self.assertFalse(result["routine_router_gate"]["ok"])
        self.assertEqual(
            {
                "acceptance_router_quality_gate_children",
                "acceptance_router_packet_tier",
                "acceptance_router_route_tier",
                "acceptance_router_terminal_tier",
            },
            {item["suite_id"] for item in result["routine_router_gate"]["nonpassing_suites"]},
        )
        for item in result["routine_router_gate"]["nonpassing_suites"]:
            self.assertIn("not_current", item["nonpass_reasons"])

    def test_required_payload_cells_are_owned_by_current_child_suites(self) -> None:
        plan = acceptance_model.build_testmesh_plan()
        owners = acceptance_model.payload_cell_owners(plan)

        self.assertEqual(set(acceptance_model.PAYLOAD_CELLS), set(owners))
        for cell_id in acceptance_model.PAYLOAD_CELLS:
            with self.subTest(cell_id=cell_id):
                self.assertTrue(owners[cell_id], cell_id)

    def test_final_review_reject_repair_loop_is_a_required_payload_cell(self) -> None:
        plan = acceptance_model.build_testmesh_plan()
        owners = acceptance_model.payload_cell_owners(plan)

        self.assertIn("terminal_replay_reject_repair_rerun_closure", acceptance_model.PAYLOAD_CELLS)
        self.assertEqual(
            set(owners["terminal_replay_reject_repair_rerun_closure"]),
            {"acceptance_fake_ai_payload_chaos", "acceptance_terminal_replay_payloads"},
        )
        self.assertIn(
            "final_review_repair_return",
            {item.item_id for item in plan.partition_items},
        )

    def test_terminal_supplemental_repair_cells_are_required_and_owned(self) -> None:
        plan = acceptance_model.build_testmesh_plan()
        owners = acceptance_model.payload_cell_owners(plan)

        expected_cells = {
            "terminal_supplemental_contract_missing",
            "terminal_supplemental_contract_corrected_recovery",
            "terminal_supplemental_fake_ai_current_checklist_recovery",
            "terminal_supplemental_final_ledger_projection",
            "terminal_supplemental_round_cap_exhaustion",
            "terminal_hygiene_review_required",
            "terminal_hygiene_required_gap_blocks",
            "terminal_hygiene_supplemental_contract",
            "terminal_hygiene_final_ledger_projection",
        }
        self.assertTrue(expected_cells.issubset(set(acceptance_model.PAYLOAD_CELLS)))
        for cell_id in expected_cells:
            with self.subTest(cell_id=cell_id):
                self.assertIn("acceptance_terminal_supplemental_repair", set(owners[cell_id]))
        self.assertIn(
            "terminal_supplemental_repair_tail",
            {item.item_id for item in plan.partition_items},
        )

    def test_ai_contract_projection_cells_are_required_and_owned(self) -> None:
        plan = acceptance_model.build_testmesh_plan()
        owners = acceptance_model.payload_cell_owners(plan)

        projection_cells = {
            "ai_contract_semantic_recheck_profile_projection",
            "ai_contract_semantic_recheck_allowed_options_projection",
            "ai_contract_all_result_allowed_options_projection",
            "ai_contract_profile_required_fields_and_types_projection",
        }
        fake_ai_cells = {
            "ai_contract_semantic_recheck_forbidden_alias_feedback",
            "ai_contract_semantic_recheck_wrong_value_corrected_retry",
            "ai_contract_all_result_allowed_options_wrong_value",
            "ai_contract_profile_forbidden_alias_feedback",
        }
        self.assertTrue((projection_cells | fake_ai_cells).issubset(set(acceptance_model.PAYLOAD_CELLS)))
        for cell_id in projection_cells:
            with self.subTest(cell_id=cell_id):
                self.assertIn("acceptance_contract_runtime_tests", set(owners[cell_id]))
        for cell_id in fake_ai_cells:
            with self.subTest(cell_id=cell_id):
                self.assertIn("acceptance_fake_ai_payload_chaos", set(owners[cell_id]))
        self.assertIn(
            "ai_contract_projection_and_retry",
            {item.item_id for item in plan.partition_items},
        )

    def test_integration_cartesian_cells_are_required_and_owned(self) -> None:
        plan = acceptance_model.build_testmesh_plan()
        owners = acceptance_model.payload_cell_owners(plan)

        integration_cells = {
            "integration_cartesian_hard_underblock",
            "integration_cartesian_advisory_overblock",
            "integration_cartesian_worker_boundary",
            "integration_cartesian_runtime_no_hard_blocker",
            "integration_cartesian_model_miss",
        }
        self.assertTrue(integration_cells.issubset(set(acceptance_model.PAYLOAD_CELLS)))
        for cell_id in integration_cells:
            with self.subTest(cell_id=cell_id):
                self.assertEqual(set(owners[cell_id]), {"acceptance_integration_cartesian_coverage"})
        self.assertIn(
            "integration_cartesian_coverage",
            {item.item_id for item in plan.partition_items},
        )

    def test_release_child_progress_only_or_not_run_is_not_a_pass(self) -> None:
        routine = acceptance_runner.run_checks(release_evidence=False)
        release_rows = [
            row
            for row in routine["test_mesh"]["rows"]
            if row["id"] == "acceptance_router_release_tiers"
        ]

        self.assertEqual(len(release_rows), 1)
        self.assertEqual(release_rows[0]["status"], "not_run")
        self.assertIn("not_run", release_rows[0]["nonpass_reasons"])
        self.assertFalse(routine["release_gate"]["ok"])

    def test_release_child_progress_timeout_or_stale_pass_is_not_release_evidence(self) -> None:
        cases = (
            {
                "name": "progress_only",
                "kwargs": {
                    "release_evidence": True,
                    "release_result_status": "progress_only",
                    "release_progress_only": True,
                    "release_background": True,
                    "release_has_exit_artifact": False,
                    "release_has_result_artifact": False,
                },
                "expected": {"progress_only", "missing_exit_artifact", "missing_result_artifact"},
            },
            {
                "name": "timeout",
                "kwargs": {
                    "release_evidence": False,
                    "release_result_status": "timeout",
                    "release_timeout_seconds": 30.0,
                    "release_background": True,
                },
                "expected": {"timeout", "not_current"},
            },
            {
                "name": "stale_pass",
                "kwargs": {
                    "release_evidence": True,
                    "release_result_status": "passed",
                    "release_evidence_current": False,
                    "release_stale_reasons": ("source_changed_after_result",),
                },
                "expected": {"not_current", "stale:source_changed_after_result"},
            },
        )

        for case in cases:
            with self.subTest(case=case["name"]):
                with tempfile.TemporaryDirectory() as tmp:
                    result = acceptance_runner.run_checks(
                        **case["kwargs"],
                        **self.passed_router_background_dirs(Path(tmp)),
                    )
                row = [
                    item
                    for item in result["test_mesh"]["rows"]
                    if item["id"] == "acceptance_router_release_tiers"
                ][0]

                self.assertFalse(result["release_gate"]["ok"])
                self.assertTrue(case["expected"].issubset(set(row["nonpass_reasons"])))

    def test_background_router_packet_failure_blocks_routine_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dirs = self.passed_router_background_dirs(Path(tmp))
            self.write_background_artifacts(
                dirs["router_packets_background_dir"],
                "acceptance_router_packet_tier",
                failing_children={"router_packet_runtime"},
            )
            result = acceptance_runner.run_checks(release_evidence=False, **dirs)

        self.assertFalse(result["ok"])
        self.assertFalse(result["routine_router_gate"]["ok"])
        packet = [
            item
            for item in result["routine_router_gate"]["nonpassing_suites"]
            if item["suite_id"] == "acceptance_router_packet_tier"
        ][0]
        self.assertIn("failed", packet["nonpass_reasons"])
        details = [
            item
            for item in result["router_tier_background_details"]
            if item["suite_id"] == "acceptance_router_packet_tier"
        ][0]
        self.assertEqual(details["failed_children"], ["router_packet_runtime"])

    def test_background_progress_without_exit_blocks_routine_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dirs = self.passed_router_background_dirs(Path(tmp))
            self.write_background_artifacts(
                dirs["router_quality_background_dir"],
                "acceptance_router_quality_gate_children",
                running_children={"router_quality_gates_route_draft_product_model"},
            )
            result = acceptance_runner.run_checks(release_evidence=False, **dirs)

        self.assertFalse(result["ok"])
        quality = [
            item
            for item in result["routine_router_gate"]["nonpassing_suites"]
            if item["suite_id"] == "acceptance_router_quality_gate_children"
        ][0]
        self.assertIn("progress_only", quality["nonpass_reasons"])
        self.assertIn("missing_exit_artifact", quality["nonpass_reasons"])

    def test_acceptance_testmesh_exposes_required_router_tier_mapping(self) -> None:
        result = acceptance_runner.run_checks()
        tiers = {item["tier"]: item for item in result["router_tier_mappings"]}

        self.assertEqual(
            {
                "router-quality-gates",
                "router-packets",
                "router-route",
                "router-terminal",
                "integration",
                "release",
            },
            set(tiers),
        )
        self.assertEqual(tiers["router-terminal"]["risk"], "terminal replay segment targets and final-review repair-return loop")
        self.assertNotIn("final-confidence", tiers)

    def test_router_packet_child_suite_matches_current_tier_exactly(self) -> None:
        expected = acceptance_runner.BACKGROUND_CHILD_SUITES[
            "acceptance_router_packet_tier"
        ]["expected"]
        actual = tuple(
            command.name
            for command in test_tier_runner.commands_for_tier("router-packets")
        )

        self.assertEqual(expected, actual)
        self.assertNotIn("router_packets_material", expected)

    def test_upstream_release_evidence_cells_are_release_owned(self) -> None:
        plan = acceptance_model.build_testmesh_plan()
        owners = acceptance_model.release_evidence_cell_owners(plan)

        expected_cells = {
            "all_tier_complete",
            "formal_submit_adversarial_tier_complete",
            "release_tier_complete",
        }
        self.assertEqual(expected_cells, set(acceptance_model.RELEASE_EVIDENCE_CELLS))
        for cell_id in expected_cells:
            with self.subTest(cell_id=cell_id):
                self.assertEqual(set(owners[cell_id]), {"acceptance_router_release_tiers"})
        self.assertNotIn("formal_exit_authority", {item.item_id for item in plan.partition_items})
        result = acceptance_runner.run_checks()
        self.assertEqual(expected_cells, set(result["release_evidence_cells"]))
        for cell_id in expected_cells:
            self.assertEqual(
                result["release_evidence_cell_owners"][cell_id],
                ["acceptance_router_release_tiers"],
            )


if __name__ == "__main__":
    unittest.main()
