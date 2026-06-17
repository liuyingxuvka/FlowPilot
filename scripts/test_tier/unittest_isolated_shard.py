"""Run a strict OR-filtered unittest shard with each test in a subprocess."""

from __future__ import annotations

import argparse
import fnmatch
import subprocess
import sys
import unittest
from collections.abc import Iterable
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def iter_test_cases(suite: unittest.TestSuite) -> Iterable[unittest.TestCase]:
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from iter_test_cases(item)
        else:
            yield item


def pattern_matches(test_id: str, pattern: str) -> bool:
    if "*" in pattern:
        return fnmatch.fnmatchcase(test_id, pattern)
    return pattern in test_id


def load_tests(modules: list[str]) -> list[unittest.TestCase]:
    loaded: list[unittest.TestCase] = []
    for module in modules:
        suite = unittest.defaultTestLoader.loadTestsFromName(module)
        loaded.extend(iter_test_cases(suite))
    return loaded


def selected_test_ids(
    tests: list[unittest.TestCase],
    patterns: list[str],
) -> tuple[list[str], list[str]]:
    ids = [test.id() for test in tests]
    missing = [
        pattern
        for pattern in patterns
        if not any(pattern_matches(test_id, pattern) for test_id in ids)
    ]
    selected = [
        test_id
        for test_id in ids
        if any(pattern_matches(test_id, pattern) for pattern in patterns)
    ]
    return selected, missing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-k", dest="patterns", action="append", default=[])
    parser.add_argument("modules", nargs="+")
    args = parser.parse_args(argv)

    if not args.patterns:
        raise SystemExit("isolated unittest shard requires at least one -k pattern")

    tests = load_tests(args.modules)
    failed_loads = [test.id() for test in tests if test.id().startswith("unittest.loader._FailedTest.")]
    if failed_loads:
        suite = unittest.TestSuite(tests)
        result = unittest.TextTestRunner(verbosity=2 if args.verbose else 1).run(suite)
        return 0 if result.wasSuccessful() else 1

    chosen, missing = selected_test_ids(tests, args.patterns)
    if missing:
        for pattern in missing:
            print(f"stale isolated unittest shard pattern did not match any test: {pattern}", file=sys.stderr)
        return 1
    if not chosen:
        print("isolated unittest shard selected no tests", file=sys.stderr)
        return 1

    failed: list[str] = []
    for test_id in chosen:
        print(f"[isolated-unittest] running {test_id}", flush=True)
        command = [sys.executable, "-m", "unittest", "-v" if args.verbose else "-q", test_id]
        completed = subprocess.run(command, cwd=ROOT)
        if completed.returncode != 0:
            failed.append(test_id)

    if failed:
        print("[isolated-unittest] failed tests:", file=sys.stderr)
        for test_id in failed:
            print(f"  {test_id}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
