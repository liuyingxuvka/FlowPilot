"""Focused checks for FlowPilot information-flow alignment evidence."""

from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SIMULATIONS = ROOT / "simulations"
ASSETS = ROOT / "skills" / "flowpilot" / "assets"
if str(ASSETS) not in sys.path:
    sys.path.insert(0, str(ASSETS))
if str(SIMULATIONS) not in sys.path:
    sys.path.insert(0, str(SIMULATIONS))

from flowpilot_router_errors import RouterError  # noqa: E402
from flowpilot_router_work_packets_pm_role_writes_decisions_role_result import (  # noqa: E402
    _validate_result_bodies_opened_by_pm,
)
import run_flowpilot_information_flow_alignment_checks as information_flow_alignment  # noqa: E402


def test_information_flow_alignment_has_no_unbound_obligations() -> None:
    report = information_flow_alignment.build_report()

    assert report["ok"], report["findings"]
    assert report["obligation_count"] == 14
    assert report["alignment_ok"]
    assert report["marker_ok"]
    assert report["code_symbol_ok"]
    assert report["underlying_model_ok"]


def test_pm_result_disposition_requires_opened_result_body(tmp_path: Path) -> None:
    project_root = tmp_path
    result_path = (
        project_root
        / ".flowpilot"
        / "runs"
        / "run-test"
        / "packets"
        / "packet-1"
        / "result_envelope.json"
    )
    result_path.parent.mkdir(parents=True)
    result_path.write_text(
        json.dumps(
            {
                "packet_id": "packet-1",
                "result_body_opened_by_role": {
                    "role": "project_manager",
                    "body_hash_verified": True,
                },
            }
        ),
        encoding="utf-8",
    )
    relative_result_path = result_path.relative_to(project_root)
    fake_router = SimpleNamespace(
        _result_envelope_path_from_packet_record=lambda _root, _state, _record: relative_result_path
    )

    _validate_result_bodies_opened_by_pm(
        fake_router,
        project_root,
        {"run_id": "run-test"},
        [{"packet_id": "packet-1"}],
    )

    result_path.write_text(
        json.dumps(
            {
                "packet_id": "packet-1",
                "result_body_opened_by_role": {
                    "role": "worker",
                    "body_hash_verified": True,
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RouterError, match="project_manager to open result body"):
        _validate_result_bodies_opened_by_pm(
            fake_router,
            project_root,
            {"run_id": "run-test"},
            [{"packet_id": "packet-1"}],
        )


@pytest.mark.parametrize(
    ("runner", "result_path"),
    [
        ("flowpilot_blocker_repair_information_flow", "flowpilot_blocker_repair_information_flow_results.json"),
        ("flowpilot_canonical_repair_scope_rotation", "flowpilot_canonical_repair_scope_rotation_results.json"),
        ("flowpilot_complete_system_historical_replay", "flowpilot_complete_system_historical_replay_results.json"),
        ("flowpilot_complete_system_live_host_readiness", "flowpilot_complete_system_live_host_results.json"),
        ("flowpilot_complete_system_runtime", "flowpilot_complete_system_runtime_results.json"),
        ("flowpilot_project_control_information_flow", "flowpilot_project_control_information_flow_results.json"),
        ("flowpilot_role_packet_access", "flowpilot_role_packet_access_results.json"),
        ("flowpilot_semantic_gate_outcome", "flowpilot_semantic_gate_outcome_results.json"),
        ("flowpilot_stopped_blocker_recheck", "flowpilot_stopped_blocker_recheck_results.json"),
        ("flowpilot_symmetric_work_packet", "flowpilot_symmetric_work_packet_results.json"),
        ("flowpilot_unsupported_transition_pruning", "flowpilot_unsupported_transition_pruning_results.json"),
        ("flowpilot_validation_pm_gate", "flowpilot_validation_pm_gate_results.json"),
        ("new_only_runtime", "flowpilot_new_only_runtime_results.json"),
    ],
)
def test_model_runner_tracked_result_is_green(runner: str, result_path: str) -> None:
    payload = json.loads((SIMULATIONS / result_path).read_text(encoding="utf-8"))

    assert payload.get("ok") is True, runner
