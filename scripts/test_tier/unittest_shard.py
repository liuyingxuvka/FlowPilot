"""Run a strict OR-filtered unittest shard for FlowPilot test tiers."""

from __future__ import annotations

import argparse
import fnmatch
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


def selected_tests(
    tests: list[unittest.TestCase],
    patterns: list[str],
) -> tuple[list[unittest.TestCase], list[str]]:
    selected: list[unittest.TestCase] = []
    missing: list[str] = []
    ids = [test.id() for test in tests]
    for pattern in patterns:
        if not any(pattern_matches(test_id, pattern) for test_id in ids):
            missing.append(pattern)

    for test in tests:
        test_id = test.id()
        if any(pattern_matches(test_id, pattern) for pattern in patterns):
            selected.append(test)
    return selected, missing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-k", dest="patterns", action="append", default=[])
    parser.add_argument("modules", nargs="+")
    args = parser.parse_args(argv)

    if not args.patterns:
        raise SystemExit("unittest shard requires at least one -k pattern")

    tests = load_tests(args.modules)
    failed_loads = [test.id() for test in tests if test.id().startswith("unittest.loader._FailedTest.")]
    if failed_loads:
        suite = unittest.TestSuite(tests)
        result = unittest.TextTestRunner(verbosity=2 if args.verbose else 1).run(suite)
        return 0 if result.wasSuccessful() else 1

    chosen, missing = selected_tests(tests, args.patterns)
    if missing:
        for pattern in missing:
            print(f"stale unittest shard pattern did not match any test: {pattern}", file=sys.stderr)
        return 1
    if not chosen:
        print("unittest shard selected no tests", file=sys.stderr)
        return 1

    suite = unittest.TestSuite(chosen)
    result = unittest.TextTestRunner(verbosity=2 if args.verbose else 1).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
