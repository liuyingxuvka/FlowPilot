"""Refresh current FlowPilot model-regression file bindings."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from flowguard.model_purpose import build_model_purpose_closure, file_fingerprint


def refresh(root: Path) -> dict:
    path = root / ".flowguard" / "model-regression-manifest.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    for entry in payload.get("models", []):
        purpose = entry.get("purpose_closure")
        if not isinstance(purpose, dict):
            raise ValueError(f"{entry.get('model_id', '<unknown>')}: missing purpose_closure")
        model_path = root / str(entry["model_path"])
        runner = tuple(str(item) for item in entry.get("runner", ()))
        if len(runner) < 2 or runner[0] != "{python}":
            raise ValueError(f"{entry.get('model_id', '<unknown>')}: unsupported runner")
        runner_path = root / runner[1]
        model_sha256 = file_fingerprint(model_path)
        runner_sha256 = file_fingerprint(runner_path)
        rebuilt = build_model_purpose_closure(
            model_instance_id=purpose["model_instance_id"],
            reusable_model_type_id=purpose["reusable_model_type_id"],
            task_intent_id=purpose["task_intent_id"],
            guarded_purpose=purpose["guarded_purpose"],
            protected_failure_ids=purpose["protected_failure_ids"],
            known_good_case_id=purpose["known_good_case_id"],
            failure_bindings=purpose["failure_bindings"],
            claim_boundary=purpose["claim_boundary"],
            evidence_check_ids=purpose["evidence_check_ids"],
            model_sha256=model_sha256,
            runner_sha256=runner_sha256,
        )
        entry["purpose_closure"] = rebuilt.to_dict()
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    payload = refresh(Path(args.root).resolve())
    print(json.dumps({"ok": True, "model_count": len(payload.get("models", []))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
