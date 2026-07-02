from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_KIT = ROOT / "skills" / "flowpilot" / "assets" / "runtime_kit"


def normalized(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").lower().split())


class FlowPilotSemanticBlockerMeshTests(unittest.TestCase):
    def test_pm_worker_reviewer_prompt_mesh_keeps_blockers_itemized_and_rechecked(self) -> None:
        surfaces = {
            "pm_repair": normalized(RUNTIME_KIT / "cards" / "phases" / "pm_review_repair.md"),
            "worker": normalized(RUNTIME_KIT / "cards" / "roles" / "worker.md"),
            "reviewer": normalized(RUNTIME_KIT / "cards" / "roles" / "human_like_reviewer.md"),
        }
        required_terms = {
            "pm_repair": (
                "prior blocker id",
                "exact itemized repair required now",
                "same review/check gate that must re-run",
                "required/delivered/gap",
            ),
            "worker": (
                "answer the concrete repair obligations item by item",
                "each named repair item is now satisfied",
                "not a repair result",
            ),
            "reviewer": (
                "existence evidence is not enough",
                "block with a `final_blockers[]` row",
                "user's original intent",
            ),
        }

        for surface, terms in required_terms.items():
            with self.subTest(surface=surface):
                for term in terms:
                    self.assertIn(term, surfaces[surface])


if __name__ == "__main__":
    unittest.main()
