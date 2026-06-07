"""Small CLI for the FlowPilot core runtime."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

try:  # pragma: no cover - direct execution harness path.
    from . import cockpit, router, run_shell, runtime
except ImportError:  # pragma: no cover
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from flowpilot_core_runtime import cockpit, router, run_shell, runtime  # type: ignore


def _print(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True) + "\n", end="")


def _demo_ledger() -> dict:
    ledger = runtime.new_ledger(
        "Build a clean isolated FlowPilot core runtime",
        "Complete only with current route, accepted result, review, FlowGuard, and validation evidence.",
    )
    runtime.create_route(ledger, "Single packet clean runtime demo", ["implement runtime"])
    packet_id = runtime.issue_task_packet(
        ledger,
        "worker",
        "Produce the runtime demo result",
        "sealed worker instruction body",
    )
    worker = runtime.lease_agent(ledger, "worker", agent_id="worker-demo")
    runtime.assign_packet(ledger, packet_id, worker)
    runtime.ack_lease(ledger, worker, packet_id)
    result_id = runtime.submit_result(
        ledger,
        worker,
        packet_id,
        "sealed worker result body",
        evidence_ids=["unit-demo"],
    )
    order_id = runtime.create_flowguard_work_order(
        ledger,
        "development_process",
        "done_claim",
        packet_id,
    )
    runtime.complete_flowguard_work_order(ledger, order_id, evidence_id="fg-demo")
    reviewer = runtime.lease_agent(ledger, "reviewer", agent_id="reviewer-demo")
    runtime.review_result(ledger, result_id, reviewer)
    runtime.record_validation_evidence(ledger, "validation-demo")
    runtime.attempt_final_closure(ledger, "validation-demo")
    return ledger


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    demo = sub.add_parser("demo", help="create a deterministic complete demo ledger")
    demo.add_argument("--json-out", type=Path, default=None)

    start = sub.add_parser("start", help="create a current-run shell")
    start.add_argument("--root", type=Path, default=Path("."))
    start.add_argument("--goal", required=True)
    start.add_argument("--acceptance-contract", required=True)
    start.add_argument("--run-id", default=None)

    intake = sub.add_parser("record-startup", help="record a sealed startup-intake result into the current run")
    intake.add_argument("--root", type=Path, default=Path("."))
    intake.add_argument("--result", type=Path, required=True)

    status = sub.add_parser("status", help="render public console status for a ledger")
    status.add_argument("ledger", type=Path)

    cockpit_status = sub.add_parser("cockpit", help="render projection-only current-run Cockpit status")
    cockpit_status.add_argument("--root", type=Path, default=Path("."))

    event = sub.add_parser("event", help="submit a projection-only Cockpit event for the current run")
    event.add_argument("--root", type=Path, default=Path("."))
    event.add_argument("--event-type", required=True)

    args = parser.parse_args()
    if args.command == "demo":
        ledger = _demo_ledger()
        if args.json_out:
            runtime.save_ledger(ledger, args.json_out)
        _print({"ok": ledger["closure"]["decision"] == "complete", "console": runtime.render_console(ledger)})
        return 0
    if args.command == "start":
        shell = run_shell.create_run_shell(
            args.root,
            args.goal,
            args.acceptance_contract,
            run_id=args.run_id,
        )
        _print({"ok": True, "run": shell.to_json()})
        return 0
    if args.command == "record-startup":
        shell = run_shell.load_run_shell(args.root)
        record = run_shell.record_startup_intake_result(shell, args.result)
        _print({"ok": True, "startup_intake": record, "next_action": router.router_next_action(run_shell.load_run_ledger(shell)).to_json()})
        return 0
    if args.command == "status":
        _print(runtime.render_console(runtime.load_ledger(args.ledger)))
        return 0
    if args.command == "cockpit":
        shell = run_shell.load_run_shell(args.root)
        ledger = run_shell.load_run_ledger(shell)
        _print(cockpit.render_status(ledger))
        return 0
    if args.command == "event":
        shell = run_shell.load_run_shell(args.root)
        ledger = run_shell.load_run_ledger(shell)
        response = router.apply_router_event(ledger, args.event_type)
        run_shell.save_run_ledger(shell, ledger)
        _print({"ok": response.get("accepted", False), "event": response})
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
