from __future__ import annotations

import unittest

from tests.test_flowpilot_router_runtime import FlowPilotRouterRuntimeTests


def runtime_suite(test_names: tuple[str, ...]) -> unittest.TestSuite:
    suite = unittest.TestSuite()
    for name in test_names:
        suite.addTest(FlowPilotRouterRuntimeTests(name))
    return suite


def load_named_runtime_tests(
    loader: unittest.TestLoader,
    tests: unittest.TestSuite,
    pattern: str | None,
    test_names: tuple[str, ...],
) -> unittest.TestSuite:
    del loader, tests, pattern
    return runtime_suite(test_names)
