from __future__ import annotations

import unittest

from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase
from tests.router_runtime.ack_return import AckReturnRuntimeTests
from tests.router_runtime.bootstrap_cli import BootstrapCliRuntimeTests
from tests.router_runtime.cards import CardsRuntimeTests
from tests.router_runtime.closure import ClosureRuntimeTests
from tests.router_runtime.control_blockers import ControlBlockersRuntimeTests
from tests.router_runtime.controller import ControllerRuntimeTests
from tests.router_runtime.dispatch_gate import DispatchGateRuntimeTests
from tests.router_runtime.foreground import ForegroundRuntimeTests
from tests.router_runtime.foreground_controller import ForegroundControllerRuntimeTests
from tests.router_runtime.material_modeling import MaterialModelingRuntimeTests
from tests.router_runtime.packets import PacketsRuntimeTests
from tests.router_runtime.pm_role_work import PmRoleWorkRuntimeTests
from tests.router_runtime.quality_gates import QualityGatesRuntimeTests
from tests.router_runtime.resume import ResumeRuntimeTests
from tests.router_runtime.route_mutation_acceptance_repair import RouteMutationAcceptanceRepairRuntimeTests
from tests.router_runtime.route_mutation_draft_activation import RouteMutationDraftActivationRuntimeTests
from tests.router_runtime.route_mutation_model_miss_triage import RouteMutationModelMissTriageRuntimeTests
from tests.router_runtime.route_mutation_parent_backward import RouteMutationParentBackwardRuntimeTests
from tests.router_runtime.route_mutation_preconditions import RouteMutationPreconditionRuntimeTests
from tests.router_runtime.route_mutation_sibling_replacement import RouteMutationSiblingReplacementRuntimeTests
from tests.router_runtime.route_mutation_topology import RouteMutationTopologyRuntimeTests
from tests.router_runtime.route_mutation_transactions import RouteMutationTransactionRuntimeTests
from tests.router_runtime.startup_bootstrap import StartupBootstrapRuntimeTests
from tests.router_runtime.startup_daemon import StartupDaemonRuntimeTests
from tests.router_runtime.terminal import TerminalRuntimeTests


class FlowPilotRouterRuntimeTests(FlowPilotRouterRuntimeTestBase):
    pass


def _test_names(test_case: type[unittest.TestCase]) -> tuple[str, ...]:
    return tuple(name for name in unittest.TestLoader().getTestCaseNames(test_case))


_DOMAIN_TEST_CASES = (
    AckReturnRuntimeTests,
    BootstrapCliRuntimeTests,
    CardsRuntimeTests,
    ClosureRuntimeTests,
    ControlBlockersRuntimeTests,
    ControllerRuntimeTests,
    DispatchGateRuntimeTests,
    ForegroundRuntimeTests,
    ForegroundControllerRuntimeTests,
    MaterialModelingRuntimeTests,
    PacketsRuntimeTests,
    PmRoleWorkRuntimeTests,
    QualityGatesRuntimeTests,
    ResumeRuntimeTests,
    RouteMutationDraftActivationRuntimeTests,
    RouteMutationModelMissTriageRuntimeTests,
    RouteMutationAcceptanceRepairRuntimeTests,
    RouteMutationPreconditionRuntimeTests,
    RouteMutationTransactionRuntimeTests,
    RouteMutationTopologyRuntimeTests,
    RouteMutationSiblingReplacementRuntimeTests,
    RouteMutationParentBackwardRuntimeTests,
    StartupBootstrapRuntimeTests,
    StartupDaemonRuntimeTests,
    TerminalRuntimeTests,
)

_MIGRATED_TEST_NAMES: set[str] = set()
for _test_case in _DOMAIN_TEST_CASES:
    for _test_name in _test_names(_test_case):
        if _test_name in _MIGRATED_TEST_NAMES:
            raise RuntimeError(f"duplicate migrated router runtime test: {_test_name}")
        _MIGRATED_TEST_NAMES.add(_test_name)
        setattr(FlowPilotRouterRuntimeTests, _test_name, getattr(_test_case, _test_name))


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    suite = unittest.TestSuite()
    for _test_case in _DOMAIN_TEST_CASES:
        suite.addTests(loader.loadTestsFromTestCase(_test_case))
    return suite


if __name__ == "__main__":
    unittest.main()
