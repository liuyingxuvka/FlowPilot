from __future__ import annotations

import unittest

from tests.flowpilot_route_mutation_contracts import (
    TestRouteMutationChildContractFixture,
    TestRouteMutationParentContracts,
)


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    del tests, pattern
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestRouteMutationChildContractFixture))
    suite.addTests(loader.loadTestsFromTestCase(TestRouteMutationParentContracts))
    return suite


if __name__ == "__main__":
    unittest.main()
