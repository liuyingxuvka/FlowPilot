"""Shared control-surface helpers for current-run and evidence contracts."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping


RUN_POINTER_FIELD_SETS = (
    ("run_id", "run_root"),
    ("current_run_id", "current_run_root"),
    ("active_run_id", "active_run_root"),
)
CONTROL_SURFACE_SCHEMA = "black_box_flowpilot.control_surface.v1"


@dataclass(frozen=True)
class SafeReadResult:
    path: Path
    ok: bool
    value: Any = None
    error_code: str = ""
    message: str = ""

    def finding(self, *, code: str = "unreadable_evidence", severity: str = "error") -> dict[str, object]:
        return {
            "code": code,
            "severity": severity,
            "summary": self.message or self.error_code,
            "matched_invariant": "evidence_reads_are_structured",
            "evidence": {
                "path": self.path.as_posix(),
                "error_code": self.error_code,
                "message": self.message,
            },
            "minimal_fix": "Read evidence through the shared safe reader and treat unreadable files as audit findings.",
        }


@dataclass(frozen=True)
class CurrentRunResolution:
    root: Path
    ok: bool
    run_id: str = ""
    run_root: Path | None = None
    ledger_path: Path | None = None
    pointer_path: Path | None = None
    source_fields: tuple[str, str] | None = None
    error_code: str = ""
    message: str = ""

    def finding(self, *, severity: str = "error") -> dict[str, object]:
        return {
            "code": "current_run_resolution_failed",
            "severity": severity,
            "summary": self.message or self.error_code,
            "matched_invariant": "current_run_resolution_is_explicit",
            "evidence": {
                "root": self.root.as_posix(),
                "pointer_path": self.pointer_path.as_posix() if self.pointer_path else "",
                "run_id": self.run_id,
                "run_root": self.run_root.as_posix() if self.run_root else "",
                "error_code": self.error_code,
            },
            "minimal_fix": "Write a current pointer with run_id/run_root or legacy current_run_id/current_run_root fields.",
        }


def safe_read_text(path: str | Path) -> SafeReadResult:
    resolved = Path(path)
    try:
        return SafeReadResult(path=resolved, ok=True, value=resolved.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return SafeReadResult(resolved, False, error_code="missing_file", message=f"missing file: {resolved}")
    except UnicodeDecodeError as exc:
        return SafeReadResult(resolved, False, error_code="invalid_utf8", message=f"invalid UTF-8 in {resolved}: {exc}")
    except OSError as exc:
        return SafeReadResult(resolved, False, error_code="unreadable_file", message=f"unreadable file {resolved}: {exc}")


def safe_read_json(path: str | Path, *, require_object: bool = False) -> SafeReadResult:
    text = safe_read_text(path)
    if not text.ok:
        return text
    try:
        value = json.loads(str(text.value))
    except json.JSONDecodeError as exc:
        return SafeReadResult(Path(path), False, error_code="invalid_json", message=f"invalid JSON in {path}: {exc}")
    if require_object and not isinstance(value, dict):
        return SafeReadResult(Path(path), False, error_code="json_not_object", message=f"expected JSON object: {path}")
    return SafeReadResult(Path(path), True, value=value)


def _project_path(root: Path, raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path.resolve()
    return (root / path).resolve()


def _is_run_root(root: Path, run_root: Path, run_id: str) -> bool:
    runs_root = (root / ".flowpilot" / "runs").resolve()
    try:
        run_root.relative_to(runs_root)
    except ValueError:
        return False
    return run_root.name == run_id


def resolve_current_run(root: str | Path, *, run_id: str | None = None) -> CurrentRunResolution:
    """Resolve the current run without falling back to project root or newest run."""

    resolved_root = Path(root).resolve()
    pointer_path = resolved_root / ".flowpilot" / "current.json"
    if run_id:
        candidate = (resolved_root / ".flowpilot" / "runs" / run_id).resolve()
        if not candidate.exists():
            return CurrentRunResolution(
                resolved_root,
                False,
                run_id=run_id,
                run_root=candidate,
                pointer_path=pointer_path,
                error_code="run_root_missing",
                message=f"requested run root does not exist: {candidate}",
            )
        return CurrentRunResolution(
            resolved_root,
            True,
            run_id=run_id,
            run_root=candidate,
            ledger_path=candidate / "ledger.json",
            pointer_path=pointer_path,
            source_fields=("explicit_run_id", "implicit_run_root"),
        )

    current_read = safe_read_json(pointer_path, require_object=True)
    if not current_read.ok:
        return CurrentRunResolution(
            resolved_root,
            False,
            pointer_path=pointer_path,
            error_code=current_read.error_code,
            message=current_read.message,
        )
    current = current_read.value
    assert isinstance(current, dict)

    selected_fields: tuple[str, str] | None = None
    selected_run_id = ""
    selected_run_root_raw = ""
    for run_id_field, run_root_field in RUN_POINTER_FIELD_SETS:
        raw_run_id = current.get(run_id_field)
        raw_run_root = current.get(run_root_field)
        if isinstance(raw_run_id, str) and raw_run_id.strip():
            selected_fields = (run_id_field, run_root_field)
            selected_run_id = raw_run_id.strip()
            selected_run_root_raw = str(raw_run_root or "").strip()
            break
    if not selected_run_id:
        return CurrentRunResolution(
            resolved_root,
            False,
            pointer_path=pointer_path,
            error_code="missing_run_id",
            message="current pointer does not contain run_id, current_run_id, or active_run_id",
        )

    if selected_run_root_raw:
        selected_run_root = _project_path(resolved_root, selected_run_root_raw)
    else:
        selected_run_root = (resolved_root / ".flowpilot" / "runs" / selected_run_id).resolve()

    if not _is_run_root(resolved_root, selected_run_root, selected_run_id):
        return CurrentRunResolution(
            resolved_root,
            False,
            run_id=selected_run_id,
            run_root=selected_run_root,
            pointer_path=pointer_path,
            source_fields=selected_fields,
            error_code="invalid_run_root",
            message="current pointer run_root must be .flowpilot/runs/<run_id>; no project-root fallback is allowed",
        )
    if not selected_run_root.exists():
        return CurrentRunResolution(
            resolved_root,
            False,
            run_id=selected_run_id,
            run_root=selected_run_root,
            pointer_path=pointer_path,
            source_fields=selected_fields,
            error_code="run_root_missing",
            message=f"current run root does not exist: {selected_run_root}",
        )
    ledger_raw = current.get("ledger_path")
    ledger_path = _project_path(resolved_root, str(ledger_raw)) if isinstance(ledger_raw, str) and ledger_raw else selected_run_root / "ledger.json"
    return CurrentRunResolution(
        resolved_root,
        True,
        run_id=selected_run_id,
        run_root=selected_run_root,
        ledger_path=ledger_path,
        pointer_path=pointer_path,
        source_fields=selected_fields,
    )


def build_packet_output_contract(
    *,
    packet_id: str,
    responsibility: str,
    packet_kind: str,
    route_version: int,
    source_generation: int,
) -> dict[str, object]:
    return {
        "schema_version": "black_box_flowpilot.packet_output_contract.v1",
        "contract_id": f"black_box_flowpilot.output.{packet_kind}.v1",
        "packet_id": packet_id,
        "recipient_responsibility": responsibility,
        "route_version": route_version,
        "source_generation": source_generation,
        "ack_authority": "lease_ack_only",
        "result_authority": "sealed_result_envelope",
        "accepted_authority": "runtime_acceptance_gate",
        "ack_result_accepted_separate": True,
        "expected_result_visibility": "sealed",
    }


def build_result_output_contract(packet_envelope: Mapping[str, Any]) -> dict[str, object]:
    output_contract = packet_envelope.get("output_contract")
    if isinstance(output_contract, Mapping):
        return dict(output_contract)
    return build_packet_output_contract(
        packet_id=str(packet_envelope.get("packet_id") or ""),
        responsibility=str(packet_envelope.get("responsibility") or ""),
        packet_kind=str(packet_envelope.get("packet_kind") or "task"),
        route_version=int(packet_envelope.get("route_version") or 0),
        source_generation=int(packet_envelope.get("source_generation") or 0),
    )


def audit_packet_contracts(
    ledger: Mapping[str, Any],
    *,
    required_responsibilities: set[str] | None = None,
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    packets = ledger.get("packets") if isinstance(ledger.get("packets"), Mapping) else {}
    results = ledger.get("results") if isinstance(ledger.get("results"), Mapping) else {}
    current_generation = int(ledger.get("source_generation") or 0)
    observed_roles: set[str] = set()
    for packet_id, packet_obj in packets.items():
        if not isinstance(packet_obj, Mapping):
            findings.append(_packet_finding("packet_not_object", str(packet_id), "packet record is not an object"))
            continue
        envelope = packet_obj.get("envelope")
        if not isinstance(envelope, Mapping):
            findings.append(_packet_finding("packet_envelope_missing", str(packet_id), "packet envelope is missing"))
            continue
        role = str(envelope.get("responsibility") or "")
        observed_roles.add(role)
        missing_fields = [
            field
            for field in (
                "packet_id",
                "packet_kind",
                "route_version",
                "responsibility",
                "objective",
                "body_hash",
                "body_visibility",
                "source_generation",
            )
            if envelope.get(field) in (None, "")
        ]
        output_contract = envelope.get("output_contract")
        if not isinstance(output_contract, Mapping):
            missing_fields.append("output_contract")
        elif output_contract.get("recipient_responsibility") != role:
            findings.append(
                _packet_finding(
                    "packet_output_contract_role_mismatch",
                    str(packet_id),
                    "packet output contract recipient does not match responsibility",
                    {"responsibility": role, "output_contract": dict(output_contract)},
                )
            )
        if missing_fields:
            findings.append(
                _packet_finding(
                    "packet_contract_fields_missing",
                    str(packet_id),
                    "packet envelope lacks required symmetric contract fields",
                    {"missing_fields": missing_fields},
                )
            )
        if packet_obj.get("status") == "accepted" and not packet_obj.get("accepted_result_id"):
            findings.append(_packet_finding("accepted_packet_missing_result", str(packet_id), "accepted packet has no accepted_result_id"))
        if packet_obj.get("accepted_result_id") and packet_obj.get("status") not in {"accepted", "quarantined_after_route_mutation"}:
            findings.append(_packet_finding("accepted_result_status_regressed", str(packet_id), "packet has accepted_result_id but nonterminal status"))
        for result_id in packet_obj.get("result_ids") or []:
            result = results.get(result_id) if isinstance(results, Mapping) else None
            if not isinstance(result, Mapping):
                continue
            envelope_obj = result.get("envelope")
            result_contract = envelope_obj.get("output_contract") if isinstance(envelope_obj, Mapping) else None
            if not isinstance(result_contract, Mapping):
                findings.append(
                    _packet_finding(
                        "result_output_contract_missing",
                        str(packet_id),
                        "result envelope lacks the packet output contract",
                        {"result_id": result_id},
                    )
                )
            elif result_contract.get("packet_id") != str(packet_id):
                findings.append(
                    _packet_finding(
                        "result_output_contract_packet_mismatch",
                        str(packet_id),
                        "result output contract points at a different packet",
                        {"result_id": result_id, "output_contract": dict(result_contract)},
                    )
                )
            envelope_generation = int(envelope_obj.get("evidence_generation") or 0) if isinstance(envelope_obj, Mapping) else 0
            if envelope_generation < current_generation and not result.get("quarantined"):
                findings.append(
                    _packet_finding(
                        "old_generation_result_not_quarantined",
                        str(packet_id),
                        "old-generation result is not quarantined",
                        {"result_id": result_id, "current_generation": current_generation, "result_generation": envelope_generation},
                    )
                )
    if required_responsibilities:
        missing_roles = sorted(required_responsibilities - observed_roles)
        if missing_roles:
            findings.append(
                _packet_finding(
                    "packet_contract_role_coverage_missing",
                    "*",
                    "packet contract audit did not observe every required responsibility",
                    {"missing_responsibilities": missing_roles, "observed_responsibilities": sorted(observed_roles)},
                )
            )
    return findings


def _packet_finding(code: str, packet_id: str, summary: str, evidence: Mapping[str, object] | None = None) -> dict[str, object]:
    payload = {"packet_id": packet_id}
    if evidence:
        payload.update(evidence)
    return {
        "code": code,
        "severity": "error",
        "summary": summary,
        "matched_invariant": "role_packets_share_symmetric_control_surface_contract",
        "evidence": payload,
        "minimal_fix": "Issue packets through the shared packet factory and keep ACK, result, and accepted-result authority separate.",
    }
