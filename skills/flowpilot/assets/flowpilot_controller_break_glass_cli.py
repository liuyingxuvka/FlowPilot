"""CLI wiring for Controller break-glass helpers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


def _core() -> Any:
    for name in ("flowpilot_controller_break_glass", "__main__"):
        module = sys.modules.get(name)
        if getattr(module, "INCIDENT_SCHEMA", None):
            return module
    raise RuntimeError("flowpilot_controller_break_glass core module is not loaded")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=_core().__doc__)
    parser.add_argument("--root", default=".", help="Project root")
    parser.add_argument("--run-root", default=None, help="Run root, defaults to .flowpilot/current.json")
    sub = parser.add_subparsers(dest="command", required=True)

    open_cmd = sub.add_parser("open-incident")
    open_cmd.add_argument("--incident-id", required=True)
    open_cmd.add_argument("--trigger-summary", required=True)
    open_cmd.add_argument("--failure-kind", required=True)
    open_cmd.add_argument("--source", action="append", default=[])
    open_cmd.add_argument("--normal-lane", action="append", default=[])

    patch_cmd = sub.add_parser("record-patch")
    patch_cmd.add_argument("--incident-id", required=True)
    patch_cmd.add_argument("--patch-id", required=True)
    patch_cmd.add_argument("--reason", required=True)
    patch_cmd.add_argument("--touched-path", action="append", default=[])
    patch_cmd.add_argument("--validation", action="append", default=[])

    finalize_patch_cmd = sub.add_parser("finalize-patch")
    finalize_patch_cmd.add_argument("--patch-id", required=True)
    finalize_patch_cmd.add_argument("--disposition", required=True)

    close_cmd = sub.add_parser("close-incident")
    close_cmd.add_argument("--incident-id", required=True)
    close_cmd.add_argument("--disposition", required=True)

    blocker_cmd = sub.add_parser("record-control-blocker")
    blocker_cmd.add_argument("--blocker-id", required=True)
    blocker_cmd.add_argument("--family-id", required=True)
    blocker_cmd.add_argument("--status", required=True)
    blocker_cmd.add_argument("--summary", required=True)
    blocker_cmd.add_argument("--source", action="append", default=[])
    blocker_cmd.add_argument("--recovery-transaction-id", default=None)
    blocker_cmd.add_argument("--historical", action="store_true")
    blocker_cmd.add_argument("--requires-body-access", action="store_true")
    blocker_cmd.add_argument("--classification", default="current_repair")

    recovery_cmd = sub.add_parser("open-recovery")
    recovery_cmd.add_argument("--transaction-id", required=True)
    recovery_cmd.add_argument("--incident-id", required=True)
    recovery_cmd.add_argument("--trigger-summary", required=True)
    recovery_cmd.add_argument("--failure-kind", required=True)
    recovery_cmd.add_argument("--blocker-id", action="append", default=[])
    recovery_cmd.add_argument("--family-id", action="append", default=[])
    recovery_cmd.add_argument("--normal-lane", action="append", default=[])
    recovery_cmd.add_argument("--controller-generation-id", required=True)
    recovery_cmd.add_argument("--flowguard-obligation", action="append", default=[])

    body_cmd = sub.add_parser("request-body-access")
    body_cmd.add_argument("--transaction-id", required=True)
    body_cmd.add_argument("--grant-id", required=True)
    body_cmd.add_argument("--body-path", required=True)
    body_cmd.add_argument("--reason", required=True)
    body_cmd.add_argument("--unavailable-role-lane", action="append", default=[])
    body_cmd.add_argument("--post-recovery-reviewer", default="project_manager")

    reinject_cmd = sub.add_parser("record-controller-reinjection")
    reinject_cmd.add_argument("--transaction-id", required=True)
    reinject_cmd.add_argument("--reinjection-id", required=True)
    reinject_cmd.add_argument("--previous-generation-id", required=True)
    reinject_cmd.add_argument("--next-generation-id", required=True)
    reinject_cmd.add_argument("--controller-core-path", required=True)
    reinject_cmd.add_argument("--boundary-proof-path", default=None)
    reinject_cmd.add_argument("--proof-artifact", action="append", default=[])

    close_recovery_cmd = sub.add_parser("close-recovery")
    close_recovery_cmd.add_argument("--transaction-id", required=True)
    close_recovery_cmd.add_argument("--disposition", required=True)
    close_recovery_cmd.add_argument("--same-family-evidence", action="append", default=[])
    return parser


def main(argv: list[str] | None = None) -> int:
    core = _core()
    parser = build_parser()
    args = parser.parse_args(argv)
    project_root = Path(args.root).resolve()
    run_root = core.current_run_root(project_root, args.run_root).resolve()
    if args.command == "open-incident":
        result = core.open_incident(
            project_root,
            run_root,
            incident_id=args.incident_id,
            trigger_summary=args.trigger_summary,
            failure_kind=args.failure_kind,
            sources=args.source,
            normal_lanes=args.normal_lane,
        )
    elif args.command == "record-patch":
        result = core.record_patch(
            project_root,
            run_root,
            incident_id=args.incident_id,
            patch_id=args.patch_id,
            reason=args.reason,
            touched_paths=args.touched_path,
            validation=args.validation,
        )
    elif args.command == "finalize-patch":
        result = core.finalize_patch(project_root, run_root, patch_id=args.patch_id, disposition=args.disposition)
    elif args.command == "close-incident":
        result = core.close_incident(project_root, run_root, incident_id=args.incident_id, disposition=args.disposition)
    elif args.command == "record-control-blocker":
        result = core.record_control_plane_blocker(
            project_root,
            run_root,
            blocker_id=args.blocker_id,
            family_id=args.family_id,
            status=args.status,
            summary=args.summary,
            sources=args.source,
            recovery_transaction_id=args.recovery_transaction_id,
            current=not args.historical,
            requires_body_access=args.requires_body_access,
            classification=args.classification,
        )
    elif args.command == "open-recovery":
        result = core.open_recovery_transaction(
            project_root,
            run_root,
            transaction_id=args.transaction_id,
            incident_id=args.incident_id,
            trigger_summary=args.trigger_summary,
            failure_kind=args.failure_kind,
            blocker_ids=args.blocker_id,
            family_ids=args.family_id,
            normal_lanes=args.normal_lane,
            controller_generation_id=args.controller_generation_id,
            flowguard_obligations=args.flowguard_obligation,
        )
    elif args.command == "request-body-access":
        result = core.request_body_access(
            project_root,
            run_root,
            transaction_id=args.transaction_id,
            grant_id=args.grant_id,
            body_path=args.body_path,
            reason=args.reason,
            unavailable_role_lanes=args.unavailable_role_lane,
            post_recovery_reviewer=args.post_recovery_reviewer,
        )
    elif args.command == "record-controller-reinjection":
        result = core.record_controller_reinjection(
            project_root,
            run_root,
            transaction_id=args.transaction_id,
            reinjection_id=args.reinjection_id,
            previous_generation_id=args.previous_generation_id,
            next_generation_id=args.next_generation_id,
            controller_core_path=args.controller_core_path,
            boundary_proof_path=args.boundary_proof_path,
            proof_artifacts=args.proof_artifact,
        )
    elif args.command == "close-recovery":
        result = core.close_recovery_transaction(
            project_root,
            run_root,
            transaction_id=args.transaction_id,
            disposition=args.disposition,
            same_family_evidence=args.same_family_evidence,
        )
    else:  # pragma: no cover
        parser.error(f"Unknown command: {args.command}")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0
