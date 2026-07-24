"""Strong local process identity and bounded process-tree cleanup helpers."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Mapping, Sequence


def resolve_current_python_process_launch(
    command: Sequence[str],
    *,
    environment: Mapping[str, str] | None = None,
) -> tuple[list[str], dict[str, str] | None, dict[str, str]]:
    """Bind a Windows venv request to the real current interpreter process."""

    requested = list(command)
    if not requested:
        raise ValueError("process command must not be empty")
    process_command = list(requested)
    process_environment = dict(environment) if environment is not None else None
    plan = {
        "kind": "direct_command",
        "requested_executable": requested[0],
        "process_owner_executable": requested[0],
    }
    if sys.platform != "win32":
        return process_command, process_environment, plan

    requested_key = os.path.normcase(os.path.abspath(requested[0]))
    current_key = os.path.normcase(os.path.abspath(sys.executable))
    base_executable = str(getattr(sys, "_base_executable", "") or "")
    if requested_key != current_key or not base_executable:
        return process_command, process_environment, plan
    base_key = os.path.normcase(os.path.abspath(base_executable))
    if base_key == current_key:
        return process_command, process_environment, plan

    process_command[0] = base_executable
    process_environment = dict(os.environ if environment is None else environment)
    process_environment["__PYVENV_LAUNCHER__"] = sys.executable
    return (
        process_command,
        process_environment,
        {
            "kind": "windows_venv_direct_base_owner",
            "requested_executable": sys.executable,
            "process_owner_executable": base_executable,
            "venv_launcher_binding": sys.executable,
        },
    )


def _coerce_pid(pid: Any) -> int | None:
    try:
        value = int(pid)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def process_is_live(pid: Any) -> bool:
    """Return whether a pid-like value appears to name a live local process."""

    value = _coerce_pid(pid)
    if value is None:
        return False
    if value == os.getpid():
        return True
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            query_limited_information = 0x1000
            still_active = 259
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            kernel32.OpenProcess.restype = wintypes.HANDLE
            kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
            kernel32.GetExitCodeProcess.restype = wintypes.BOOL
            kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel32.CloseHandle.restype = wintypes.BOOL
            handle = kernel32.OpenProcess(query_limited_information, False, value)
            if not handle:
                return False
            try:
                exit_code = wintypes.DWORD()
                ok = kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
                return bool(ok) and exit_code.value == still_active
            finally:
                kernel32.CloseHandle(handle)
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


def process_start_token(pid: Any) -> str | None:
    """Return a PID-reuse-resistant local process creation token."""

    value = _coerce_pid(pid)
    if value is None or not process_is_live(value):
        return None
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            class FILETIME(ctypes.Structure):
                _fields_ = [("low", wintypes.DWORD), ("high", wintypes.DWORD)]

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            kernel32.OpenProcess.restype = wintypes.HANDLE
            kernel32.GetProcessTimes.argtypes = [
                wintypes.HANDLE,
                ctypes.POINTER(FILETIME),
                ctypes.POINTER(FILETIME),
                ctypes.POINTER(FILETIME),
                ctypes.POINTER(FILETIME),
            ]
            kernel32.GetProcessTimes.restype = wintypes.BOOL
            kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel32.CloseHandle.restype = wintypes.BOOL
            handle = kernel32.OpenProcess(0x1000, False, value)
            if not handle:
                return None
            try:
                creation = FILETIME()
                exit_time = FILETIME()
                kernel = FILETIME()
                user = FILETIME()
                ok = kernel32.GetProcessTimes(
                    handle,
                    ctypes.byref(creation),
                    ctypes.byref(exit_time),
                    ctypes.byref(kernel),
                    ctypes.byref(user),
                )
                if not ok:
                    return None
                ticks = (int(creation.high) << 32) | int(creation.low)
                return f"win-filetime:{ticks}"
            finally:
                kernel32.CloseHandle(handle)
        except Exception:
            return None
    stat_path = Path("/proc") / str(value) / "stat"
    try:
        raw = stat_path.read_text(encoding="utf-8")
        fields = raw[raw.rfind(")") + 2 :].split()
        if len(fields) > 19:
            return f"proc-starttime:{fields[19]}"
    except (OSError, ValueError):
        pass
    try:
        started = subprocess.check_output(
            ["ps", "-o", "lstart=", "-p", str(value)],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return f"ps-lstart:{started}" if started else None


def process_identity(pid: Any) -> dict[str, Any] | None:
    value = _coerce_pid(pid)
    token = process_start_token(value)
    if value is None or token is None:
        return None
    return {"pid": value, "start_token": token}


def process_identity_is_live(identity: Any) -> bool:
    if not isinstance(identity, dict):
        return False
    pid = _coerce_pid(identity.get("pid"))
    expected_token = identity.get("start_token")
    if pid is None or not isinstance(expected_token, str) or not expected_token:
        return False
    return process_is_live(pid) and process_start_token(pid) == expected_token


def _ordered_start_token(identity: Any) -> tuple[str, int] | None:
    """Return an orderable exact start token for platforms that expose one."""

    if not isinstance(identity, dict):
        return None
    token = identity.get("start_token")
    if not isinstance(token, str):
        return None
    for prefix in ("win-filetime:", "proc-starttime:"):
        if token.startswith(prefix):
            try:
                return prefix, int(token.removeprefix(prefix))
            except ValueError:
                return None
    return None


def process_identity_started_not_before(
    identity: Any,
    ancestor_identity: Any,
) -> bool:
    """Reject impossible descendants whose process predates the exact owner."""

    child_token = _ordered_start_token(identity)
    ancestor_token = _ordered_start_token(ancestor_identity)
    if child_token is None or ancestor_token is None:
        return True
    if child_token[0] != ancestor_token[0]:
        return True
    return child_token[1] >= ancestor_token[1]


def _process_parent_map() -> dict[int, int]:
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            class PROCESSENTRY32W(ctypes.Structure):
                _fields_ = [
                    ("dwSize", wintypes.DWORD),
                    ("cntUsage", wintypes.DWORD),
                    ("th32ProcessID", wintypes.DWORD),
                    ("th32DefaultHeapID", ctypes.c_size_t),
                    ("th32ModuleID", wintypes.DWORD),
                    ("cntThreads", wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD),
                    ("pcPriClassBase", ctypes.c_long),
                    ("dwFlags", wintypes.DWORD),
                    ("szExeFile", wintypes.WCHAR * 260),
                ]

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
            kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
            kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
            kernel32.Process32FirstW.restype = wintypes.BOOL
            kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
            kernel32.Process32NextW.restype = wintypes.BOOL
            kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel32.CloseHandle.restype = wintypes.BOOL
            snapshot = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)
            invalid_handle = ctypes.c_void_p(-1).value
            if snapshot == invalid_handle:
                return {}
            result: dict[int, int] = {}
            try:
                entry = PROCESSENTRY32W()
                entry.dwSize = ctypes.sizeof(entry)
                ok = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
                while ok:
                    result[int(entry.th32ProcessID)] = int(entry.th32ParentProcessID)
                    ok = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
            finally:
                kernel32.CloseHandle(snapshot)
            return result
        except Exception:
            return {}
    result: dict[int, int] = {}
    proc_root = Path("/proc")
    if proc_root.exists():
        for stat_path in proc_root.glob("[0-9]*/stat"):
            try:
                pid = int(stat_path.parent.name)
                raw = stat_path.read_text(encoding="utf-8")
                fields = raw[raw.rfind(")") + 2 :].split()
                result[pid] = int(fields[1])
            except (OSError, ValueError, IndexError):
                continue
        return result
    try:
        output = subprocess.check_output(
            ["ps", "-eo", "pid=,ppid="],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError):
        return result
    for line in output.splitlines():
        parts = line.split()
        if len(parts) == 2:
            try:
                result[int(parts[0])] = int(parts[1])
            except ValueError:
                continue
    return result


def _descendant_pids(pid: int) -> list[int]:
    """Return the raw PID-only descendant projection for diagnostics.

    PID-only ancestry is never termination authority. On Windows an exited
    process ID can be reused while another owner is still running, so a raw
    parent map can contain an apparent cycle through an older supervisor and
    then reach a younger sibling process.
    """

    parent_map = _process_parent_map()
    descendants: list[int] = []
    visited = {pid}
    frontier = [pid]
    while frontier:
        parent = frontier.pop(0)
        children = sorted(
            child
            for child, candidate_parent in parent_map.items()
            if candidate_parent == parent
        )
        for child in children:
            if child in visited:
                continue
            visited.add(child)
            descendants.append(child)
            frontier.append(child)
    return descendants


def process_descendant_identities(identity: Any) -> list[dict[str, Any]]:
    if not process_identity_is_live(identity):
        return []
    root = dict(identity)
    root_pid = int(root["pid"])
    parent_map = _process_parent_map()
    descendants: list[dict[str, Any]] = []
    visited = {root_pid}
    frontier = [root]
    while frontier:
        parent_identity = frontier.pop(0)
        parent_pid = int(parent_identity["pid"])
        child_pids = sorted(
            child_pid
            for child_pid, candidate_parent in parent_map.items()
            if candidate_parent == parent_pid
        )
        for child_pid in child_pids:
            if child_pid in visited:
                continue
            child_identity = process_identity(child_pid)
            if child_identity is None:
                continue
            # Every edge must preserve creation order. Checking only the final
            # child against the root lets traversal cross an older, PID-reused
            # supervisor link and then misclassify a newer sibling as a child.
            if not process_identity_started_not_before(
                child_identity,
                parent_identity,
            ):
                continue
            if not process_identity_started_not_before(child_identity, root):
                continue
            visited.add(child_pid)
            descendants.append(child_identity)
            frontier.append(child_identity)
    return descendants


def _terminate_pid(pid: int, *, force: bool) -> None:
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            kernel32.OpenProcess.restype = wintypes.HANDLE
            kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
            kernel32.TerminateProcess.restype = wintypes.BOOL
            kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel32.CloseHandle.restype = wintypes.BOOL
            handle = kernel32.OpenProcess(0x0001, False, pid)
            if handle:
                try:
                    kernel32.TerminateProcess(handle, 1)
                finally:
                    kernel32.CloseHandle(handle)
        except Exception:
            return
        return
    try:
        os.kill(pid, signal.SIGKILL if force else signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        return


def terminate_process_tree(identity: Any, *, timeout_seconds: float = 5.0) -> dict[str, Any]:
    """Terminate one exact process identity and every descendant observed under it."""

    target = dict(identity) if isinstance(identity, dict) else {}
    pid = _coerce_pid(target.get("pid"))
    expected_token = target.get("start_token")
    base = {
        "target_identity": target,
        "observed_descendant_identities": [],
        "remaining_live_identities": [],
        "cleanup_confirmed": False,
        "descendant_zero_confirmed": False,
        "pid_reuse_detected": False,
        "signal_sent": False,
    }
    if pid is None or not isinstance(expected_token, str) or not expected_token:
        return {**base, "reason": "invalid_process_identity"}
    if pid == os.getpid():
        return {**base, "reason": "refused_to_terminate_current_process"}
    if not process_is_live(pid):
        return {
            **base,
            "cleanup_confirmed": True,
            "descendant_zero_confirmed": True,
            "reason": "target_identity_already_exited",
        }
    if process_start_token(pid) != expected_token:
        return {
            **base,
            "cleanup_confirmed": True,
            "descendant_zero_confirmed": True,
            "pid_reuse_detected": True,
            "reason": "pid_reused_target_identity_not_signaled",
        }

    descendants = process_descendant_identities(target)
    observed = [target, *descendants]
    base["observed_descendant_identities"] = descendants
    if sys.platform != "win32":
        try:
            if os.getpgid(pid) == pid:
                os.killpg(pid, signal.SIGTERM)
                base["signal_sent"] = True
            else:
                _terminate_pid(pid, force=False)
                for child in reversed(descendants):
                    _terminate_pid(int(child["pid"]), force=False)
                base["signal_sent"] = True
        except (ProcessLookupError, PermissionError, OSError):
            pass
    else:
        _terminate_pid(pid, force=False)
        for child in reversed(descendants):
            _terminate_pid(int(child["pid"]), force=False)
        base["signal_sent"] = True

    deadline = time.monotonic() + max(float(timeout_seconds), 0.0)
    while time.monotonic() < deadline:
        remaining = [item for item in observed if process_identity_is_live(item)]
        if not remaining:
            return {
                **base,
                "cleanup_confirmed": True,
                "descendant_zero_confirmed": True,
                "reason": "process_tree_exited",
            }
        time.sleep(0.05)

    remaining = [item for item in observed if process_identity_is_live(item)]
    for item in remaining:
        _terminate_pid(int(item["pid"]), force=True)
    force_deadline = time.monotonic() + min(max(float(timeout_seconds), 0.25), 2.0)
    while time.monotonic() < force_deadline:
        remaining = [item for item in observed if process_identity_is_live(item)]
        if not remaining:
            break
        time.sleep(0.05)
    remaining = [item for item in observed if process_identity_is_live(item)]
    return {
        **base,
        "remaining_live_identities": remaining,
        "cleanup_confirmed": not remaining,
        "descendant_zero_confirmed": not remaining,
        "reason": "process_tree_force_killed" if not remaining else "cleanup_unconfirmed",
    }
