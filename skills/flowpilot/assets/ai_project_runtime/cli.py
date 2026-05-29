"""Small CLI for the clean AI project runtime."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:  # pragma: no cover - direct script fallback.
    from . import runtime
except ImportError:  # pragma: no cover
    import runtime  # type: ignore


def _print(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True) + "\n", end="")


def _demo_ledger() -> dict:
    ledger = runtime.new_ledger(
        "Build a clean isolated AI project runtime",
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

    status = sub.add_parser("status", help="render public console status for a ledger")
    status.add_argument("ledger", type=Path)

    args = parser.parse_args()
    if args.command == "demo":
        ledger = _demo_ledger()
        if args.json_out:
            runtime.save_ledger(ledger, args.json_out)
        _print({"ok": ledger["closure"]["decision"] == "complete", "console": runtime.render_console(ledger)})
        return 0
    if args.command == "status":
        _print(runtime.render_console(runtime.load_ledger(args.ledger)))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
