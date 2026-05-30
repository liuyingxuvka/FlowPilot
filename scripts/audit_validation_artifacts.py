"""Read-only audit for duplicated validation result artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCAN_ROOT = ROOT / "simulations"


def _repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_paths(scan_root: Path) -> list[Path]:
    if not scan_root.exists():
        return []
    return sorted(
        path
        for path in scan_root.rglob("*.json")
        if path.is_file() and not path.name.endswith(".proof.json")
    )


def _canonical_candidate(paths: list[Path]) -> Path:
    def score(path: Path) -> tuple[int, int, str]:
        relpath = _repo_relative(path)
        generated_name_score = 1 if "_checks_results" in path.name else 0
        return generated_name_score, len(relpath), relpath

    return sorted(paths, key=score)[0]


RETIRED_SEMANTIC_MARKERS = (
    "unsupported_historical alias",
    "unsupported_historical aliases",
    "unsupported_historical metadata",
    "accepted as unsupported_historical",
    "retaining modelability names as unsupported_historical aliases",
    "retaining route process check names as unsupported_historical aliases",
)


def _has_unsupported_semantics(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="replace").lower()
    except OSError:
        return False
    return any(marker in text for marker in RETIRED_SEMANTIC_MARKERS)


def _exact_duplicate_groups(paths: list[Path]) -> list[dict[str, Any]]:
    by_hash: dict[tuple[str, int], list[Path]] = defaultdict(list)
    for path in paths:
        stat = path.stat()
        by_hash[(_sha256(path), stat.st_size)].append(path)

    groups: list[dict[str, Any]] = []
    for (digest, size), group_paths in sorted(by_hash.items(), key=lambda item: item[0]):
        if len(group_paths) < 2:
            continue
        canonical = _canonical_candidate(group_paths)
        groups.append(
            {
                "sha256": digest,
                "bytes": size,
                "count": len(group_paths),
                "canonical_candidate": _repo_relative(canonical),
                "files": [_repo_relative(path) for path in sorted(group_paths)],
            }
        )
    return groups


def _runner_duplicate_pairs(paths: list[Path]) -> list[dict[str, Any]]:
    path_set = {path.resolve(): path for path in paths}
    pairs: list[dict[str, Any]] = []
    for checks_path in sorted(path for path in paths if path.name.endswith("_checks_results.json")):
        result_name = checks_path.name.replace("_checks_results.json", "_results.json")
        result_path = checks_path.with_name(result_name)
        if result_path.resolve() not in path_set:
            continue
        if checks_path.stat().st_size != result_path.stat().st_size:
            continue
        checks_hash = _sha256(checks_path)
        result_hash = _sha256(result_path)
        if checks_hash != result_hash:
            continue
        pairs.append(
            {
                "checks_results": _repo_relative(checks_path),
                "results": _repo_relative(result_path),
                "bytes": checks_path.stat().st_size,
                "sha256": checks_hash,
                "canonical_candidate": _repo_relative(result_path),
            }
        )
    return pairs


def _shadow_result_pairs(paths: list[Path]) -> list[dict[str, Any]]:
    path_set = {path.resolve(): path for path in paths}
    pairs: list[dict[str, Any]] = []
    for checks_path in sorted(path for path in paths if path.name.endswith("_checks_results.json")):
        result_path = checks_path.with_name(checks_path.name.replace("_checks_results.json", "_results.json"))
        if result_path.resolve() not in path_set:
            continue
        checks_size = checks_path.stat().st_size
        result_size = result_path.stat().st_size
        checks_hash = _sha256(checks_path)
        result_hash = _sha256(result_path)
        exact_duplicate = checks_size == result_size and checks_hash == result_hash
        checks_unsupported = _has_unsupported_semantics(checks_path)
        result_unsupported = _has_unsupported_semantics(result_path)
        pairs.append(
            {
                "checks_results": _repo_relative(checks_path),
                "results": _repo_relative(result_path),
                "canonical_candidate": _repo_relative(result_path),
                "exact_duplicate": exact_duplicate,
                "semantic_drift": not exact_duplicate,
                "checks_unsupported_semantics": checks_unsupported,
                "results_unsupported_semantics": result_unsupported,
                "stale_shadow_semantics": checks_unsupported and not result_unsupported,
                "checks_sha256": checks_hash,
                "results_sha256": result_hash,
                "checks_bytes": checks_size,
                "results_bytes": result_size,
            }
        )
    return pairs


def build_report(scan_root: Path = DEFAULT_SCAN_ROOT) -> dict[str, Any]:
    paths = _artifact_paths(scan_root)
    total_bytes = sum(path.stat().st_size for path in paths)
    duplicate_groups = _exact_duplicate_groups(paths)
    runner_pairs = _runner_duplicate_pairs(paths)
    shadow_pairs = _shadow_result_pairs(paths)
    duplicate_bytes = sum((group["count"] - 1) * group["bytes"] for group in duplicate_groups)
    stale_shadow_pairs = [pair for pair in shadow_pairs if pair["stale_shadow_semantics"]]

    return {
        "ok": True,
        "read_only": True,
        "scan_root": _repo_relative(scan_root),
        "artifact_count": len(paths),
        "total_bytes": total_bytes,
        "duplicate_group_count": len(duplicate_groups),
        "duplicate_bytes": duplicate_bytes,
        "runner_duplicate_pair_count": len(runner_pairs),
        "shadow_pair_count": len(shadow_pairs),
        "semantic_drift_pair_count": sum(1 for pair in shadow_pairs if pair["semantic_drift"]),
        "stale_shadow_semantics_pair_count": len(stale_shadow_pairs),
        "duplicate_groups": duplicate_groups,
        "runner_duplicate_pairs": runner_pairs,
        "shadow_result_pairs": shadow_pairs,
        "stale_shadow_semantics_pairs": stale_shadow_pairs,
        "recommendation": (
            "Use canonical_candidate paths before cleanup; exact duplicates can be removed after references "
            "are canonicalized, and stale_shadow_semantics_pairs need review. This audit does not delete "
            "or rewrite validation artifacts."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument(
        "--scan-root",
        default=str(DEFAULT_SCAN_ROOT),
        help="Directory to scan for validation JSON artifacts.",
    )
    args = parser.parse_args(argv)

    report = build_report(Path(args.scan_root))
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("Validation artifact audit: read-only")
        print(f"Scanned: {report['scan_root']}")
        print(f"Artifacts: {report['artifact_count']} ({report['total_bytes']} bytes)")
        print(
            "Exact duplicate groups: "
            f"{report['duplicate_group_count']} ({report['duplicate_bytes']} duplicate bytes)"
        )
        print(f"Runner duplicate pairs: {report['runner_duplicate_pair_count']}")
        print(f"Shadow result pairs: {report['shadow_pair_count']}")
        print(f"Semantic-drift shadow pairs: {report['semantic_drift_pair_count']}")
        print(f"Stale-shadow semantic pairs: {report['stale_shadow_semantics_pair_count']}")
        for pair in report["runner_duplicate_pairs"][:10]:
            print(f"- {pair['checks_results']} == {pair['results']}")
        if len(report["runner_duplicate_pairs"]) > 10:
            print(f"- ... {len(report['runner_duplicate_pairs']) - 10} more pairs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
