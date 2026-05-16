"""Read-only retention report for local `.flowpilot` runtime state."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _tree_size(path: Path) -> tuple[int, int]:
    if not path.exists():
        return 0, 0
    total = 0
    count = 0
    for child in path.rglob("*"):
        if child.is_file():
            count += 1
            try:
                total += child.stat().st_size
            except OSError:
                pass
    return total, count


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _run_timestamp(run_id: str, entry: dict[str, Any] | None, run_dir: Path) -> datetime | None:
    for key in ("updated_at", "completed_at", "created_at"):
        if entry:
            parsed = _parse_timestamp(entry.get(key))
            if parsed is not None:
                return parsed
    if run_dir.exists():
        try:
            return datetime.fromtimestamp(run_dir.stat().st_mtime, tz=timezone.utc)
        except OSError:
            return None
    for pattern in ("%Y%m%d-%H%M%S", "%Y%m%d"):
        token = run_id.removeprefix("run-").split("-", 2)
        raw = "-".join(token[:2]) if pattern.endswith("%S") and len(token) >= 2 else token[0]
        try:
            return datetime.strptime(raw, pattern).replace(tzinfo=timezone.utc)
        except (ValueError, IndexError):
            continue
    return None


def _index_entries(index: dict[str, Any]) -> dict[str, dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}
    for item in index.get("runs", []):
        if isinstance(item, dict) and item.get("run_id"):
            entries[str(item["run_id"])] = item
    return entries


def build_report(project_root: Path = ROOT, *, max_runs: int = 30) -> dict[str, Any]:
    root = project_root.resolve()
    flowpilot_root = root / ".flowpilot"
    current_path = flowpilot_root / "current.json"
    index_path = flowpilot_root / "index.json"
    runs_root = flowpilot_root / "runs"

    current = _read_json(current_path)
    index = _read_json(index_path)
    indexed = _index_entries(index)
    current_run_id = (
        current.get("current_run_id")
        or current.get("active_run_id")
        or current.get("run_id")
        or index.get("current_run_id")
    )

    run_dirs = {path.name: path for path in runs_root.iterdir() if path.is_dir()} if runs_root.exists() else {}
    indexed_ids = set(indexed)
    run_dir_ids = set(run_dirs)
    missing_run_dirs = sorted(indexed_ids - run_dir_ids)
    unindexed_run_dirs = sorted(run_dir_ids - indexed_ids)

    records: list[dict[str, Any]] = []
    for run_id in sorted(run_dir_ids | indexed_ids):
        run_dir = run_dirs.get(run_id, runs_root / run_id)
        size_bytes, file_count = _tree_size(run_dir)
        timestamp = _run_timestamp(run_id, indexed.get(run_id), run_dir)
        records.append(
            {
                "run_id": run_id,
                "path": _repo_relative(run_dir),
                "indexed": run_id in indexed_ids,
                "directory_exists": run_id in run_dir_ids,
                "is_current": run_id == current_run_id,
                "status": indexed.get(run_id, {}).get("status"),
                "timestamp": timestamp.isoformat() if timestamp else None,
                "bytes": size_bytes,
                "file_count": file_count,
            }
        )

    sortable = [
        record
        for record in records
        if record["directory_exists"] and not record["is_current"]
    ]
    sortable.sort(key=lambda record: record["timestamp"] or "")
    excess_count = max(0, len(run_dir_ids) - max_runs)
    stale_candidates = sortable[:excess_count]

    flowpilot_bytes, flowpilot_file_count = _tree_size(flowpilot_root)
    return {
        "ok": True,
        "read_only": True,
        "project_root": _repo_relative(root),
        "flowpilot_root": _repo_relative(flowpilot_root),
        "exists": flowpilot_root.exists(),
        "current_run_id": current_run_id,
        "current_path_exists": current_path.exists(),
        "index_path_exists": index_path.exists(),
        "indexed_run_count": len(indexed_ids),
        "run_directory_count": len(run_dir_ids),
        "total_bytes": flowpilot_bytes,
        "total_files": flowpilot_file_count,
        "missing_run_dirs": missing_run_dirs,
        "unindexed_run_dirs": unindexed_run_dirs,
        "max_runs": max_runs,
        "excess_run_directory_count": excess_count,
        "stale_candidates": stale_candidates,
        "recommendation": (
            "This report is intentionally read-only. Review stale_candidates and current_run_id "
            "before any future cleanup command is added or run."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--dry-run", action="store_true", help="Accepted for clarity; this tool is always read-only.")
    parser.add_argument("--project-root", default=str(ROOT), help="Project root containing `.flowpilot`.")
    parser.add_argument("--max-runs", type=int, default=30, help="Run directory count to keep before reporting excess.")
    args = parser.parse_args(argv)

    report = build_report(Path(args.project_root), max_runs=args.max_runs)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("FlowPilot runtime retention report: read-only")
        print(f"Runtime root: {report['flowpilot_root']}")
        print(f"Current run: {report['current_run_id'] or '<none>'}")
        print(f"Run directories: {report['run_directory_count']} / indexed: {report['indexed_run_count']}")
        print(f"Size: {report['total_bytes']} bytes in {report['total_files']} files")
        print(f"Missing indexed run dirs: {len(report['missing_run_dirs'])}")
        print(f"Unindexed run dirs: {len(report['unindexed_run_dirs'])}")
        print(f"Stale candidates by max-runs={report['max_runs']}: {len(report['stale_candidates'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
