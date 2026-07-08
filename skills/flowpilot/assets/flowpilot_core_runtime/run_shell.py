"""Current-run shell persistence for the complete black-box FlowPilot runtime."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from typing import Any

from . import control_surface
from . import pointer_store
from . import runtime


RUN_SCHEMA_VERSION = "black_box_flowpilot_run_shell.v1"


@dataclass(frozen=True)
class RunShell:
    root: Path
    flowpilot_root: Path
    run_id: str
    run_root: Path
    ledger_path: Path
    events_path: Path

    def to_json(self) -> dict[str, str]:
        return {
            "schema_version": RUN_SCHEMA_VERSION,
            "root": str(self.root),
            "flowpilot_root": str(self.flowpilot_root),
            "run_id": self.run_id,
            "run_root": str(self.run_root),
            "ledger_path": str(self.ledger_path),
            "events_path": str(self.events_path),
        }


def _default_run_id() -> str:
    return datetime.now(timezone.utc).strftime("run-%Y%m%d-%H%M%S")


def create_run_shell(
    root: Path,
    goal: str,
    acceptance_contract: str,
    *,
    run_id: str | None = None,
) -> RunShell:
    """Create a fresh current-run shell and seed its canonical ledger."""

    root = Path(root).resolve()
    flowpilot_root = root / ".flowpilot"
    selected_run_id = run_id or _default_run_id()
    run_root = flowpilot_root / "runs" / selected_run_id
    ledger_path = run_root / "ledger.json"
    events_path = run_root / "events.jsonl"
    for relative in (
        "routes",
        "startup_intake",
        "packets/envelopes",
        "packets/bodies",
        "results/envelopes",
        "results/bodies",
        "leases",
        "role_memory",
        "role_continuity",
        "role_assignments",
        "frontier",
        "preplanning",
        "route_nodes",
        "node_acceptance_plans",
        "parent_backward_replays",
        "flowguard/work_orders",
        "flowguard/work_orders/envelopes",
        "flowguard/work_orders/reports",
        "reviews",
        "evidence",
        "console",
        "closure",
        "lifecycle",
        "runtime",
        "imports",
    ):
        (run_root / relative).mkdir(parents=True, exist_ok=True)

    ledger = runtime.new_ledger(goal, acceptance_contract, project_id=selected_run_id)
    ledger["run_id"] = selected_run_id
    ledger["run_root"] = str(run_root)
    ledger["projection_paths"] = {
        "ledger": str(ledger_path),
        "events": str(events_path),
        "console_status": str(run_root / "console" / "status.json"),
    }
    shell = RunShell(root, flowpilot_root, selected_run_id, run_root, ledger_path, events_path)
    save_run_ledger(shell, ledger)

    flowpilot_root.mkdir(parents=True, exist_ok=True)
    current = pointer_store.current_payload_from_ledger(
        root,
        run_id=selected_run_id,
        run_root=run_root,
        ledger_path=ledger_path,
        ledger=ledger,
        include_refresh_fields=False,
    )
    pointer_store.write_pointer_json(flowpilot_root / "current.json", current)
    pointer_store.append_index(root, current)
    return shell


def load_run_shell(root: Path, *, run_id: str | None = None) -> RunShell:
    root = Path(root).resolve()
    flowpilot_root = root / ".flowpilot"
    resolution = control_surface.resolve_current_run(root, run_id=run_id)
    if not resolution.ok or not resolution.run_id or resolution.run_root is None:
        raise runtime.BlackBoxRuntimeError(resolution.message or resolution.error_code or "cannot resolve current run")
    return RunShell(
        root,
        flowpilot_root,
        resolution.run_id,
        resolution.run_root,
        resolution.ledger_path or resolution.run_root / "ledger.json",
        resolution.run_root / "events.jsonl",
    )


def save_run_ledger(
    shell: RunShell,
    ledger: dict[str, Any],
    *,
    guard_trigger: str = "save",
    resume_source: str = "",
) -> None:
    record_guard_progress = guard_trigger != "save"
    runtime.refresh_lifecycle_guard(
        ledger,
        trigger=guard_trigger,
        resume_source=resume_source,
        record_history=record_guard_progress,
        record_event=record_guard_progress,
    )
    runtime.refresh_status_projection(ledger)
    runtime.save_ledger(ledger, shell.ledger_path)
    _write_events_jsonl(ledger, shell.events_path)
    materialize_run_artifacts(shell, ledger)
    _refresh_current_pointer_status(shell, ledger)


def load_run_ledger(shell: RunShell) -> dict[str, Any]:
    return runtime.load_ledger(shell.ledger_path)


def record_startup_intake_result(shell: RunShell, result_path: Path) -> dict[str, Any]:
    """Import a native startup-intake result as sealed current-run authority."""

    result_path = Path(result_path)
    if not result_path.is_absolute():
        result_path = (shell.root / result_path).resolve()
    result = _read_json(result_path)
    status = str(result.get("status") or "")
    startup_answers = result.get("startup_answers") if isinstance(result.get("startup_answers"), dict) else {}
    if status == "blocked":
        if startup_answers.get(runtime.BACKGROUND_COLLABORATION_ACK_FIELD) is not False:
            raise runtime.BlackBoxRuntimeError(
                "blocked startup intake must record background_collaboration_authorized=false"
            )
        startup_root = shell.run_root / "startup_intake"
        startup_root.mkdir(parents=True, exist_ok=True)
        copied_result = startup_root / "startup_intake_result.json"
        shutil.copy2(result_path, copied_result)
        copied: dict[str, str] = {"result": str(copied_result)}
        raw_receipt = result.get("receipt_path")
        if isinstance(raw_receipt, str) and raw_receipt:
            source = _resolve_record_path(shell.root, result_path, raw_receipt)
            if source.exists():
                target = startup_root / "startup_intake_receipt.json"
                shutil.copy2(source, target)
                copied["receipt"] = str(target)

        ledger = load_run_ledger(shell)
        record = {
            "schema_version": "black_box_flowpilot.startup_intake.v1",
            "status": "blocked",
            "source": result.get("source", ""),
            "launch_mode": result.get("launch_mode", ""),
            "headless": result.get("headless"),
            "formal_startup_allowed": result.get("formal_startup_allowed"),
            "startup_answers": startup_answers,
            "block_reason": str(result.get("block_reason") or "background_collaboration_required"),
            "body_visibility": "none",
            "controller_may_read_body": False,
            "body_text_included": False,
            "current_run_authority": True,
            "imported_from": str(result_path),
            "run_paths": copied,
            "recorded_at": runtime.now_iso(),
        }
        ledger["startup_intake"] = record
        runtime._event(
            ledger,
            "startup_intake_recorded",
            status="blocked",
            block_reason=record["block_reason"],
            source=str(result_path),
        )
        runtime.record_terminal_lifecycle(
            ledger,
            "stopped_by_user",
            reason=record["block_reason"],
            actor="startup_intake",
        )
        if isinstance(ledger.get("terminal_lifecycle"), dict):
            ledger["terminal_lifecycle"]["startup_block_reason"] = record["block_reason"]
        if isinstance(ledger.get("lifecycle"), dict):
            ledger["lifecycle"]["startup_block_reason"] = record["block_reason"]
        save_run_ledger(shell, ledger, guard_trigger="startup_blocked")
        return record
    if status != "confirmed":
        raise runtime.BlackBoxRuntimeError("startup intake must be confirmed")
    if startup_answers.get(runtime.BACKGROUND_COLLABORATION_ACK_FIELD) is not True:
        raise runtime.BlackBoxRuntimeError(
            runtime.BACKGROUND_COLLABORATION_REQUIRED_MESSAGE
            + ": "
            + runtime.background_collaboration_blocker({"startup_intake": {"startup_answers": startup_answers}})
        )
    body_path = _resolve_record_path(shell.root, result_path, str(result.get("body_path", "")))
    if not body_path.exists():
        raise runtime.BlackBoxRuntimeError(f"missing startup body: {body_path}")
    body_hash = hashlib.sha256(body_path.read_bytes()).hexdigest()
    if body_hash != result.get("body_hash"):
        raise runtime.BlackBoxRuntimeError("startup body hash mismatch")

    startup_root = shell.run_root / "startup_intake"
    startup_root.mkdir(parents=True, exist_ok=True)
    copied_result = startup_root / "startup_intake_result.json"
    copied_body = startup_root / "startup_intake_body.md"
    shutil.copy2(result_path, copied_result)
    shutil.copy2(body_path, copied_body)

    copied: dict[str, str] = {
        "result": str(copied_result),
        "body": str(copied_body),
    }
    for key, filename in (
        ("receipt_path", "startup_intake_receipt.json"),
        ("envelope_path", "startup_intake_envelope.json"),
    ):
        raw = result.get(key)
        if isinstance(raw, str) and raw:
            source = _resolve_record_path(shell.root, result_path, raw)
            if source.exists():
                target = startup_root / filename
                shutil.copy2(source, target)
                copied[key.removesuffix("_path")] = str(target)

    ledger = load_run_ledger(shell)
    record = {
        "schema_version": "black_box_flowpilot.startup_intake.v1",
        "status": "confirmed",
        "source": result.get("source", ""),
        "launch_mode": result.get("launch_mode", ""),
        "headless": result.get("headless"),
        "formal_startup_allowed": result.get("formal_startup_allowed"),
        "startup_answers": result.get("startup_answers", {}),
        "body_hash": body_hash,
        "body_visibility": "sealed_pm_only",
        "controller_may_read_body": False,
        "body_text_included": False,
        "current_run_authority": True,
        "imported_from": str(result_path),
        "run_paths": copied,
        "recorded_at": runtime.now_iso(),
    }
    ledger["startup_intake"] = record
    ledger["lifecycle"] = {"state": "startup_intake_recorded"}
    runtime._event(ledger, "startup_intake_recorded", body_hash=body_hash, source=str(result_path))
    save_run_ledger(shell, ledger)
    return record


def materialize_run_artifacts(shell: RunShell, ledger: dict[str, Any]) -> None:
    """Project the canonical ledger into current-run envelope/body files."""

    for packet_id, packet in ledger.get("packets", {}).items():
        _write_json(shell.run_root / "packets" / "envelopes" / f"{packet_id}.json", packet["envelope"])
        _write_text(shell.run_root / "packets" / "bodies" / f"{packet_id}.md", str(packet.get("body", "")))
    for route_version, route in ledger.get("routes", {}).items():
        _write_json(shell.run_root / "routes" / f"route-v{route_version}.json", route)
    _write_route_node_projections(shell, ledger.get("route_nodes", {}))
    if isinstance(ledger.get("high_standard_contract"), dict):
        _write_json(shell.run_root / "preplanning" / "high_standard_contract.json", ledger["high_standard_contract"])
    if isinstance(ledger.get("preplanning_discovery"), dict):
        _write_json(shell.run_root / "preplanning" / "discovery.json", ledger["preplanning_discovery"])
    if isinstance(ledger.get("skill_standard_contract"), dict):
        _write_json(shell.run_root / "preplanning" / "skill_standard_contract.json", ledger["skill_standard_contract"])
    for plan_id, plan in ledger.get("node_acceptance_plans", {}).items():
        _write_json(shell.run_root / "node_acceptance_plans" / f"{plan_id}.json", plan)
    for replay_id, replay in ledger.get("parent_backward_replays", {}).items():
        _write_json(shell.run_root / "parent_backward_replays" / f"{replay_id}.json", replay)
    if isinstance(ledger.get("execution_frontier"), dict):
        _write_json(shell.run_root / "frontier" / "execution_frontier.json", ledger["execution_frontier"])
    for result_id, result in ledger.get("results", {}).items():
        _write_json(shell.run_root / "results" / "envelopes" / f"{result_id}.json", result["envelope"])
        _write_text(shell.run_root / "results" / "bodies" / f"{result_id}.md", str(result.get("body", "")))
    for lease_id, lease in ledger.get("leases", {}).items():
        _write_json(shell.run_root / "leases" / f"{lease_id}.json", lease)
    for assignment_id, assignment in ledger.get("role_assignments", {}).items():
        _write_json(shell.run_root / "role_assignments" / f"{assignment_id}.json", assignment)
    for lease_id, memory in ledger.get("role_memory", {}).items():
        _write_json(shell.run_root / "role_memory" / f"{lease_id}.json", memory)
    if isinstance(ledger.get("role_continuity"), dict):
        _write_json(shell.run_root / "role_continuity" / "role_continuity.json", ledger["role_continuity"])
    for order_id, order in ledger.get("flowguard_work_orders", {}).items():
        _write_json(shell.run_root / "flowguard" / "work_orders" / f"{order_id}.json", order)
        envelope = {
            "order_id": order["order_id"],
            "modeled_target": order["modeled_target"],
            "risk_type": order["risk_type"],
            "selected_skill": order["selected_skill"],
            "subject_id": order["subject_id"],
            "status": order["status"],
            "source_generation": order["source_generation"],
        }
        _write_json(shell.run_root / "flowguard" / "work_orders" / "envelopes" / f"{order_id}.json", envelope)
        _write_json(shell.run_root / "flowguard" / "work_orders" / "reports" / f"{order_id}.json", order)
    for review_id, review in ledger.get("reviews", {}).items():
        _write_json(shell.run_root / "reviews" / f"{review_id}.json", review)
    for import_id, imported in ledger.get("imported_evidence", {}).items():
        _write_json(shell.run_root / "imports" / f"{import_id}.json", imported)
    for evidence_id, evidence in ledger.get("validation_evidence", {}).items():
        safe_id = evidence_id.replace("/", "_").replace("\\", "_")
        _write_json(shell.run_root / "evidence" / f"{safe_id}.json", evidence)
    if isinstance(ledger.get("cutover_gate"), dict):
        _write_json(shell.run_root / "closure" / "cutover_gate.json", ledger["cutover_gate"])
    if isinstance(ledger.get("closure"), dict):
        _write_json(shell.run_root / "closure" / "final_closure.json", runtime.render_final_closure_projection(ledger))
    if isinstance(ledger.get("lifecycle_guard"), dict):
        _write_json(shell.run_root / "lifecycle" / "guard.json", ledger["lifecycle_guard"])
    if isinstance(ledger.get("terminal_lifecycle"), dict):
        _write_json(shell.run_root / "lifecycle" / "terminal_lifecycle.json", ledger["terminal_lifecycle"])
    if ledger.get("lifecycle_guard_history"):
        _write_json(shell.run_root / "lifecycle" / "guard_history.json", ledger["lifecycle_guard_history"])
    if isinstance(ledger.get("foreground_duty"), dict):
        _write_json(shell.run_root / "lifecycle" / "foreground_duty.json", ledger["foreground_duty"])
    if ledger.get("foreground_duty_history"):
        _write_json(shell.run_root / "lifecycle" / "foreground_duty_history.json", ledger["foreground_duty_history"])
    if isinstance(ledger.get("flowpilot_runtime_self_check"), dict):
        _write_json(
            shell.run_root / "runtime" / "flowpilot_runtime_self_check_receipt.json",
            ledger["flowpilot_runtime_self_check"],
        )
    if isinstance(ledger.get("final_route_wide_gate_ledger"), dict):
        _write_json(shell.run_root / "closure" / "final_route_wide_gate_ledger.json", ledger["final_route_wide_gate_ledger"])
    if isinstance(ledger.get("final_requirement_evidence_matrix"), dict):
        _write_json(shell.run_root / "closure" / "final_requirement_evidence_matrix.json", ledger["final_requirement_evidence_matrix"])
    if ledger.get("orphan_evidence"):
        _write_json(shell.run_root / "evidence" / "orphan_evidence.json", ledger["orphan_evidence"])
    status_projection = ledger.get("status_projection")
    _write_json(
        shell.run_root / "console" / "status.json",
        status_projection if isinstance(status_projection, dict) else runtime.render_console(ledger),
    )


def _append_index(index_path: Path, current: dict[str, Any]) -> None:
    pointer_store.append_index(index_path.parent.parent, current)


def _refresh_current_pointer_status(shell: RunShell, ledger: dict[str, Any]) -> None:
    current_path = shell.flowpilot_root / "current.json"
    if not current_path.exists():
        return
    try:
        current = json.loads(current_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        recovery = pointer_store.recover_current_pointer(shell.root)
        if not recovery.ok or recovery.current is None:
            return
        current = recovery.current
    if not isinstance(current, dict) or current.get("run_id") != shell.run_id:
        return
    current = pointer_store.current_payload_from_ledger(
        shell.root,
        run_id=shell.run_id,
        run_root=shell.run_root,
        ledger_path=shell.ledger_path,
        ledger=ledger,
        include_refresh_fields=True,
    )
    pointer_store.write_pointer_json(current_path, current)
    _append_index(shell.flowpilot_root / "index.json", current)


def _write_events_jsonl(ledger: dict[str, Any], events_path: Path) -> None:
    events_path.parent.mkdir(parents=True, exist_ok=True)
    existing_ids: set[str] = set()
    if events_path.exists():
        for line in events_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            event_id = payload.get("event_id")
            if isinstance(event_id, str):
                existing_ids.add(event_id)
    new_lines = [
        json.dumps(event, sort_keys=True)
        for event in ledger.get("events", [])
        if event.get("event_id") not in existing_ids
    ]
    if new_lines:
        with events_path.open("a", encoding="utf-8") as handle:
            handle.write("\n".join(new_lines) + "\n")


def _write_route_node_projections(shell: RunShell, route_nodes: Any) -> None:
    if not isinstance(route_nodes, dict):
        return
    entries: list[dict[str, Any]] = []
    for node_id, node in route_nodes.items():
        node_id_text = str(node_id)
        filename = _safe_projection_filename(node_id_text)
        path = shell.run_root / "route_nodes" / filename
        _write_json(path, node)
        entries.append(
            {
                "node_id": node_id_text,
                "filename": filename,
                "path": str(path),
                "sha256": hashlib.sha256(node_id_text.encode("utf-8")).hexdigest(),
                "shortened": filename != f"{_filename_safe_stem(node_id_text)}.json",
            }
        )
    _write_json(
        shell.run_root / "route_nodes" / "index.json",
        {
            "schema_version": "black_box_flowpilot.route_node_projection_index.v1",
            "nodes": entries,
        },
    )


def _safe_projection_filename(raw_id: str, *, suffix: str = ".json", max_component_chars: int = 120) -> str:
    stem = _filename_safe_stem(raw_id)
    if len(stem) + len(suffix) <= max_component_chars:
        return f"{stem}{suffix}"
    digest = hashlib.sha256(raw_id.encode("utf-8")).hexdigest()[:16]
    prefix_limit = max(1, max_component_chars - len(suffix) - len(digest) - 1)
    return f"{stem[:prefix_limit]}-{digest}{suffix}"


def _filename_safe_stem(raw_id: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in raw_id)


def _write_json(path: Path, payload: Any) -> None:
    _write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(text)
            tmp_path = Path(handle.name)
        tmp_path.replace(path)
    finally:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink()


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise runtime.BlackBoxRuntimeError(f"expected JSON object: {path}")
    return payload


def _resolve_record_path(root: Path, record_path: Path, raw: str) -> Path:
    if not raw:
        raise runtime.BlackBoxRuntimeError("startup intake path is missing")
    path = Path(raw)
    if path.is_absolute():
        return path
    candidate_bases = [root, record_path.parent, Path.cwd()]
    for parent in Path(__file__).resolve().parents:
        if (parent / "assets" / "brand" / "flowpilot-icon-default.png").exists():
            candidate_bases.append(parent)
            break
    for base in candidate_bases:
        candidate = (base / path).resolve()
        if candidate.exists():
            return candidate
    return (root / path).resolve()
