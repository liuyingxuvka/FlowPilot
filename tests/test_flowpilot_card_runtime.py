from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "flowpilot" / "assets"))

import card_runtime  # noqa: E402


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def make_project() -> tuple[Path, Path, Path]:
    root = Path(tempfile.mkdtemp(prefix="flowpilot-card-runtime-"))
    run_root = root / ".flowpilot" / "runs" / "run-card-runtime"
    body_path = run_root / "runtime_kit" / "cards" / "system" / "pm_core.md"
    body_path.parent.mkdir(parents=True, exist_ok=True)
    body_path.write_text("PM core card body", encoding="utf-8")
    write_json(run_root / "card_ledger.json", {"schema_version": card_runtime.CARD_LEDGER_SCHEMA, "run_id": run_root.name, "deliveries": [], "read_receipts": [], "ack_envelopes": []})
    write_json(run_root / "return_event_ledger.json", {"schema_version": card_runtime.RETURN_EVENT_LEDGER_SCHEMA, "run_id": run_root.name, "pending_returns": [], "completed_returns": []})
    return root, run_root, body_path


def make_envelope(root: Path, run_root: Path, body_path: Path) -> Path:
    envelope_path = run_root / "mailbox" / "system_cards" / "pm_core_delivery.json"
    receipt_path = run_root / "runtime_receipts" / "card_reads" / "pm_core.receipt.json"
    ack_path = run_root / "mailbox" / "outbox" / "card_acks" / "pm_core.ack.json"
    envelope = {
        "schema_version": card_runtime.CARD_ENVELOPE_SCHEMA,
        "run_id": run_root.name,
        "run_root": run_root.relative_to(root).as_posix(),
        "resume_tick_id": "manual-resume",
        "envelope_id": "pm_core-delivery-001-attempt-001",
        "delivery_id": "pm_core-delivery-001",
        "delivery_attempt_id": "pm_core-delivery-001-attempt-001",
        "card_id": "pm.core",
        "target_role": "project_manager",
        "target_agent_id": "pm-agent-1",
        "body_path": body_path.relative_to(root).as_posix(),
        "body_hash": card_runtime.sha256_file(body_path),
        "manifest_hash": "manifest-hash",
        "controller_visibility": "system_card_envelope_only",
        "sealed_body_reads_allowed": False,
        "requires_read_receipt": True,
        "open_method": "open-card",
        "card_return_event": "pm_card_ack",
        "expected_receipt_path": receipt_path.relative_to(root).as_posix(),
        "expected_return_path": ack_path.relative_to(root).as_posix(),
        "delivered_at": card_runtime.utc_now(),
    }
    token = {
        "schema_version": card_runtime.CARD_DIRECT_ROUTER_ACK_TOKEN_SCHEMA,
        "return_kind": "system_card",
        "submission_mode": "direct_to_router",
        "controller_ack_handoff_allowed": False,
        "run_id": run_root.name,
        "card_id": "pm.core",
        "card_return_event": "pm_card_ack",
        "target_role": "project_manager",
        "target_agent_id": "pm-agent-1",
        "delivery_id": "pm_core-delivery-001",
        "delivery_attempt_id": "pm_core-delivery-001-attempt-001",
        "expected_return_path": ack_path.relative_to(root).as_posix(),
        "expected_receipt_path": receipt_path.relative_to(root).as_posix(),
        "body_hash": envelope["body_hash"],
    }
    envelope["direct_router_ack_token"] = token
    envelope["direct_router_ack_token_hash"] = card_runtime.stable_json_hash(token)
    envelope["envelope_hash"] = card_runtime.stable_json_hash(envelope)
    write_json(envelope_path, envelope)
    return envelope_path


