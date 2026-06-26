from __future__ import annotations

import sys
import tempfile
import unittest
import hashlib
import json
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "flowpilot" / "assets"))

import flowpilot_router_terminal_ledger_flowguard_coverage as coverage  # noqa: E402
import flowpilot_router_terminal_ledger_source_entries as source_entries  # noqa: E402
import flowpilot_router_terminal_ledger_traceability as traceability  # noqa: E402
import flowpilot_router_terminal_ledger_writer as ledger_writer  # noqa: E402


def _dummy_router() -> ModuleType:
    router = ModuleType("terminal_source_entry_test_router")

    def project_relative(project_root: Path, path: Path) -> str:
        return str(Path(path).relative_to(project_root)).replace("\\", "/")

    def read_json(path: Path) -> dict:
        return json.loads(Path(path).read_text(encoding="utf-8"))

    def string_list(value):
        if not isinstance(value, list):
            return []
        return [str(item) for item in value if str(item or "").strip()]

    router.project_relative = project_relative  # type: ignore[attr-defined]
    router.read_json = read_json  # type: ignore[attr-defined]
    router._string_list = string_list  # type: ignore[attr-defined]
    router._effective_route_nodes = lambda route, mutations: route.get("nodes", [])  # type: ignore[attr-defined]
    router._route_mutation_superseded_nodes = lambda item: item.get("superseded_node_ids", [])  # type: ignore[attr-defined]
    return router


