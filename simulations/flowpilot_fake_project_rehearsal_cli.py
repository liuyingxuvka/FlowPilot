"""CLI helpers for the black-box FlowPilot fake-project rehearsal."""

from __future__ import annotations

import atexit
import json
import queue
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
ENTRYPOINT = REPO_ROOT / "skills" / "flowpilot" / "assets" / "flowpilot_new.py"
ASSETS = REPO_ROOT / "skills" / "flowpilot" / "assets"
FAKE_STARTUP_TEXT = "Build a fake calculator CLI with docs, tests, FlowGuard evidence, review, validation, and closure."
MIN_ACCEPTED_ROUTE_NODES = 3
ROUTE_PLAN_SCHEMA_VERSION = "flowpilot.route_plan.v1"
CLI_TIMEOUT_SECONDS = 45
FULL_PACKET_CHAIN_BUDGET = 180
PLANNING_PACKET_CHAIN_BUDGET = 120
PLANNING_CHAIN = (
    ("task", "pm"),
    ("flowguard_check", "flowguard_operator"),
    ("review", "reviewer"),
)


class RehearsalFailure(AssertionError):
    """Raised when a black-box rehearsal observation violates the contract."""


def ensure(condition: bool, message: str) -> None:
    if not condition:
        raise RehearsalFailure(message)


def redact_args(args: tuple[str, ...]) -> list[str]:
    redacted: list[str] = []
    redact_next = False
    for arg in args:
        if redact_next:
            redacted.append("<sealed>")
            redact_next = False
            continue
        redacted.append(arg)
        if arg in {"--body", "--startup-text"}:
            redact_next = True
    return redacted


def payload_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not payload:
        return {}
    summary: dict[str, Any] = {"ok": payload.get("ok")}
    if "error" in payload:
        summary["error"] = payload["error"]
    if "mode" in payload:
        summary["mode"] = payload["mode"]
    if "lease_id" in payload:
        summary["lease_id"] = payload["lease_id"]
    if "result_id" in payload:
        summary["result_id"] = payload["result_id"]
    duty = payload.get("foreground_duty")
    if isinstance(duty, dict):
        summary["foreground_duty"] = {
            "action": duty.get("action", ""),
            "final_return_allowed": (duty.get("final_return_preflight") or {}).get("allowed", False),
        }
    action = payload.get("next_action")
    if isinstance(action, dict):
        summary["next_action"] = {
            "action_type": action.get("action_type", ""),
            "responsibility": action.get("responsibility", ""),
            "subject_id": action.get("subject_id", ""),
        }
    return summary


def parse_json(stdout: str) -> dict[str, Any] | None:
    text = stdout.strip()
    if not text:
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


_CLI_WORKER_SCRIPT = r"""
import contextlib
import io
import json
import sys

assets_root = {assets_root!r}
if assets_root not in sys.path:
    sys.path.insert(0, assets_root)

from flowpilot_new_cli import main

for line in sys.stdin:
    request = json.loads(line)
    argv = ["--root", request["root"]]
    if request.get("json_mode"):
        argv.append("--json")
    argv.extend(request["args"])
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            returncode = int(main(argv) or 0)
        except SystemExit as exc:
            code = exc.code
            returncode = int(code) if isinstance(code, int) else 1
        except BaseException as exc:
            returncode = 1
            stderr.write(repr(exc))
    sys.stdout.write(json.dumps({{"returncode": returncode, "stdout": stdout.getvalue(), "stderr": stderr.getvalue()}}, sort_keys=True) + "\n")
    sys.stdout.flush()
""".format(assets_root=str(ASSETS))


