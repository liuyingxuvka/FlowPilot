from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_KIT = ROOT / "skills" / "flowpilot" / "assets" / "runtime_kit"


def normalized(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").lower().split())


class FlowPilotFlowGuardWorkOrderMeshTests(unittest.TestCase):
    def test_flowguard_operator_answers_work_order_without_becoming_reviewer(self) -> None:
        flowguard = normalized(RUNTIME_KIT / "cards" / "roles" / "flowguard_operator.md")
        pm_repair = normalized(RUNTIME_KIT / "cards" / "phases" / "pm_review_repair.md")

        for term in (
            "answer only that work order and its named check items",
            "do not take over the reviewer's quality judgement",
            "product quality, prose quality, final-user usefulness, or artifact standard",
            "pm decides the repair path",
        ):
            self.assertIn(term, flowguard)

        for term in (
            "name the blocker id",
            "required semantic focus",
            "a flowguard report that only checks result shape",
            "cannot close a subject-bound reviewer blocker",
        ):
            self.assertIn(term, pm_repair)


if __name__ == "__main__":
    unittest.main()
