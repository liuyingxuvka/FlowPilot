"""Formal entrypoint for the new black-box FlowPilot runtime.

This module is the current public FlowPilot entrypoint. Implementation
ownership lives in focused child modules; this file keeps only the supported
current command/import surface.
"""

from __future__ import annotations

from flowpilot_new_cli import main
from flowpilot_new_role_commands import (
    ack,
    dispatch_current_role,
    open_packet,
    open_result,
    role_handoff_payload,
)
from flowpilot_new_run_commands import (
    cancel_run,
    final_preflight,
    host_liveness,
    patrol,
    progress,
    repair_accepted_packet,
    resolve_stopped_blocker,
    resume,
    run_fake_e2e,
    run_until_wait,
    status,
    stop_run,
    submit_result,
)
from flowpilot_new_shared import (
    DEFAULT_ACCEPTANCE_CONTRACT,
    DEFAULT_GOAL,
    HOST_KIND_HELP,
    STARTUP_UI,
    _assert_formal_interactive_result,
    startup_ui_command,
    start_run,
)


__all__ = [
    "DEFAULT_ACCEPTANCE_CONTRACT",
    "DEFAULT_GOAL",
    "HOST_KIND_HELP",
    "STARTUP_UI",
    "_assert_formal_interactive_result",
    "ack",
    "cancel_run",
    "dispatch_current_role",
    "final_preflight",
    "host_liveness",
    "main",
    "open_packet",
    "open_result",
    "patrol",
    "progress",
    "repair_accepted_packet",
    "resolve_stopped_blocker",
    "resume",
    "role_handoff_payload",
    "run_fake_e2e",
    "run_until_wait",
    "startup_ui_command",
    "start_run",
    "status",
    "stop_run",
    "submit_result",
]


if __name__ == "__main__":
    raise SystemExit(main())