class PublicCliWorker:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.process = subprocess.Popen(
            [sys.executable, "-B", "-c", _CLI_WORKER_SCRIPT],
            cwd=REPO_ROOT,
            text=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self._responses: queue.Queue[dict[str, Any] | None] = queue.Queue()
        self._lock = threading.Lock()
        self._reader = threading.Thread(target=self._read_responses, daemon=True)
        self._reader.start()

    def _read_responses(self) -> None:
        assert self.process.stdout is not None
        for line in self.process.stdout:
            try:
                payload = json.loads(line)
                self._responses.put(payload if isinstance(payload, dict) else None)
            except json.JSONDecodeError:
                self._responses.put({"returncode": 1, "stdout": "", "stderr": line})
        self._responses.put(None)

    def run(self, args: tuple[str, ...], *, json_mode: bool) -> subprocess.CompletedProcess[str]:
        if self.process.poll() is not None:
            raise subprocess.TimeoutExpired([sys.executable, "-B", str(ENTRYPOINT), *args], 0)
        assert self.process.stdin is not None
        with self._lock:
            self.process.stdin.write(
                json.dumps(
                    {
                        "root": str(self.root),
                        "json_mode": json_mode,
                        "args": list(args),
                    },
                    sort_keys=True,
                )
                + "\n"
            )
            self.process.stdin.flush()
            try:
                response = self._responses.get(timeout=CLI_TIMEOUT_SECONDS)
            except queue.Empty as exc:
                self.close(kill=True)
                raise subprocess.TimeoutExpired([sys.executable, "-B", str(ENTRYPOINT), *args], CLI_TIMEOUT_SECONDS) from exc
        if response is None:
            raise subprocess.TimeoutExpired([sys.executable, "-B", str(ENTRYPOINT), *args], 0)
        return subprocess.CompletedProcess(
            args=[sys.executable, "-B", str(ENTRYPOINT), "--root", str(self.root), *(("--json",) if json_mode else ()), *args],
            returncode=int(response.get("returncode", 1)),
            stdout=str(response.get("stdout") or ""),
            stderr=str(response.get("stderr") or ""),
        )

    def close(self, *, kill: bool = False) -> None:
        if self.process.poll() is None:
            if kill:
                self.process.kill()
            else:
                try:
                    if self.process.stdin is not None:
                        self.process.stdin.close()
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
            if stream is not None and not stream.closed:
                stream.close()


_CLI_WORKERS: dict[str, PublicCliWorker] = {}
_CLI_WORKERS_LOCK = threading.Lock()


def _cli_worker_for_root(root: Path) -> PublicCliWorker:
    key = str(root.resolve())
    with _CLI_WORKERS_LOCK:
        worker = _CLI_WORKERS.get(key)
        if worker is None or worker.process.poll() is not None:
            worker = PublicCliWorker(root)
            _CLI_WORKERS[key] = worker
        return worker


def close_cli_worker(root: Path) -> None:
    key = str(root.resolve())
    with _CLI_WORKERS_LOCK:
        worker = _CLI_WORKERS.pop(key, None)
    if worker is not None:
        worker.close()


def close_all_cli_workers() -> None:
    with _CLI_WORKERS_LOCK:
        workers = list(_CLI_WORKERS.values())
        _CLI_WORKERS.clear()
    for worker in workers:
        worker.close()


atexit.register(close_all_cli_workers)


def _run_public_cli(root: Path, args: tuple[str, ...], *, json_mode: bool) -> subprocess.CompletedProcess[str]:
    return _cli_worker_for_root(root).run(args, json_mode=json_mode)


def run_cli(root: Path, command_log: list[dict[str, Any]], *args: str, expect_ok: bool = True) -> dict[str, Any]:
    try:
        completed = _run_public_cli(root, args, json_mode=True)
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        command_log.append(
            {
                "args": redact_args(args),
                "returncode": "timeout",
                "payload": None,
                "stderr_excerpt": stderr.strip()[:300],
            }
        )
        raise RehearsalFailure(
            f"CLI command timed out after {CLI_TIMEOUT_SECONDS}s: {args[0]} "
            f"stdout={stdout.strip()[:500]} stderr={stderr.strip()[:300]}"
        ) from exc
    payload = parse_json(completed.stdout)
    command_log.append(
        {
            "args": redact_args(args),
            "returncode": completed.returncode,
            "payload": payload_summary(payload),
            "stderr_excerpt": completed.stderr.strip()[:300],
        }
    )
    if expect_ok:
        ensure(
            completed.returncode == 0,
            f"CLI command failed: {args[0]} stdout={completed.stdout.strip()[:500]} stderr={completed.stderr.strip()[:300]}",
        )
        ensure(payload is not None, f"CLI command did not return JSON: {args[0]}")
        ensure(payload.get("ok") is True, f"CLI command returned ok=false: {args[0]} {payload}")
    return payload or {"ok": False, "error": completed.stderr.strip(), "returncode": completed.returncode}


def run_raw_cli(root: Path, command_log: list[dict[str, Any]], *args: str) -> subprocess.CompletedProcess[str]:
    try:
        completed = _run_public_cli(root, args, json_mode=False)
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        command_log.append(
            {
                "args": redact_args(args),
                "returncode": "timeout",
                "stdout_excerpt": stdout.strip()[:300],
                "stderr_excerpt": stderr.strip()[:300],
            }
        )
        raise RehearsalFailure(
            f"raw CLI command timed out after {CLI_TIMEOUT_SECONDS}s: {args[0]} "
            f"stdout={stdout.strip()[:500]} stderr={stderr.strip()[:300]}"
        ) from exc
    command_log.append(
        {
            "args": redact_args(args),
            "returncode": completed.returncode,
            "stdout_excerpt": completed.stdout[:300],
            "stderr_excerpt": completed.stderr.strip()[:300],
        }
    )
    return completed


def run_internal_rehearsal_start(
    root: Path,
    command_log: list[dict[str, Any]],
    *,
    run_id: str,
    startup_text: str,
) -> dict[str, Any]:
    if str(ASSETS) not in sys.path:
        sys.path.insert(0, str(ASSETS))
    from flowpilot_new import start_run

    payload = start_run(
        root,
        run_id=run_id,
        headless_startup_text=startup_text,
        require_formal_ui=False,
    )
    command_log.append(
        {
            "args": ["internal-rehearsal-start", "--run-id", run_id, "--startup-text", "<sealed>"],
            "returncode": 0,
            "payload": payload_summary(payload),
            "stderr_excerpt": "",
        }
    )
    return payload


def resolve_and_lease_packet(
    root: Path,
    command_log: list[dict[str, Any]],
    *,
    packet_id: str,
    responsibility: str,
    agent_id: str,
    host_kind: str = "fake",
) -> dict[str, Any]:
    return run_cli(
        root,
        command_log,
        "dispatch-current-role",
        "--packet-id",
        packet_id,
        "--responsibility",
        responsibility,
        "--host-kind",
        host_kind,
        "--agent-id",
        agent_id,
    )


def open_current_packet_inputs(
    root: Path,
    command_log: list[dict[str, Any]],
    *,
    lease_id: str,
    packet: dict[str, Any],
) -> dict[str, Any]:
    packet_id = str(packet.get("packet_id") or "")
    ensure(packet_id, f"cannot open packet inputs without packet_id: {packet}")
    opened_packet = run_cli(root, command_log, "open-packet", "--lease-id", lease_id, "--packet-id", packet_id)
    if opened_packet.get("authorized_input_materials_delivered") is False:
        raise RehearsalFailure(f"open-packet did not deliver authorized input materials for {packet_id}")
    opened_projection = opened_packet.get("packet")
    ensure(isinstance(opened_projection, dict), f"open-packet did not return packet projection for {packet_id}")
    handoff_contract = opened_projection.get("current_handoff_contract")
    if isinstance(handoff_contract, dict):
        if not opened_projection.get("route_scope"):
            opened_projection["route_scope"] = str(handoff_contract.get("route_scope") or "")
        manifest = handoff_contract.get("input_material_manifest")
        if isinstance(manifest, dict):
            if not opened_projection.get("route_node_id"):
                opened_projection["route_node_id"] = str(manifest.get("route_node_id") or "")
            if not opened_projection.get("target_result_id"):
                opened_projection["target_result_id"] = str(manifest.get("target_result_id") or "")
    return opened_projection


def reset_scenario_root(work_root: Path, name: str) -> Path:
    root = (work_root / name).resolve()
    work_root_resolved = work_root.resolve()
    ensure(str(root).startswith(str(work_root_resolved)), f"refusing to reset path outside work root: {root}")
    if root.exists():
        for attempt in range(5):
            try:
                shutil.rmtree(root)
                break
            except OSError:
                if attempt == 4:
                    raise
                time.sleep(0.2)
    root.mkdir(parents=True, exist_ok=True)
    return root


def status_projection(root: Path, command_log: list[dict[str, Any]]) -> dict[str, Any]:
    payload = run_cli(root, command_log, "status")
    projection = payload.get("status")
    ensure(isinstance(projection, dict), "status command did not return a projection")
    return projection


def packet_row(projection: dict[str, Any], packet_id: str) -> dict[str, Any]:
    for packet in projection.get("packets", []):
        if packet.get("packet_id") == packet_id:
            return packet
    raise RehearsalFailure(f"missing packet row in public status: {packet_id}")


def assert_public_projection_is_sealed(projection: dict[str, Any]) -> None:
    serialized = json.dumps(projection, sort_keys=True)
    ensure(projection.get("sealed_bodies_visible") is False, "public status claims sealed bodies are visible")
    ensure(FAKE_STARTUP_TEXT not in serialized, "public status leaked fake startup text")
    ensure("SEALED_RESULT_BODY" not in serialized, "public status leaked sealed fake AI result body")
    for packet in projection.get("packets", []):
        ensure(packet.get("sealed_body_hidden") is True, f"packet body is not marked hidden: {packet}")


def _route_plan_body(*, node_count: int = MIN_ACCEPTED_ROUTE_NODES) -> str:
    node_templates = [
        {
            "node_id": "node-001",
            "title": "Implement fake calculator CLI behavior",
            "responsibility": "worker",
            "modeled_target": "development_process",
            "acceptance_criteria": [
                "The fake calculator behavior is implemented in the bounded scenario.",
                "Worker evidence names current files and command results.",
            ],
        },
        {
            "node_id": "node-002",
            "title": "Validate fake project evidence",
            "responsibility": "worker",
            "modeled_target": "model_test_alignment",
            "acceptance_criteria": [
                "FlowGuard and ordinary validation evidence are current.",
                "Evidence can be challenged by an independent reviewer.",
            ],
        },
        {
            "node_id": "node-003",
            "title": "Assemble final closure package",
            "responsibility": "worker",
            "modeled_target": "development_process",
            "acceptance_criteria": [
                "The final route-wide ledger accounts for all effective nodes.",
                "The public status remains body-free at terminal completion.",
            ],
        },
    ]
    ensure(1 <= node_count <= len(node_templates), f"unsupported fake route node count: {node_count}")
    return json.dumps(
        {
            "decision": "pass",
            "schema_version": ROUTE_PLAN_SCHEMA_VERSION,
            "nodes": node_templates[:node_count],
        },
        sort_keys=True,
    )


def _node_acceptance_plan_body(packet: dict[str, Any]) -> str:
    node_id = str(packet.get("route_node_id") or "")
    return json.dumps(
        {
            "decision": "pass",
            "pm_visible_summary": [f"PM accepted a current node plan for {node_id or 'the active node'}."],
            "route_node_id": node_id,
            "proof_obligations": ["implementation evidence", "FlowGuard evidence", "review", "validation"],
            "repair_policy": "same_node_repair_default",
            "low_quality_success_risks": ["existence-only evidence", "missing skill evidence"],
            "node_context_package": {
                "node_id": node_id,
                "purpose": "Complete the current route node with bounded worker execution, FlowGuard checks, review, and validation.",
                "acceptance_criteria": [
                    "worker result satisfies the node packet",
                    "pre-work and post-result FlowGuard evidence are current",
                    "reviewer independently challenges the node outcome",
                ],
                "relevant_references": ["route node contract", "high standard contract", "runtime ledger"],
                "evidence_targets": ["worker result body", "FlowGuard report", "reviewer report", "validation output"],
                "inspection_targets": ["changed files", "command output", "model artifacts", "runtime ledger"],
                "known_risks": ["existence-only evidence", "stale generation", "review without active inspection"],
                "flowguard_targets": ["development-process route", "model-test alignment where applicable"],
                "reviewer_starting_points": ["worker result", "node context package", "FlowGuard reports", "validation evidence"],
                "high_standard_requirement_ids": ["hsr-001"],
                "low_quality_success_risks": ["existence-only evidence", "generic pass without hard-part proof"],
                "semantic_downgrade_risks": ["accepted node does not prove user-visible completion"],
                "work_packet_projection": ["copy hard requirements, risk probes, and test obligations into Worker, FlowGuard, Reviewer, and PM disposition packets"],
                "final_user_intent_checks": ["node evidence advances the sealed startup request"],
                "structure_hygiene_expectation": ["no compatibility branch, fallback parser, or stale artifact may be introduced"],
                "direct_evidence_closure_rules": ["report-only closure is not sufficient for covered hard requirements"],
                "test_obligation_matrix": {
                    "pre_worker": [
                        {
                            "obligation_id": f"test-{node_id or 'active'}-001",
                            "source": "node_acceptance_plan",
                            "required_test_kind": "targeted_current_validation",
                            "owner_role": "worker",
                            "expected_evidence": "current validation evidence",
                            "freshness_rule": "after worker result for the current node",
                            "pm_disposition": "pending",
                        }
                    ]
                },
            },
        }
    )


def _high_standard_contract_body() -> str:
    return json.dumps(
        {
            "requirements": [
                {
                    "requirement_id": "hsr-001",
                    "classification": "hard_current",
                    "summary": "Complete the fake project to a high standard.",
                    "source_user_intent": "sealed_startup_intake",
                    "evidence_rule": "Direct current evidence or explicit waiver required.",
                    "closure_blocking": True,
                    "report_only_closure_allowed": False,
                }
            ],
        },
        sort_keys=True,
    )


def _discovery_body() -> str:
    return json.dumps(
        {
            "decision": "pass",
            "pm_visible_summary": ["PM confirmed current startup material and local skill inventory."],
            "material_sources": ["startup"],
            "material_sufficiency": "sufficient_for_route_planning",
            "local_skill_inventory": ["flowguard-development-process-flow"],
            "candidate_only_skill_policy": True,
        },
        sort_keys=True,
    )


def _skill_standard_body() -> str:
    return json.dumps(
        {
            "decision": "pass",
            "pm_visible_summary": ["PM set current skill obligations for the fake project route."],
            "obligations": [
                {
                    "obligation_id": "skill-std-001",
                    "skill": "flowguard-development-process-flow",
                    "classification": "required",
                    "role_use": "flowguard_operator",
                    "use_context": "node_validation",
                    "evidence_required": "current-run FlowGuard work order",
                    "closure_blocking": True,
                }
            ],
        },
        sort_keys=True,
    )


def _generic_current_result_body(packet: dict[str, Any]) -> str:
    packet_id = str(packet.get("packet_id") or "")
    packet_kind = str(packet.get("packet_kind") or "task")
    route_scope = str(packet.get("route_scope") or "")
    summary_subject = f"{packet_kind} result for {packet_id}"
    if route_scope:
        summary_subject += f" in {route_scope}"
    return json.dumps(
        {
            "decision": "pass",
            "pm_visible_summary": [f"Fake AI submitted current-contract {summary_subject}."],
        },
        sort_keys=True,
    )


def _packet_result_contract_body(packet: dict[str, Any]) -> str:
    if str(ASSETS) not in sys.path:
        sys.path.insert(0, str(ASSETS))
    from flowpilot_core_runtime import packet_result_contracts

    family_id = packet_result_contracts.packet_result_family_id(packet)
    payload = packet_result_contracts.minimal_valid_shape_for_family(family_id)
    packet_id = str(packet.get("packet_id") or "")
    packet_kind = str(packet.get("packet_kind") or "task")
    route_scope = str(packet.get("route_scope") or "")
    summary_subject = f"{packet_kind} result for {packet_id}"
    if route_scope:
        summary_subject += f" in {route_scope}"
    if "pm_visible_summary" in payload:
        payload["pm_visible_summary"] = [f"Fake AI submitted current-contract {summary_subject}."]
    return json.dumps(payload, sort_keys=True)


def current_contract_body_for_packet(
    packet: dict[str, Any],
    *,
    pm_disposition_decision: str = "accept",
    route_node_count: int = MIN_ACCEPTED_ROUTE_NODES,
) -> str:
    packet_kind = str(packet.get("packet_kind") or "")
    route_scope = str(packet.get("route_scope") or "")
    packet_id = str(packet.get("packet_id") or "")
    if packet_kind == "task" and route_scope == "high_standard_contract":
        return _high_standard_contract_body()
    if packet_kind == "task" and route_scope == "discovery":
        return _discovery_body()
    if packet_kind == "task" and route_scope == "skill_standard":
        return _skill_standard_body()
    if packet_kind == "task" and route_scope == "planning":
        return _route_plan_body(node_count=route_node_count)
    if packet_kind == "task" and route_scope == "node_acceptance_plan":
        return _node_acceptance_plan_body(packet)
    if packet_kind in {"flowguard_check", "review"}:
        return _packet_result_contract_body(packet)
    if packet_kind == "pm_disposition":
        return json.dumps(
            {
                "decision": pm_disposition_decision,
                "reason": f"fake PM disposition {pm_disposition_decision}",
                "covered_requirement_ids": ["hsr-001"] if pm_disposition_decision == "accept" else [],
                "reviewer_absorption": "PM absorbed current Reviewer challenge fields.",
                "flowguard_absorption": "PM absorbed current FlowGuard boundary and missing-test fields.",
                "residual_risk_disposition": "No unresolved residual risk remains for this fake node.",
                "semantic_downgrade_disposition": "No semantic downgrade remains for this fake node.",
                "validation_evidence_ids": ["fake-current-validation"],
                "waived_requirement_ids": [],
            },
            sort_keys=True,
        )
    return _generic_current_result_body(packet)


def complete_full_packet_chain(
    root: Path,
    command_log: list[dict[str, Any]],
    current_payload: dict[str, Any],
    *,
    first_pm_disposition_decision: str = "accept",
    route_node_count: int = MIN_ACCEPTED_ROUTE_NODES,
    min_accepted_route_nodes: int = MIN_ACCEPTED_ROUTE_NODES,
) -> dict[str, Any]:
    completed_packets: list[dict[str, str]] = []
    pm_disposition_count = 0
    for step_index in range(FULL_PACKET_CHAIN_BUDGET):
        action = current_payload.get("next_action")
        ensure(isinstance(action, dict), f"missing next action at step {step_index}")
        if action.get("action_type") == "terminal_complete":
            break
        ensure(
            action.get("action_type") == "dispatch_current_role",
            f"expected role assignment action at step {step_index}: {action}",
        )
        responsibility = str(action.get("responsibility", ""))
        packet_id = str(action.get("subject_id", ""))
        ensure(packet_id, f"missing packet id at step {step_index}")

        lease_payload = resolve_and_lease_packet(
            root,
            command_log,
            packet_id=packet_id,
            responsibility=responsibility,
            agent_id=f"fake-current-{step_index}",
        )
        lease_id = str(lease_payload.get("lease_id", ""))
        ensure(lease_id, f"missing lease id for {packet_id}")
        ensure(lease_payload["next_action"]["action_type"] == "wait_for_ack", f"expected wait_for_ack: {lease_payload}")

        ack_payload = run_cli(root, command_log, "ack", "--lease-id", lease_id, "--packet-id", packet_id)
        ensure(ack_payload["next_action"]["action_type"] == "wait_for_result", f"expected wait_for_result: {ack_payload}")
        packet = open_current_packet_inputs(root, command_log, lease_id=lease_id, packet={"packet_id": packet_id})
        packet_kind = str(packet.get("packet_kind", ""))
        ensure(packet_kind, f"missing packet kind for {packet_id}: {packet}")
        ensure(
            packet_kind != "task" or packet.get("route_scope") != "planning" or responsibility == "pm",
            f"planning task packet must be PM-owned: {packet}",
        )
        decision = "accept"
        if packet_kind == "pm_disposition":
            pm_disposition_count += 1
            decision = first_pm_disposition_decision if pm_disposition_count == 1 else "accept"
        body = current_contract_body_for_packet(
            packet,
            pm_disposition_decision=decision,
            route_node_count=route_node_count,
        )

        current_payload = run_cli(
            root,
            command_log,
            "submit-result",
            "--lease-id",
            lease_id,
            "--packet-id",
            packet_id,
            "--body",
            body,
        )
        completed_packets.append({"packet_id": packet_id, "packet_kind": packet_kind, "lease_id": lease_id})
    else:
        raise RehearsalFailure(
            f"packet chain exceeded recursive route budget={FULL_PACKET_CHAIN_BUDGET}; "
            f"last_next_action={current_payload.get('next_action')}"
        )

    final_action = current_payload.get("next_action", {})
    ensure(final_action.get("action_type") == "terminal_complete", f"final action was not terminal_complete: {final_action}")
    projection = status_projection(root, command_log)
    assert_public_projection_is_sealed(projection)
    ensure(projection.get("next_action", {}).get("action_type") == "terminal_complete", "public status is not terminal")
    ensure(projection.get("closure", {}).get("decision") == "complete", "closure did not complete")
    guard = projection.get("lifecycle_guard", {})
    ensure(guard.get("decision") == "terminal_return", f"terminal guard did not allow terminal return: {guard}")
    ensure(guard.get("controller_stop_allowed") is True, f"terminal guard did not allow Controller stop: {guard}")
    duty = projection.get("foreground_duty", {})
    ensure(duty.get("action") == "terminal_return", f"terminal foreground duty did not allow return: {duty}")
    ensure(duty.get("final_return_preflight", {}).get("allowed") is True, f"terminal final preflight failed: {duty}")

    packet_kinds = [packet.get("packet_kind") for packet in projection.get("packets", [])]
    route_nodes = projection.get("route_nodes", [])
    accepted_nodes = [node for node in route_nodes if node.get("status") == "accepted"]
    ensure(len(accepted_nodes) >= min_accepted_route_nodes, f"recursive route did not accept enough nodes: {route_nodes}")
    ensure(packet_kinds.count("pm_disposition") >= min_accepted_route_nodes, f"PM dispositions missing from chain: {packet_kinds}")
    ensure(all(packet.get("status") == "accepted" for packet in projection.get("packets", [])), "not all packets are accepted")
    ensure(not [lease for lease in projection.get("leases", []) if lease.get("status") == "active"], "terminal status has active leases")
    ensure(all(lease.get("ack_received") for lease in projection.get("leases", [])), "a terminal lease is missing ACK")
    ensure(all(lease.get("packet_id") for lease in projection.get("leases", [])), "a terminal lease is missing packet id")
    ensure(projection.get("flowguard") and projection["flowguard"][0].get("decision") == "pass", "FlowGuard pass evidence missing")
    ensure(
        projection.get("validation_evidence") and projection["validation_evidence"][0].get("status") == "passed",
        "validation evidence missing",
    )
    ensure(projection.get("system_closures"), "system closure evidence missing")
    ensure("validation" not in packet_kinds, f"ordinary path still issued validator packets: {packet_kinds}")
    ensure("closure" not in packet_kinds, f"ordinary path still issued closure packets: {packet_kinds}")
    ensure(not projection.get("blockers"), f"terminal public status has blockers: {projection.get('blockers')}")
    return {
        "terminal_action": final_action,
        "packet_kinds": packet_kinds,
        "accepted_route_nodes": [node.get("node_id") for node in accepted_nodes],
        "completed_packets": completed_packets,
        "lease_count": len(projection.get("leases", [])),
        "sealed_bodies_visible": projection.get("sealed_bodies_visible"),
    }


def complete_planning_chain_only(
    root: Path,
    command_log: list[dict[str, Any]],
    current_payload: dict[str, Any],
) -> dict[str, Any]:
    for step_index in range(PLANNING_PACKET_CHAIN_BUDGET):
        action = current_payload.get("next_action")
        ensure(isinstance(action, dict), "missing planning next action")
        ensure(action.get("action_type") == "dispatch_current_role", f"expected planning role dispatch action: {action}")
        responsibility = str(action.get("responsibility", ""))
        packet_id = str(action.get("subject_id", ""))
        lease_payload = resolve_and_lease_packet(
            root,
            command_log,
            packet_id=packet_id,
            responsibility=responsibility,
            agent_id=f"fake-planning-{step_index}",
        )
        lease_id = str(lease_payload["lease_id"])
        run_cli(root, command_log, "ack", "--lease-id", lease_id, "--packet-id", packet_id)
        packet = open_current_packet_inputs(root, command_log, lease_id=lease_id, packet={"packet_id": packet_id})
        packet_kind = str(packet.get("packet_kind", ""))
        route_scope = str(packet.get("route_scope", ""))
        ensure(packet_kind in {"task", "flowguard_check", "review"}, f"wrong planning packet kind: {packet}")
        ensure(responsibility == packet.get("responsibility"), f"wrong planning responsibility: {action}")
        body = current_contract_body_for_packet(packet)
        current_payload = run_cli(
            root,
            command_log,
            "submit-result",
            "--lease-id",
            lease_id,
            "--packet-id",
            packet_id,
            "--body",
            body,
        )
        if packet_kind == "review" and route_scope == "planning":
            break
    else:
        raise RehearsalFailure(
            f"planning chain exceeded high-standard gate budget={PLANNING_PACKET_CHAIN_BUDGET}; "
            f"last_next_action={current_payload.get('next_action')}"
        )
    projection = status_projection(root, command_log)
    assert_public_projection_is_sealed(projection)
    next_action = projection.get("next_action", {})
    ensure(next_action.get("action_type") == "dispatch_current_role", "planning chain did not continue to node planning")
    next_packet = packet_row(projection, str(next_action.get("subject_id", "")))
    ensure(
        next_packet.get("route_scope") == "node_acceptance_plan",
        f"planning chain did not stop at node acceptance planning: {next_packet}",
    )
    ensure(next_action.get("responsibility") == "pm", f"node acceptance plan is not PM-owned: {next_action}")
    ensure(projection.get("closure", {}).get("decision") != "complete", "planning chain reached terminal closure")
    guard = projection.get("lifecycle_guard", {})
    ensure(guard.get("controller_stop_allowed") is False, f"planning guard allowed Controller stop: {guard}")
    duty = projection.get("foreground_duty", {})
    ensure(duty.get("action") == "process_next_action", f"planning duty did not continue: {duty}")
    ensure(duty.get("subject_id") == str(next_action.get("subject_id", "")), f"planning duty lost next packet: {duty}")
    ensure(duty.get("final_return_preflight", {}).get("allowed") is False, f"planning duty allowed final return: {duty}")
    ensure(len(projection.get("route_nodes", [])) >= MIN_ACCEPTED_ROUTE_NODES, "planning chain did not materialize route nodes")
    return {
        "next_action": next_action,
        "next_route_scope": next_packet.get("route_scope"),
        "route_nodes": projection.get("route_nodes", []),
        "closure": projection.get("closure", {}),
    }


def start_rehearsal(root: Path, command_log: list[dict[str, Any]], run_id: str) -> dict[str, Any]:
    payload = run_internal_rehearsal_start(root, command_log, run_id=run_id, startup_text=FAKE_STARTUP_TEXT)
    ensure(payload.get("mode") == "rehearsal", "headless startup should be recorded as rehearsal mode")
    ensure(
        payload.get("next_action", {}).get("action_type") == "dispatch_current_role",
        "startup did not request first role dispatch",
    )
    ensure(payload.get("next_action", {}).get("responsibility") == "pm", "startup did not request PM first")
    projection = payload.get("status", {})
    ensure(isinstance(projection, dict), "startup did not include public status")
    assert_public_projection_is_sealed(projection)
    duty = projection.get("foreground_duty", {})
    ensure(duty.get("action") == "process_next_action", f"startup foreground duty did not process next action: {duty}")
    ensure(duty.get("final_return_preflight", {}).get("allowed") is False, f"startup allowed final return: {duty}")
    return payload
