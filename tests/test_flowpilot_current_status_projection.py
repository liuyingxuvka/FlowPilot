from __future__ import annotations

from simulations import flowpilot_current_status_projection_model as model
from simulations import run_flowpilot_current_status_projection_checks as runner


def test_current_status_projection_cartesian_matrix_is_complete() -> None:
    report = model.matrix_report()

    assert report["ok"]
    assert report["full_product_count"] == (
        len(model.AUTHORITY_STATES)
        * len(model.BLOCKER_LIFECYCLES)
        * len(model.NODE_CLOSURE_LIFECYCLES)
        * len(model.REPAIR_DOSSIER_LIFECYCLES)
        * len(model.PROJECTION_SURFACE_BEHAVIORS)
    )
    assert report["negative_cell_count"] > 0
    assert "projection_used_historical_or_fallback_authority" in report["by_failure"]


def test_current_status_projection_flowguard_runner_passes() -> None:
    report = runner.run_checks()

    assert report["ok"]
    assert report["matrix"]["ok"]
    assert report["walk"]["ok"]
    assert report["flowguard"]["ok"]
    assert report["hazards"]["ok"]
