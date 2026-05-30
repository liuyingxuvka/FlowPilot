"""Current-run shell persistence for the complete black-box FlowPilot runtime."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any

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
    current = {
        "schema_version": RUN_SCHEMA_VERSION,
        "run_id": selected_run_id,
        "run_root": str(run_root),
        "ledger_path": str(ledger_path),
        "authority": "current_run_ledger",
    }
    (flowpilot_root / "current.json").write_text(json.dumps(current, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _append_index(flowpilot_root / "index.json", current)
    return shell


def load_run_shell(root: Path, *, run_id: str | None = None) -> RunShell:
    root = Path(root).resolve()
    flowpilot_root = root / ".flowpilot"
    if run_id is None:
        current = json.loads((flowpilot_root / "current.json").read_text(encoding="utf-8"))
        run_id = current["run_id"]
    run_root = flowpilot_root / "runs" / run_id
    return RunShell(root, flowpilot_root, run_id, run_root, run_root / "ledger.json", run_root / "events.jsonl")


def save_run_ledger(shell: RunShell, ledger: dict[str, Any], *, guard_trigger: str = "save") -> None:
    record_guard_progress = guard_trigger != "save"
    runtime.refresh_lifecycle_guard(
        ledger,
        trigger=guard_trigger,
        record_history=record_guard_progress,
        record_event=record_guard_progress,
    )
    runtime.save_ledger(ledger, shell.ledger_path)
    _write_events_jsonl(ledger, shell.events_path)
    materialize_run_artifacts(shell, ledger)


def load_run_ledger(shell: RunShell) -> dict[str, Any]:
    return runtime.load_ledger(shell.ledger_path)


def record_startup_intake_result(shell: RunShell, result_path: Path) -> dict[str, Any]:
    """Import a native startup-intake result as sealed current-run authority."""

    result_path = Path(result_path)
    if not result_path.is_absolute():
        result_path = (shell.root / result_path).resolve()
    result = _read_json(result_path)
    if result.get("status") != "confirmed":
        raise runtime.BlackBoxRuntimeError("startup intake must be confirmed")
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
    for node_id, node in ledger.get("route_nodes", {}).items():
        _write_json(shell.run_root / "route_nodes" / f"{node_id}.json", node)
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
    for lease_id, memory in ledger.get("role_memory", {}).items():
        _write_json(shell.run_root / "role_memory" / f"{lease_id}.json", memory)
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
        _write_json(shell.run_root / "closure" / "final_closure.json", ledger["closure"])
    if isinstance(ledger.get("lifecycle_guard"), dict):
        _write_json(shell.run_root / "lifecycle" / "guard.json", ledger["lifecycle_guard"])
    if ledger.get("lifecycle_guard_history"):
        _write_json(shell.run_root / "lifecycle" / "guard_history.json", ledger["lifecycle_guard_history"])
    if isinstance(ledger.get("final_route_wide_gate_ledger"), dict):
        _write_json(shell.run_root / "closure" / "final_route_wide_gate_ledger.json", ledger["final_route_wide_gate_ledger"])
    if isinstance(ledger.get("final_requirement_evidence_matrix"), dict):
        _write_json(shell.run_root / "closure" / "final_requirement_evidence_matrix.json", ledger["final_requirement_evidence_matrix"])
    _write_json(shell.run_root / "console" / "status.json", runtime.render_console(ledger))


def _append_index(index_path: Path, current: dict[str, str]) -> None:
    if index_path.exists():
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    else:
        payload = {"schema_version": RUN_SCHEMA_VERSION, "runs": []}
    runs = [item for item in payload.get("runs", []) if item.get("run_id") != current["run_id"]]
    runs.append(current)
    payload["runs"] = runs
    index_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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