def make_bundle_envelope(root: Path, run_root: Path, body_path: Path) -> Path:
    second_body = run_root / "runtime_kit" / "cards" / "system" / "pm_phase_map.md"
    second_body.write_text("PM phase map card body", encoding="utf-8")
    envelope_path = run_root / "mailbox" / "system_card_bundles" / "pm_startup_bundle.json"
    ack_path = run_root / "mailbox" / "outbox" / "card_bundle_acks" / "pm_startup_bundle.ack.json"
    first_receipt = run_root / "runtime_receipts" / "card_reads" / "pm_core.receipt.json"
    second_receipt = run_root / "runtime_receipts" / "card_reads" / "pm_phase_map.receipt.json"
    envelope = {
        "schema_version": card_runtime.CARD_BUNDLE_ENVELOPE_SCHEMA,
        "run_id": run_root.name,
        "run_root": run_root.relative_to(root).as_posix(),
        "resume_tick_id": "manual-resume",
        "bundle_id": "pm-startup-bundle-001",
        "target_role": "project_manager",
        "target_agent_id": "pm-agent-1",
        "cards": [
            {
                "card_id": "pm.core",
                "delivery_id": "pm-core-delivery-001",
                "delivery_attempt_id": "pm-core-delivery-001-attempt-001",
                "body_path": body_path.relative_to(root).as_posix(),
                "body_hash": card_runtime.sha256_file(body_path),
                "manifest_hash": "manifest-hash",
                "expected_receipt_path": first_receipt.relative_to(root).as_posix(),
                "card_return_event": "pm_card_ack",
            },
            {
                "card_id": "pm.phase_map",
                "delivery_id": "pm-phase-map-delivery-001",
                "delivery_attempt_id": "pm-phase-map-delivery-001-attempt-001",
                "body_path": second_body.relative_to(root).as_posix(),
                "body_hash": card_runtime.sha256_file(second_body),
                "manifest_hash": "manifest-hash",
                "expected_receipt_path": second_receipt.relative_to(root).as_posix(),
                "card_return_event": "pm_card_ack",
            },
        ],
        "card_ids": ["pm.core", "pm.phase_map"],
        "controller_visibility": "system_card_bundle_envelope_only",
        "sealed_body_reads_allowed": False,
        "requires_read_receipt": True,
        "open_method": "open-card-bundle",
        "card_return_event": "pm_card_bundle_ack",
        "expected_receipt_paths": [
            first_receipt.relative_to(root).as_posix(),
            second_receipt.relative_to(root).as_posix(),
        ],
        "expected_return_path": ack_path.relative_to(root).as_posix(),
        "delivered_at": card_runtime.utc_now(),
    }
    token = {
        "schema_version": card_runtime.CARD_DIRECT_ROUTER_ACK_TOKEN_SCHEMA,
        "return_kind": "system_card_bundle",
        "submission_mode": "direct_to_router",
        "controller_ack_handoff_allowed": False,
        "run_id": run_root.name,
        "card_bundle_id": "pm-startup-bundle-001",
        "card_ids": ["pm.core", "pm.phase_map"],
        "delivery_attempt_ids": ["pm-core-delivery-001-attempt-001", "pm-phase-map-delivery-001-attempt-001"],
        "card_return_event": "pm_card_bundle_ack",
        "target_role": "project_manager",
        "target_agent_id": "pm-agent-1",
        "expected_return_path": ack_path.relative_to(root).as_posix(),
        "expected_receipt_paths": [
            first_receipt.relative_to(root).as_posix(),
            second_receipt.relative_to(root).as_posix(),
        ],
    }
    envelope["direct_router_ack_token"] = token
    envelope["direct_router_ack_token_hash"] = card_runtime.stable_json_hash(token)
    envelope["bundle_hash"] = card_runtime.stable_json_hash(envelope)
    write_json(envelope_path, envelope)
    return envelope_path


def test_card_runtime_opens_card_and_submits_ack() -> None:
    root, run_root, body_path = make_project()
    envelope_path = make_envelope(root, run_root, body_path)

    opened = card_runtime.open_card(root, envelope_path=envelope_path.relative_to(root).as_posix(), role="project_manager", agent_id="pm-agent-1")
    assert opened["body_text"] == "PM core card body"
    assert opened["body_text_visibility"] == "target_role_only"
    assert (root / opened["read_receipt_path"]).exists()

    ack = card_runtime.submit_card_ack(
        root,
        envelope_path=envelope_path.relative_to(root).as_posix(),
        role="project_manager",
        agent_id="pm-agent-1",
        receipt_paths=[opened["read_receipt_path"]],
    )
    assert ack["ack_envelope"]["contains_card_body"] is False
    assert ack["ack_envelope"]["card_return_event"] == "pm_card_ack"
    assert ack["ack_envelope"]["ack_delivery_mode"] == "direct_to_router"
    assert ack["ack_envelope"]["submitted_to"] == "router"
    assert ack["ack_envelope"]["controller_ack_handoff_used"] is False
    assert ack["ack_envelope"]["direct_router_ack_token_hash"]
    assert "return_event" not in ack["ack_envelope"]
    assert ack["ack_envelope"]["receipt_refs"]
    validation = card_runtime.validate_card_ack(
        root,
        ack_path=ack["ack_path"],
        envelope_path=envelope_path.relative_to(root).as_posix(),
    )
    assert validation["ok"] is True
    assert validation["card_return_event"] == "pm_card_ack"
    assert validation["ack_delivery_mode"] == "direct_to_router"
    assert validation["receipt_ref_count"] == 1


