"""Argument parsing for the unified FlowPilot runtime CLI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ASSETS = Path(__file__).resolve().parent
if str(ASSETS) not in sys.path:
    sys.path.insert(0, str(ASSETS))

import role_output_runtime  # noqa: E402

def _add_card_identity_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--envelope-path", required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--agent-id", required=True)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Open FlowPilot packets/cards and submit runtime-backed role outputs.")
    parser.add_argument("--root", default=".", help="Project root containing .flowpilot")
    sub = parser.add_subparsers(dest="command", required=True)

    open_packet = sub.add_parser("open-packet", help="Open a packet through the packet runtime session.")
    _add_card_identity_args(open_packet)

    open_card = sub.add_parser("open-card", help="Open a system-card envelope and write a read receipt.")
    _add_card_identity_args(open_card)

    ack_card = sub.add_parser("ack-card", help="Submit a direct Router card ACK referencing read receipts.")
    _add_card_identity_args(ack_card)
    ack_card.add_argument("--receipt-path", action="append", default=[])
    ack_card.add_argument("--status", choices=("acknowledged", "blocked"), default="acknowledged")

    receive_card = sub.add_parser("receive-card", help="Open a system card and write its runtime-backed ACK in one call.")
    _add_card_identity_args(receive_card)
    receive_card.add_argument("--status", choices=("acknowledged", "blocked"), default="acknowledged")

    open_bundle = sub.add_parser("open-card-bundle", help="Open a same-role system-card bundle and write read receipts.")
    _add_card_identity_args(open_bundle)

    ack_bundle = sub.add_parser("ack-card-bundle", help="Submit one direct Router ACK for a same-role card bundle.")
    _add_card_identity_args(ack_bundle)
    ack_bundle.add_argument("--receipt-path", action="append", default=[])
    ack_bundle.add_argument("--status", choices=("acknowledged", "blocked"), default="acknowledged")

    receive_bundle = sub.add_parser("receive-card-bundle", help="Open a system-card bundle and write its runtime-backed ACK.")
    _add_card_identity_args(receive_bundle)
    receive_bundle.add_argument("--status", choices=("acknowledged", "blocked"), default="acknowledged")

    complete_packet = sub.add_parser("complete-packet", help="Complete a packet session and generate a result envelope.")
    complete_packet.add_argument("--session-path", required=True)
    complete_packet.add_argument("--result-body-text", default="")
    complete_packet.add_argument("--result-body-file", default="")
    complete_packet.add_argument("--next-recipient", required=True)
    complete_packet.add_argument("--controller-aside", default="")

    run_packet = sub.add_parser("run-packet", help="Open and complete a packet in one runtime call.")
    _add_card_identity_args(run_packet)
    run_packet.add_argument("--result-body-text", default="")
    run_packet.add_argument("--result-body-file", default="")
    run_packet.add_argument("--next-recipient", required=True)
    run_packet.add_argument("--controller-aside", default="")

    issue_active = sub.add_parser("issue-active-holder-lease", help="Issue a scoped fast-lane lease to the current packet holder.")
    issue_active.add_argument("--envelope-path", required=True)
    issue_active.add_argument("--holder-role", required=True)
    issue_active.add_argument("--holder-agent-id", required=True)
    issue_active.add_argument("--route-version", required=True, type=int)
    issue_active.add_argument("--frontier-version", required=True, type=int)
    issue_active.add_argument("--allowed-action", action="append", default=[])

    active_ack = sub.add_parser("active-holder-ack", help="Acknowledge a fast-lane packet lease.")
    active_ack.add_argument("--lease-path", required=True)
    active_ack.add_argument("--role", required=True)
    active_ack.add_argument("--agent-id", required=True)
    active_ack.add_argument("--route-version", type=int, default=None)
    active_ack.add_argument("--frontier-version", type=int, default=None)

    active_progress = sub.add_parser("active-holder-progress", help="Write controller-safe fast-lane packet progress.")
    active_progress.add_argument("--lease-path", required=True)
    active_progress.add_argument("--role", required=True)
    active_progress.add_argument("--agent-id", required=True)
    active_progress.add_argument("--progress", required=True, type=int)
    active_progress.add_argument("--message", required=True)
    active_progress.add_argument("--controller-aside", default="")
    active_progress.add_argument("--route-version", type=int, default=None)
    active_progress.add_argument("--frontier-version", type=int, default=None)

    active_submit = sub.add_parser("active-holder-submit-result", help="Submit a packet result through the fast lane.")
    active_submit.add_argument("--lease-path", required=True)
    active_submit.add_argument("--role", required=True)
    active_submit.add_argument("--agent-id", required=True)
    active_submit.add_argument("--result-body-text", default="")
    active_submit.add_argument("--result-body-file", default="")
    active_submit.add_argument("--next-recipient", required=True)
    active_submit.add_argument("--controller-aside", default="")
    active_submit.add_argument("--route-version", type=int, default=None)
    active_submit.add_argument("--frontier-version", type=int, default=None)

    active_submit_existing = sub.add_parser(
        "active-holder-submit-existing-result",
        help="Submit an existing packet result envelope through the fast lane.",
    )
    active_submit_existing.add_argument("--lease-path", required=True)
    active_submit_existing.add_argument("--role", required=True)
    active_submit_existing.add_argument("--agent-id", required=True)
    active_submit_existing.add_argument("--result-envelope-path", required=True)
    active_submit_existing.add_argument("--route-version", type=int, default=None)
    active_submit_existing.add_argument("--frontier-version", type=int, default=None)

    open_result = sub.add_parser("open-result", help="Open a result body through the review runtime session.")
    open_result.add_argument("--result-envelope-path", required=True)
    open_result.add_argument("--role", required=True)
    open_result.add_argument("--agent-id", required=True)

    prepare_output = sub.add_parser("prepare-output", help="Generate a role-output skeleton.")
    prepare_output.add_argument("--output-type", required=True, choices=sorted(role_output_runtime.SUPPORTED_OUTPUT_TYPES))
    prepare_output.add_argument("--role", required=True)
    prepare_output.add_argument("--agent-id", required=True)
    prepare_output.add_argument("--run-id", default="")
    prepare_output.add_argument("--body-path", default="")
    prepare_output.add_argument("--event-name", default="")
    prepare_output.add_argument("--controller-status-packet-path", default="")

    submit_output = sub.add_parser("submit-output", help="Submit a role-output body and return a compact envelope.")
    submit_output.add_argument("--output-type", required=True, choices=sorted(role_output_runtime.SUPPORTED_OUTPUT_TYPES))
    submit_output.add_argument("--role", required=True)
    submit_output.add_argument("--agent-id", required=True)
    submit_output.add_argument("--body-json", default="")
    submit_output.add_argument("--body-file", default="")
    submit_output.add_argument("--output-path", default="")
    submit_output.add_argument("--run-id", default="")
    submit_output.add_argument("--event-name", default="")
    submit_output.add_argument("--session-path", default="")
    submit_output.add_argument("--controller-status-packet-path", default="")
    submit_output.add_argument("--controller-aside", default="")

    submit_output_router = sub.add_parser(
        "submit-output-to-router",
        help="Submit a role-output body and record its event directly with Router.",
    )
    submit_output_router.add_argument("--output-type", required=True, choices=sorted(role_output_runtime.SUPPORTED_OUTPUT_TYPES))
    submit_output_router.add_argument("--role", required=True)
    submit_output_router.add_argument("--agent-id", required=True)
    submit_output_router.add_argument("--body-json", default="")
    submit_output_router.add_argument("--body-file", default="")
    submit_output_router.add_argument("--output-path", default="")
    submit_output_router.add_argument("--run-id", default="")
    submit_output_router.add_argument("--event-name", default="")
    submit_output_router.add_argument("--session-path", default="")
    submit_output_router.add_argument("--controller-status-packet-path", default="")
    submit_output_router.add_argument("--controller-aside", default="")

    progress_output = sub.add_parser("progress-output", help="Update Controller-visible formal role-output progress.")
    progress_output.add_argument("--output-type", required=True, choices=sorted(role_output_runtime.SUPPORTED_OUTPUT_TYPES))
    progress_output.add_argument("--role", required=True)
    progress_output.add_argument("--agent-id", required=True)
    progress_output.add_argument("--progress", required=True, type=int)
    progress_output.add_argument("--message", required=True)
    progress_output.add_argument("--run-id", default="")
    progress_output.add_argument("--event-name", default="")
    progress_output.add_argument("--session-path", default="")
    progress_output.add_argument("--controller-status-packet-path", default="")
    progress_output.add_argument("--controller-aside", default="")

    controller_boundary = sub.add_parser(
        "submit-controller-boundary-confirmation",
        help="Write Controller boundary confirmation through the formal output runtime.",
    )
    controller_boundary.add_argument("--agent-id", required=True)
    controller_boundary.add_argument("--run-id", default="")
    controller_boundary.add_argument("--action-id", default="")
    controller_boundary.add_argument("--source-action-id", default="")
    controller_boundary.add_argument("--output-path", default="")
    controller_boundary.add_argument("--controller-status-packet-path", default="")

    verify_output = sub.add_parser("verify-output-envelope", help="Verify a role-output runtime receipt.")
    verify_output.add_argument("--envelope-file", required=True)

    return parser.parse_args(argv)

__all__ = (
    "_add_card_identity_args",
    "parse_args",
)
