"""Public facade for FlowPilot packet runtime CLI helpers."""

from __future__ import annotations

from packet_runtime_cli_args import parse_args
from packet_runtime_cli_main import _read_text_arg, main

__all__ = ["parse_args", "_read_text_arg", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
