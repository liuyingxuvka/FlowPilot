from __future__ import annotations

import unittest

from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase
from tests.router_runtime.route_mutation_draft_activation import RouteMutationDraftActivationRuntimeTests
from tests.router_runtime.route_mutation_model_miss_triage import RouteMutationModelMissTriageRuntimeTests
from tests.router_runtime.route_mutation_acceptance_repair import RouteMutationAcceptanceRepairRuntimeTests
from tests.router_runtime.route_mutation_preconditions import RouteMutationPreconditionRuntimeTests
from tests.router_runtime.route_mutation_transactions import RouteMutationTransactionRuntimeTests
from tests.router_runtime.route_mutation_topology import RouteMutationTopologyRuntimeTests
from tests.router_runtime.route_mutation_sibling_replacement import RouteMutationSiblingReplacementRuntimeTests
from tests.router_runtime.route_mutation_parent_backward import RouteMutationParentBackwardRuntimeTests


ROUTE_MUTATION_RUNTIME_TEST_CASES = (
    RouteMutationDraftActivationRuntimeTests,
    RouteMutationModelMissTriageRuntimeTests,
    RouteMutationAcceptanceRepairRuntimeTests,
    RouteMutationPreconditionRuntimeTests,
    RouteMutationTransactionRuntimeTests,
    RouteMutationTopologyRuntimeTests,
    RouteMutationSiblingReplacementRuntimeTests,
    RouteMutationParentBackwardRuntimeTests,
)


class RouteMutationRuntimeTests(FlowPilotRouterRuntimeTestBase):
    """Aggregate for explicit full route-mutation oracle runs."""


for _test_case in ROUTE_MUTATION_RUNTIME_TEST_CASES:
    for _test_name in unittest.TestLoader().getTestCaseNames(_test_case):
        if hasattr(RouteMutationRuntimeTests, _test_name):
            raise RuntimeError(f"duplicate route-mutation runtime test: {_test_name}")
        setattr(RouteMutationRuntimeTests, _test_name, getattr(_test_case, _test_name))


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    del tests, pattern
    return loader.loadTestsFromTestCase(RouteMutationRuntimeTests)


if __name__ == "__main__":
    unittest.main()
