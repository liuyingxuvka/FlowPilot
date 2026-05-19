"""Shared process-liveness probe for FlowPilot runtime owners."""

from __future__ import annotations

import os
import sys
from typing import Any


def process_is_live(pid: Any) -> bool:
    """Return whether a pid-like value appears to name a live local process."""

    try:
        value = int(pid)
    except (TypeError, ValueError):
        return False
    if value <= 0:
        return False
    if value == os.getpid():
        return True
    if sys.platform == "win32":
        try:
            import ctypes

            query_limited_information = 0x1000
            still_active = 259
            handle = ctypes.windll.kernel32.OpenProcess(query_limited_information, False, value)
            if not handle:
                return False
            try:
                exit_code = ctypes.c_ulong()
                ok = ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
                return bool(ok) and exit_code.value == still_active
            finally:
                ctypes.windll.kernel32.CloseHandle(handle)
        except Exception:
            return False
    try:
        os.kill(value, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True
