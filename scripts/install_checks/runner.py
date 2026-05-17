"""Runner for the FlowPilot install self-check groups."""

from __future__ import annotations

import json

from . import docs, files, manifests, results, runtime


CHECK_GROUPS = (
    files.run_checks,
    manifests.run_checks,
    runtime.run_checks,
    docs.run_checks,
    results.run_checks,
)


def build_result() -> dict[str, object]:
    result: dict[str, object] = {"ok": True, "checks": []}
    for run_group in CHECK_GROUPS:
        run_group(result)
    return result


def main() -> int:
    result = build_result()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1
