"""Argument parser for the FlowPilot packet runtime CLI."""

from __future__ import annotations

import argparse


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create and validate physical FlowPilot packet envelope/body files.")
    parser.add_argument("--root", default=".", help="Project root containing .flowpilot")
    subparsers = parser.add_subparsers(dest="command", required=True)

    issue = subparsers.add_parser("issue", help="Write packet_envelope.json and packet_body.md")
    issue.add_argument("--run-id", default="")
    issue.add_argument("--packet-id", required=True)
    issue.add_argument("--from-role", required=True)
    issue.add_argument("--to-role", required=True)
    issue.add_argument("--node-id", required=True)
    issue.add_argument("--body-text", default="")
    issue.add_argument("--body-file", default="")
    issue.add_argument("--return-to", default="controller")
    issue.add_argument("--next-holder", default="")
    issue.add_argument("--replacement-for", default="")

    intake = subparsers.add_parser("user-intake", help="Write the first user prompt packet for PM")
    intake.add_argument("--run-id", default="")
    intake.add_argument("--packet-id", required=True)
    intake.add_argument("--node-id", required=True)
    intake.add_argument("--body-text", default="")
    intake.add_argument("--body-file", default="")
    intake.add_argument("--startup-options-json", default="")
    intake.add_argument("--background-agents-authorized", action="store_true")
    intake.add_argument("--heartbeat-requested", action="store_true")
    intake.add_argument("--display-surface", default="")

    handoff = subparsers.add_parser("handoff", help="Print controller-visible envelope handoff only")
    handoff.add_argument("--envelope-path", required=True)

    relay = subparsers.add_parser("relay", help="Controller signs and relays an envelope without opening body")
    relay.add_argument("--envelope-path", required=True)
    relay.add_argument("--controller-agent-id", default="controller")
    relay.add_argument("--received-from-role", default="")
    relay.add_argument("--relayed-to-role", default="")
    relay.add_argument("--holder-before", default="")
    relay.add_argument("--holder-after", default="")
    relay.add_argument("--body-was-read-by-controller", action="store_true")
    relay.add_argument("--body-was-executed-by-controller", action="store_true")
    relay.add_argument("--private-role-to-role-delivery-detected", action="store_true")

    read_packet = subparsers.add_parser("read-packet", help="Target role verifies relay and opens packet body")
    read_packet.add_argument("--envelope-path", required=True)
    read_packet.add_argument("--role", required=True)

    open_packet_session = subparsers.add_parser(
        "open-packet-session",
        help="Target role opens a packet through the runtime session entrypoint",
    )
    open_packet_session.add_argument("--envelope-path", required=True)
    open_packet_session.add_argument("--role", required=True)
    open_packet_session.add_argument("--agent-id", required=True)

    complete_packet_session = subparsers.add_parser(
        "complete-packet-session",
        help="Complete a previously opened role packet session and generate the result envelope",
    )
    complete_packet_session.add_argument("--session-path", required=True)
    complete_packet_session.add_argument("--result-body-text", default="")
    complete_packet_session.add_argument("--result-body-file", default="")
    complete_packet_session.add_argument("--next-recipient", required=True)

    run_packet_session = subparsers.add_parser(
        "run-packet-session",
        help="Open a packet session and complete it in one runtime call",
    )
    run_packet_session.add_argument("--envelope-path", required=True)
    run_packet_session.add_argument("--role", required=True)
    run_packet_session.add_argument("--agent-id", required=True)
    run_packet_session.add_argument("--result-body-text", default="")
    run_packet_session.add_argument("--result-body-file", default="")
    run_packet_session.add_argument("--next-recipient", required=True)

    progress = subparsers.add_parser("progress", help="Target role updates Controller-visible packet progress")
    progress.add_argument("--envelope-path", required=True)
    progress.add_argument("--role", required=True)
    progress.add_argument("--agent-id", required=True)
    progress.add_argument("--progress", required=True, type=int)
    progress.add_argument("--message", required=True)

    issue_active = subparsers.add_parser(
        "issue-active-holder-lease",
        help="Router issues a scoped fast-lane lease to the current packet holder",
    )
    issue_active.add_argument("--envelope-path", required=True)
    issue_active.add_argument("--holder-role", required=True)
    issue_active.add_argument("--holder-agent-id", required=True)
    issue_active.add_argument("--route-version", required=True, type=int)
    issue_active.add_argument("--frontier-version", required=True, type=int)
    issue_active.add_argument("--allowed-action", action="append", default=[])

    active_ack = subparsers.add_parser("active-holder-ack", help="Current holder acknowledges a fast-lane packet lease")
    active_ack.add_argument("--lease-path", required=True)
    active_ack.add_argument("--role", required=True)
    active_ack.add_argument("--agent-id", required=True)
    active_ack.add_argument("--route-version", type=int, default=None)
    active_ack.add_argument("--frontier-version", type=int, default=None)

    active_progress = subparsers.add_parser(
        "active-holder-progress",
        help="Current holder writes controller-safe fast-lane packet progress",
    )
    active_progress.add_argument("--lease-path", required=True)
    active_progress.add_argument("--role", required=True)
    active_progress.add_argument("--agent-id", required=True)
    active_progress.add_argument("--progress", required=True, type=int)
    active_progress.add_argument("--message", required=True)
    active_progress.add_argument("--route-version", type=int, default=None)
    active_progress.add_argument("--frontier-version", type=int, default=None)

    active_submit = subparsers.add_parser(
        "active-holder-submit-result",
        help="Current holder submits a result through the fast lane and writes a Controller next-action notice",
    )
    active_submit.add_argument("--lease-path", required=True)
    active_submit.add_argument("--role", required=True)
    active_submit.add_argument("--agent-id", required=True)
    active_submit.add_argument("--result-body-text", default="")
    active_submit.add_argument("--result-body-file", default="")
    active_submit.add_argument("--next-recipient", required=True)
    active_submit.add_argument("--route-version", type=int, default=None)
    active_submit.add_argument("--frontier-version", type=int, default=None)

    active_submit_existing = subparsers.add_parser(
        "active-holder-submit-existing-result",
        help="Current holder submits an existing result envelope through the fast lane",
    )
    active_submit_existing.add_argument("--lease-path", required=True)
    active_submit_existing.add_argument("--role", required=True)
    active_submit_existing.add_argument("--agent-id", required=True)
    active_submit_existing.add_argument("--result-envelope-path", required=True)
    active_submit_existing.add_argument("--route-version", type=int, default=None)
    active_submit_existing.add_argument("--frontier-version", type=int, default=None)

    complete = subparsers.add_parser("complete", help="Write result_envelope.json and result_body.md")
    complete.add_argument("--envelope-path", required=True)
    complete.add_argument("--completed-by-role", required=True)
    complete.add_argument("--completed-by-agent-id", required=True)
    complete.add_argument("--result-body-text", default="")
    complete.add_argument("--result-body-file", default="")
    complete.add_argument("--next-recipient", required=True)
    complete.add_argument("--allow-wrong-role-for-audit", action="store_true")

    review = subparsers.add_parser("review", help="Validate packet/result envelope, hashes, and role origin")
    review.add_argument("--envelope-path", required=True)
    review.add_argument("--result-envelope-path", required=True)
    review.add_argument("--agent-role-map-json", default="")

    read_result = subparsers.add_parser("read-result", help="Reviewer/PM verifies relay and opens result body")
    read_result.add_argument("--result-envelope-path", required=True)
    read_result.add_argument("--role", required=True)

    open_result_session = subparsers.add_parser(
        "open-result-session",
        help="Reviewer/PM opens a result body through the runtime session entrypoint",
    )
    open_result_session.add_argument("--result-envelope-path", required=True)
    open_result_session.add_argument("--role", required=True)
    open_result_session.add_argument("--agent-id", required=True)

    audit_chain = subparsers.add_parser("audit-chain", help="Reviewer audits packet mail chain for a run or node")
    audit_chain.add_argument("--run-id", default="")
    audit_chain.add_argument("--node-id", default="")

    return parser.parse_args(argv)