class TerminalLedgerSourceEntryTests(unittest.TestCase):
    def test_terminal_source_entry_helpers_remain_available_on_traceability_facade(self) -> None:
        router = _dummy_router()

        for name in (
            "_root_requirement_ids",
            "_string_list",
            "_route_nodes_with_requirement_trace",
            "_requirement_trace_closure_from_root_replay",
            "_build_source_of_truth_final_entries",
        ):
            self.assertIn(name, traceability.__all__)
            self.assertTrue(callable(getattr(traceability, name)))
        self.assertEqual(
            traceability._root_requirement_ids(
                router,
                {"root_requirements": [{"requirement_id": "root-001"}]},
            ),
            ["root-001"],
        )

    def test_terminal_source_entry_child_builds_expected_gate_families(self) -> None:
        router = _dummy_router()
        traced_nodes = source_entries._route_nodes_with_requirement_trace(
            router,
            [{"id": "node-a"}],
            ["root-001"],
        )
        closure = source_entries._requirement_trace_closure_from_root_replay(
            router,
            {
                "root_requirements": [
                    {
                        "requirement_id": "root-001",
                        "source_requirement_ids": ["source-1"],
                    }
                ]
            },
            [{"requirement_id": "root-001", "evidence_paths": ["evidence/root.json"]}],
        )
        with tempfile.TemporaryDirectory(prefix="flowpilot-terminal-source-entries-") as tmp:
            project_root = Path(tmp)
            run_root = project_root / ".flowpilot" / "runs" / "run-test"
            node_root = run_root / "routes" / "route-001" / "nodes" / "node-001"
            (node_root / "reviews").mkdir(parents=True)
            (node_root / "node_acceptance_plan.json").write_text("{}", encoding="utf-8")
            (node_root / "reviews" / "node_acceptance_plan_review.json").write_text("{}", encoding="utf-8")
            mutations_path = run_root / "routes" / "route-001" / "mutations.json"
            mutations_path.parent.mkdir(parents=True, exist_ok=True)
            mutations_path.write_text("{}", encoding="utf-8")
            (run_root / "child_skill_gate_manifest.json").write_text("{}", encoding="utf-8")

            frontier = {
                "active_route_id": "route-001",
                "active_node_id": "node-002",
                "completed_nodes": ["node-001"],
                "route_version": 3,
            }
            route = {
                "nodes": [
                    {
                        "node_id": "node-001",
                        "covers_requirement_ids": ["root-001"],
                        "covers_scenario_ids": ["scenario-a"],
                    }
                ]
            }
            mutations = {"items": [{"route_version": 2, "superseded_node_ids": ["node-old"]}]}
            root_replay = [
                {
                    "requirement_id": "root-001",
                    "standard_scenarios": ["scenario-a"],
                    "evidence_paths": [".flowpilot/runs/run-test/root_acceptance_contract.json"],
                }
            ]
            child_manifest = {
                "selected_skills": [
                    {
                        "skill_name": "reviewer",
                        "gates": [{"gate_id": "review", "required_approver": "human_like_reviewer"}],
                    }
                ]
            }
            evidence_ledger = {"items": [{"evidence_id": "ev-1", "path": "evidence/ev-1.json"}]}
            generated_ledger = {
                "resources": [
                    {"resource_id": "artifact-1", "path": "artifacts/a.txt", "disposition": "resolved"}
                ]
            }

            entries = source_entries._build_source_of_truth_final_entries(
                router,
                project_root,
                run_root,
                frontier,
                route,
                mutations,
                {"root_requirements": [{"requirement_id": "root-001"}]},
                root_replay,
                child_manifest,
                evidence_ledger,
                generated_ledger,
            )

        by_family = {entry["gate_family"]: entry for entry in entries}
        self.assertIn("root_acceptance", by_family)
        self.assertIn("route_node", by_family)
        self.assertIn("superseded_node", by_family)
        self.assertIn("child_skill_gate", by_family)
        self.assertIn("evidence_integrity", by_family)
        self.assertIn("generated_resource_lineage", by_family)
        self.assertEqual(by_family["route_node"]["status"], "approved")
        self.assertEqual(
            by_family["route_node"]["source_of_truth_paths"],
            [
                ".flowpilot/runs/run-test/routes/route-001/nodes/node-001/node_acceptance_plan.json",
                ".flowpilot/runs/run-test/routes/route-001/nodes/node-001/reviews/node_acceptance_plan_review.json",
            ],
        )
        self.assertEqual(
            by_family["route_node"]["evidence_paths"],
            by_family["route_node"]["source_of_truth_paths"],
        )
        self.assertEqual(traced_nodes[0]["node_id"], "node-a")
        self.assertEqual(traced_nodes[0]["covers_requirement_ids"], ["root-001"])
        self.assertEqual(closure[0]["status"], "resolved")
        self.assertEqual(closure[0]["source_requirement_ids"], ["source-1"])
        self.assertTrue(closure[0]["direct_evidence_checked"])

    def test_terminal_flowguard_coverage_child_validates_current_report(self) -> None:
        router = _dummy_router()
        with tempfile.TemporaryDirectory(prefix="flowpilot-terminal-coverage-") as tmp:
            project_root = Path(tmp)
            run_root = project_root / ".flowpilot" / "runs" / "run-test"
            report_path = run_root / "flowguard" / "terminal_coverage_report.json"
            matrix_path = run_root / "flowguard" / "terminal_coverage_matrix.json"
            report_path.parent.mkdir(parents=True)
            matrix_path.write_text("{}", encoding="utf-8")
            report = {
                "schema_version": coverage.FLOWGUARD_TERMINAL_COVERAGE_SCHEMA,
                "reviewed_by_role": "flowguard_operator",
                "passed": True,
                "modeled_boundary": coverage.FLOWGUARD_TERMINAL_COVERAGE_BOUNDARY,
                "route_version": 7,
                "progress_only": False,
                "coverage_matrix_ref": {
                    "path": ".flowpilot/runs/run-test/flowguard/terminal_coverage_matrix.json",
                    "fresh": True,
                    "route_version": 7,
                },
                "acceptance_item_closure": ["root"],
                "route_nodes_examined": ["node"],
                "flowguard_required_items": ["terminal"],
                "flowguard_evidence_found": ["evidence"],
                "commands_run": ["python simulations/run_flowpilot_terminal_flowguard_coverage_checks.py"],
                "hard_invariants": ["no blockers"],
                "counterexamples_or_absence": ["none"],
                "missing_or_stale_evidence": [],
                "model_test_alignment_gaps": [],
                "blockers": [],
                "pm_suggestion_items": [],
                "supplemental_repair_recommendations": [],
                "confidence_boundary": "terminal coverage report for active route",
                "contract_self_check": {
                    "all_required_fields_present": True,
                    "no_progress_only_claim": True,
                    "no_unresolved_blockers": True,
                    "pm_acceptance_required": True,
                },
            }
            report_path.write_text(json.dumps(report), encoding="utf-8")
            payload = {
                "status": "accepted",
                "accepted_by_role": "project_manager",
                "route_version": 7,
                "current": True,
                "blockers_resolved": True,
                "pm_suggestion_items_disposed": True,
                "report_path": ".flowpilot/runs/run-test/flowguard/terminal_coverage_report.json",
                "coverage_matrix_path": ".flowpilot/runs/run-test/flowguard/terminal_coverage_matrix.json",
                "report_hash": hashlib.sha256(report_path.read_bytes()).hexdigest(),
            }

            status = coverage._validated_flowguard_terminal_coverage_status(
                router,
                project_root,
                run_root,
                7,
                payload,
            )

        self.assertEqual(status["segment_id"], coverage.FLOWGUARD_TERMINAL_COVERAGE_SEGMENT_ID)
        self.assertEqual(status["report_path"], ".flowpilot/runs/run-test/flowguard/terminal_coverage_report.json")
        self.assertEqual(status["coverage_matrix_path"], ".flowpilot/runs/run-test/flowguard/terminal_coverage_matrix.json")
        self.assertTrue(
            callable(coverage._flowguard_terminal_coverage_ledger_entry),
            "flowguard coverage child should keep direct ledger-entry contract",
        )

    def test_terminal_writer_child_remains_facade_exported(self) -> None:
        self.assertIn("_write_final_route_wide_ledger", traceability.__all__)
        self.assertIn("_write_final_route_wide_ledger", ledger_writer.__all__)
        self.assertTrue(callable(traceability._write_final_route_wide_ledger))
        self.assertTrue(callable(ledger_writer._write_final_route_wide_ledger))

    def test_terminal_source_entry_child_projects_requirement_trace_defaults(self) -> None:
        router = _dummy_router()
        nodes = source_entries._route_nodes_with_requirement_trace(
            router,
            [{"id": "node-a"}],
            ["root-001"],
        )
        closure = source_entries._requirement_trace_closure_from_root_replay(
            router,
            {
                "root_requirements": [
                    {
                        "requirement_id": "root-001",
                        "source_requirement_ids": ["source-1"],
                    }
                ]
            },
            [{"requirement_id": "root-001", "evidence_paths": ["evidence/root.json"]}],
        )

        self.assertEqual(nodes[0]["node_id"], "node-a")
        self.assertEqual(nodes[0]["covers_requirement_ids"], ["root-001"])
        self.assertEqual(closure[0]["status"], "resolved")
        self.assertEqual(closure[0]["source_requirement_ids"], ["source-1"])
        self.assertTrue(closure[0]["direct_evidence_checked"])


if __name__ == "__main__":
    unittest.main()
