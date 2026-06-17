"""Portable installed-skill self-check for FlowPilot runtime assets."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib
import importlib.metadata
import json
from pathlib import Path
import sys
from typing import Any


REQUIRED_RUNTIME_ASSETS = (
    "flowpilot_new.py",
    "flowpilot_new_shared.py",
    "flowpilot_core_runtime/runtime.py",
    "flowpilot_core_runtime/packet_result_contracts.py",
    "flowpilot_core_runtime/packet_stage_evidence_matrix.py",
    "runtime_kit/manifest.json",
    "runtime_kit/contracts/contract_index.json",
    "runtime_kit/cards/roles/flowguard_operator.md",
    "runtime_kit/cards/roles/human_like_reviewer.md",
    "runtime_kit/cards/phases/pm_flowguard_operator_request_report_loop.md",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def runtime_self_check(*, assets_root: Path | None = None) -> dict[str, Any]:
    root = Path(assets_root or Path(__file__).resolve().parent).resolve()
    missing = [relative for relative in REQUIRED_RUNTIME_ASSETS if not (root / relative).is_file()]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    flowguard_ok = False
    flowguard_schema = ""
    flowguard_version = ""
    flowguard_error = ""
    try:
        flowguard = importlib.import_module("flowguard")
        flowguard_schema = str(getattr(flowguard, "SCHEMA_VERSION", ""))
        flowguard_version = importlib.metadata.version("flowguard")
        flowguard_ok = bool(flowguard_schema)
    except Exception as exc:  # pragma: no cover - environment-dependent failure path.
        flowguard_error = f"{type(exc).__name__}: {exc}"
    ok = not missing and flowguard_ok
    return {
        "schema_version": "flowpilot.runtime_self_check_receipt.v1",
        "ok": ok,
        "assets_root": str(root),
        "required_runtime_assets": list(REQUIRED_RUNTIME_ASSETS),
        "missing_runtime_assets": missing,
        "flowguard_import_ok": flowguard_ok,
        "flowguard_schema_version": flowguard_schema,
        "flowguard_package_version": flowguard_version,
        "flowguard_error": flowguard_error,
        "dev_repo_simulations_required": False,
        "checked_at": _now_iso(),
    }


def write_runtime_self_check_receipt(run_root: Path, *, assets_root: Path | None = None) -> dict[str, Any]:
    receipt = runtime_self_check(assets_root=assets_root)
    target = Path(run_root).resolve() / "runtime" / "flowpilot_runtime_self_check_receipt.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    receipt["receipt_path"] = str(target)
    target.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets-root", default="", help="FlowPilot installed assets root. Defaults to this script parent.")
    parser.add_argument("--run-root", default="", help="Optional current run root for writing the receipt.")
    parser.add_argument("--json", action="store_true", help="Print JSON receipt.")
    args = parser.parse_args(argv)
    assets_root = Path(args.assets_root).resolve() if args.assets_root else None
    if args.run_root:
        receipt = write_runtime_self_check_receipt(Path(args.run_root), assets_root=assets_root)
    else:
        receipt = runtime_self_check(assets_root=assets_root)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

