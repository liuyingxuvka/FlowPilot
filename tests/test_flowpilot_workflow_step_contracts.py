from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    old_path = list(sys.path)
    old_module = sys.modules.get(name)
    sys.modules[name] = module
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = old_path
        if old_module is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = old_module
    return module


contracts = load_module(
    "flowpilot_test_workflow_step_contracts",
    ROOT / "simulations" / "flowpilot_workflow_step_contracts.py",
)
runner = load_module(
    "flowpilot_test_run_workflow_step_contract_checks",
    ROOT / "simulations" / "run_flowpilot_workflow_step_contract_checks.py",
)


class FlowPilotWorkflowStepContractTests(unittest.TestCase):
    def test_controller_receipt_projection_blocks_apply_path_confusion(self) -> None:
        projection = contracts.workflow_step_contracts_for_action(runner._controller_receipt_action())
        self.assertEqual(len(projection.contracts), 1)
        contract = projection.contracts[0]

        self.assertIn(projection.issued_receipt, contract.requires_receipts)
        self.assertIn(projection.completion_receipt, contract.produces_receipts)
        metadata = dict(contract.metadata)
        self.assertEqual(metadata["controller_completion_command"], "controller-receipt")
        self.assertFalse(metadata["apply_required"])
        self.assertIn("controller_row_complete", contract.required_for_claims[0])

    def test_missing_prerequisite_and_forbidden_skip_are_rejected(self) -> None:
        projection = contracts.workflow_step_contracts_for_action(runner._controller_receipt_action())
        contract = projection.contracts[0]

        missing_prereq = contracts.review_trace(
            (contracts.trace_step(contract.completion_labels[0]),),
            projection.contracts,
        )
        forbidden_skip = contracts.review_trace(
            (contracts.trace_step("skip", skipped=(contract.step_id,)),),
            projection.contracts,
        )

        self.assertFalse(missing_prereq.ok)
        self.assertIn("missing_prerequisite_receipt", {finding.code for finding in missing_prereq.findings})
        self.assertFalse(forbidden_skip.ok)
        self.assertIn("forbidden_step_skipped", {finding.code for finding in forbidden_skip.findings})

    def test_ack_read_receipt_does_not_complete_target_work(self) -> None:
        projection = contracts.workflow_step_contracts_for_action(runner._ack_only_action())
        self.assertEqual(len(projection.contracts), 2)
        ack_contract, work_contract = projection.contracts

        ack_only_claim = contracts.review_trace(
            (
                contracts.trace_step("router_action_issued", produced=(projection.issued_receipt,)),
                contracts.trace_step(ack_contract.completion_labels[0]),
                contracts.trace_step("claim", claims=(work_contract.required_for_claims[0],)),
            ),
            projection.contracts,
        )
        complete_claim = contracts.review_trace(
            (
                contracts.trace_step("router_action_issued", produced=(projection.issued_receipt,)),
                contracts.trace_step(ack_contract.completion_labels[0]),
                contracts.trace_step(work_contract.completion_labels[0]),
                contracts.trace_step("claim", claims=(work_contract.required_for_claims[0],)),
            ),
            projection.contracts,
        )

        self.assertFalse(ack_only_claim.ok)
        self.assertIn("missing_claim_receipt", {finding.code for finding in ack_only_claim.findings})
        self.assertTrue(complete_claim.ok, complete_claim.to_dict())

    def test_stale_ack_receipt_cannot_unlock_work_output(self) -> None:
        projection = contracts.workflow_step_contracts_for_action(runner._ack_only_action())
        ack_contract, work_contract = projection.contracts

        stale_ack = contracts.review_trace(
            (
                contracts.trace_step("router_action_issued", produced=(projection.issued_receipt,)),
                contracts.trace_step(ack_contract.completion_labels[0]),
                contracts.trace_step("invalidate_ack", invalidated=(projection.completion_receipt,)),
                contracts.trace_step(work_contract.completion_labels[0]),
            ),
            projection.contracts,
        )

        self.assertFalse(stale_ack.ok)
        self.assertIn("missing_prerequisite_receipt", {finding.code for finding in stale_ack.findings})

    def test_flowguard_workflow_step_runner_passes_known_good_and_known_bad(self) -> None:
        report = runner.build_report()

        self.assertTrue(report["ok"], report)
        self.assertIn("controller_receipt", report["reports"])
        self.assertIn("ack_separation", report["reports"])


if __name__ == "__main__":
    unittest.main()