def test_unified_runtime_receive_card_writes_receipt_and_ack() -> None:
    root, run_root, body_path = make_project()
    envelope_path = make_envelope(root, run_root, body_path)

    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "flowpilot_runtime.py"),
            "--root",
            str(root),
            "receive-card",
            "--envelope-path",
            envelope_path.relative_to(root).as_posix(),
            "--role",
            "project_manager",
            "--agent-id",
            "pm-agent-1",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    result = json.loads(completed.stdout)
    assert result["ok"] is True
    assert result["command"] == "receive-card"
    assert result["opened"]["body_text"] == "PM core card body"
    assert result["ack"]["ack_envelope"]["card_return_event"] == "pm_card_ack"
    assert result["ack"]["ack_envelope"]["ack_delivery_mode"] == "direct_to_router"
    assert result["validation"]["ok"] is True
    assert (root / result["opened"]["read_receipt_path"]).exists()
    assert (root / result["ack"]["ack_path"]).exists()


def test_card_runtime_opens_bundle_and_submits_one_ack_with_per_card_receipts() -> None:
    root, run_root, body_path = make_project()
    envelope_path = make_bundle_envelope(root, run_root, body_path)

    opened = card_runtime.open_card_bundle(
        root,
        envelope_path=envelope_path.relative_to(root).as_posix(),
        role="project_manager",
        agent_id="pm-agent-1",
    )
    assert [card["card_id"] for card in opened["cards"]] == ["pm.core", "pm.phase_map"]
    assert opened["read_receipt_paths"]

    ack = card_runtime.submit_card_bundle_ack(
        root,
        envelope_path=envelope_path.relative_to(root).as_posix(),
        role="project_manager",
        agent_id="pm-agent-1",
        receipt_paths=opened["read_receipt_paths"],
    )
    assert ack["ack_envelope"]["contains_card_body"] is False
    assert ack["ack_envelope"]["card_return_event"] == "pm_card_bundle_ack"
    assert ack["ack_envelope"]["ack_delivery_mode"] == "direct_to_router"
    assert ack["ack_envelope"]["controller_ack_handoff_used"] is False
    assert ack["ack_envelope"]["member_card_ids"] == ["pm.core", "pm.phase_map"]
    validation = card_runtime.validate_card_bundle_ack(
        root,
        ack_path=ack["ack_path"],
        envelope_path=envelope_path.relative_to(root).as_posix(),
    )
    assert validation["ok"] is True
    assert validation["ack_delivery_mode"] == "direct_to_router"
    assert validation["receipt_ref_count"] == 2


def test_unified_runtime_receive_card_bundle_writes_all_receipts_and_ack() -> None:
    root, run_root, body_path = make_project()
    envelope_path = make_bundle_envelope(root, run_root, body_path)

    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "flowpilot_runtime.py"),
            "--root",
            str(root),
            "receive-card-bundle",
            "--envelope-path",
            envelope_path.relative_to(root).as_posix(),
            "--role",
            "project_manager",
            "--agent-id",
            "pm-agent-1",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    result = json.loads(completed.stdout)
    assert result["ok"] is True
    assert result["command"] == "receive-card-bundle"
    assert [card["card_id"] for card in result["opened"]["cards"]] == ["pm.core", "pm.phase_map"]
    assert result["ack"]["ack_envelope"]["card_return_event"] == "pm_card_bundle_ack"
    assert result["ack"]["ack_envelope"]["ack_delivery_mode"] == "direct_to_router"
    assert result["validation"]["ok"] is True
    assert result["validation"]["receipt_ref_count"] == 2


def test_card_runtime_rejects_wrong_role_and_ack_without_receipt() -> None:
    root, run_root, body_path = make_project()
    envelope_path = make_envelope(root, run_root, body_path)

    with pytest.raises(card_runtime.CardRuntimeError, match="target role mismatch"):
        card_runtime.open_card(root, envelope_path=envelope_path.relative_to(root).as_posix(), role="worker_a", agent_id="pm-agent-1")

    with pytest.raises(card_runtime.CardRuntimeError, match="card ack requires receipt paths"):
        card_runtime.submit_card_ack(
            root,
            envelope_path=envelope_path.relative_to(root).as_posix(),
            role="project_manager",
            agent_id="pm-agent-1",
            receipt_paths=[],
        )


def test_card_runtime_rejects_tokenless_ack_envelope() -> None:
    root, run_root, body_path = make_project()
    envelope_path = make_envelope(root, run_root, body_path)
    envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
    envelope.pop("direct_router_ack_token", None)
    envelope.pop("direct_router_ack_token_hash", None)
    write_json(envelope_path, envelope)

    opened = card_runtime.open_card(
        root,
        envelope_path=envelope_path.relative_to(root).as_posix(),
        role="project_manager",
        agent_id="pm-agent-1",
    )
    with pytest.raises(card_runtime.CardRuntimeError, match="missing direct Router ACK token"):
        card_runtime.submit_card_ack(
            root,
            envelope_path=envelope_path.relative_to(root).as_posix(),
            role="project_manager",
            agent_id="pm-agent-1",
            receipt_paths=[opened["read_receipt_path"]],
        )
