from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "flowpilot" / "assets"))
sys.path.insert(0, str(ROOT / "scripts"))

import packet_runtime  # noqa: E402
import role_output_runtime  # noqa: E402


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def rel(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


@dataclass(frozen=True)
class SyntheticTracePackage:
    name: str
    role: str = "worker"
    agent_id: str = "agent-worker-1-1"
    packet_id: str = "trace-packet-001"
    node_id: str = "trace-node-001"
    evidence_kind: str = "synthetic"
    fake_packet_body: str = "Synthetic packet body for replay testing."
    fake_result_body: str = "Synthetic worker result for replay testing."
    next_recipient: str = "project_manager"
    expected_outcome: str = "pm_disposition_required"
    actions: tuple[str, ...] = (
        "issue_packet",
        "controller_relay_packet",
        "issue_active_holder_lease",
        "ack_packet",
        "open_packet_body",
        "submit_result",
    )


@dataclass
class SyntheticTraceReplay:
    package: SyntheticTracePackage
    root: Path
    steps: list[str] = field(default_factory=list)
    packet_envelope: dict[str, Any] | None = None
    result_envelope: dict[str, Any] | None = None
    lease: dict[str, Any] | None = None
    submission: dict[str, Any] | None = None

    @property
    def run_root(self) -> Path:
        return self.root / ".flowpilot" / "runs" / "run-test"

    @property
    def packet_dir(self) -> Path:
        return self.run_root / "packets" / self.package.packet_id

    @property
    def packet_envelope_path(self) -> Path:
        return self.packet_dir / "packet_envelope.json"

    @property
    def result_envelope_path(self) -> Path:
        return self.packet_dir / "result_envelope.json"

    @property
    def packet_ledger_path(self) -> Path:
        return self.run_root / "packet_ledger.json"

    def ledger(self) -> dict[str, Any]:
        return read_json(self.packet_ledger_path)

    def packet_record(self) -> dict[str, Any]:
        ledger = self.ledger()
        return next(
            record
            for record in ledger.get("packets", [])
            if isinstance(record, dict) and record.get("packet_id") == self.package.packet_id
        )

    def issue_packet(self) -> dict[str, Any]:
        self.packet_envelope = packet_runtime.create_packet(
            self.root,
            packet_id=self.package.packet_id,
            from_role="project_manager",
            to_role=self.package.role,
            node_id=self.package.node_id,
            body_text=self.package.fake_packet_body,
        )
        self.steps.append("issue_packet")
        return self.packet_envelope

    def relay_packet(self) -> dict[str, Any]:
        assert self.packet_envelope is not None
        self.packet_envelope = packet_runtime.controller_relay_envelope(
            self.root,
            envelope=self.packet_envelope,
            envelope_path=self.packet_envelope_path,
            controller_agent_id="agent-controller-1",
            received_from_role="project_manager",
            relayed_to_role=self.package.role,
        )
        self.steps.append("controller_relay_packet")
        return self.packet_envelope

    def issue_lease(self) -> dict[str, Any]:
        assert self.packet_envelope is not None
        self.lease = packet_runtime.issue_active_holder_lease(
            self.root,
            packet_envelope=self.packet_envelope,
            holder_role=self.package.role,
            holder_agent_id=self.package.agent_id,
            route_version=1,
            frontier_version=1,
        )
        self.steps.append("issue_active_holder_lease")
        return self.lease

    def ack(self) -> dict[str, Any]:
        assert self.lease is not None
        ack = packet_runtime.active_holder_ack(
            self.root,
            lease_path=self.lease["lease_path"],
            role=self.package.role,
            agent_id=self.package.agent_id,
            route_version=1,
            frontier_version=1,
        )
        self.steps.append("ack_packet")
        return ack

    def open_packet_body(self) -> str:
        assert self.packet_envelope is not None
        body = packet_runtime.read_packet_body_for_role(
            self.root,
            self.packet_envelope,
            role=self.package.role,
        )
        self.packet_envelope = read_json(self.packet_envelope_path)
        self.steps.append("open_packet_body")
        return body

    def submit_result(self) -> dict[str, Any]:
        assert self.lease is not None
        body = self.package.fake_result_body
        if "Contract Self-Check" not in body:
            body = body.rstrip() + "\n\nContract Self-Check\n\nstatus: pass\n"
        self.submission = packet_runtime.active_holder_submit_result(
            self.root,
            lease_path=self.lease["lease_path"],
            role=self.package.role,
            agent_id=self.package.agent_id,
            result_body_text=body,
            next_recipient=self.package.next_recipient,
            route_version=1,
            frontier_version=1,
        )
        self.result_envelope = read_json(self.result_envelope_path)
        self.steps.append("submit_result")
        return self.submission

    def relay_result(self, *, to_role: str | None = None) -> dict[str, Any]:
        assert self.result_envelope is not None
        target = to_role or str(self.result_envelope.get("next_recipient"))
        self.result_envelope = packet_runtime.controller_relay_envelope(
            self.root,
            envelope=self.result_envelope,
            envelope_path=self.result_envelope_path,
            controller_agent_id="agent-controller-1",
            received_from_role=self.package.role,
            relayed_to_role=target,
        )
        self.steps.append(f"controller_relay_result:{target}")
        return self.result_envelope

    def open_result_body(self, *, role: str | None = None) -> str:
        assert self.result_envelope is not None
        target = role or str(self.result_envelope.get("next_recipient"))
        body = packet_runtime.read_result_body_for_role(
            self.root,
            self.result_envelope,
            role=target,
        )
        self.result_envelope = read_json(self.result_envelope_path)
        self.steps.append(f"open_result_body:{target}")
        return body

    def pm_disposition(self, *, decision: str = "absorbed") -> dict[str, Any]:
        output_path = self.run_root / "synthetic_trace_outputs" / f"{self.package.name}.pm_disposition.json"
        result = role_output_runtime.submit_output(
            self.root,
            output_type="pm_package_result_disposition",
            role="project_manager",
            agent_id="agent-project_manager",
            run_id="run-test",
            event_name="pm_records_current_node_result_disposition",
            output_path=output_path,
            body={
                "decided_by_role": "project_manager",
                "decision": decision,
                "decision_reason": f"PM disposition for synthetic trace {self.package.name}.",
                "residual_risks": [],
            },
        )
        self.steps.append("pm_disposition")
        return result

    def tamper_result_body(self) -> None:
        path = self.root / self.result_envelope["result_body_path"]  # type: ignore[index]
        path.write_text(path.read_text(encoding="utf-8") + "\nTAMPERED\n", encoding="utf-8")
        self.steps.append("tamper_result_body")

    def update_result_hash_to_current_body(self) -> None:
        assert self.result_envelope is not None
        path = self.root / self.result_envelope["result_body_path"]
        self.result_envelope["result_body_hash"] = hashlib.sha256(path.read_bytes()).hexdigest()
        write_json(self.result_envelope_path, self.result_envelope)
        self.steps.append("update_result_hash_to_current_body")


def make_trace_project() -> Path:
    root = Path(tempfile.mkdtemp(prefix="flowpilot-synthetic-trace-"))
    write_json(
        root / ".flowpilot" / "current.json",
        {
            "current_run_id": "run-test",
            "current_run_root": ".flowpilot/runs/run-test",
            "status": "running",
        },
    )
    run_root = root / ".flowpilot" / "runs" / "run-test"
    write_json(run_root / "run.json", {"schema_version": "flowpilot.run.v1", "run_id": "run-test"})
    write_json(
        run_root / "state.json",
        {
            "schema_version": "flowpilot.state.v1",
            "run_id": "run-test",
            "status": "running",
            "active_route": "route-001",
            "route_version": 1,
            "active_node": "trace-node-001",
        },
    )
    write_json(
        run_root / "execution_frontier.json",
        {
            "schema_version": "flowpilot.execution_frontier.v1",
            "run_id": "run-test",
            "active_route": "route-001",
            "route_version": 1,
            "active_node": "trace-node-001",
            "completed_nodes": [],
        },
    )
    write_live_runtime_roles_slot(root)
    return root


def write_live_runtime_roles_slot(
    root: Path,
    *,
    role: str = "worker",
    agent_id: str = "agent-worker-1-1",
) -> None:
    write_json(
        root / ".flowpilot" / "runs" / "run-test" / "role_binding_ledger.json",
        {
            "schema_version": "flowpilot.role_binding_ledger.v1",
            "run_id": "run-test",
            "role_slots": [
                {
                    "role_key": role,
                    "status": "live_agent_started",
                    "agent_id": agent_id,
                    "binding_open_result": "opened_for_current_task",
                    "opened_for_run_id": "run-test",
                    "opened_after_startup_answers": True,
                    "role_binding_generation": 1,
                    "role_binding_epoch": 1,
                }
            ],
        },
    )


def start_worker_trace(
    package: SyntheticTracePackage | None = None,
) -> SyntheticTraceReplay:
    replay = SyntheticTraceReplay(package or SyntheticTracePackage(name="worker_happy_path"), make_trace_project())
    replay.issue_packet()
    replay.relay_packet()
    replay.issue_lease()
    return replay


def run_worker_result_trace(
    package: SyntheticTracePackage | None = None,
) -> SyntheticTraceReplay:
    replay = start_worker_trace(package)
    replay.ack()
    replay.open_packet_body()
    replay.submit_result()
    return replay
