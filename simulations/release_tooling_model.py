"""FlowGuard release-tooling model for FlowPilot-only publication.

The model isolates the installer and release-preflight contract. FlowPilot may
install its own skill folder and missing dependencies, but release tooling has
no authority to package or publish companion skill repositories.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import InvariantResult


@dataclass(frozen=True)
class State:
    manifest_written: bool = False
    installer_written: bool = False
    release_checker_written: bool = False
    host_capability_declared: bool = False
    host_provider_hardcoded_universal: bool = False
    dependency_sources_checked: bool = False
    dependency_sources_ready: bool = False
    dependency_sources_reported_missing: bool = False
    flowpilot_install_checked: bool = False
    missing_dependencies_installed: bool = False
    existing_skill_overwritten: bool = False
    overwrite_force_requested: bool = False
    privacy_scan_done: bool = False
    tracked_private_state_found: bool = False
    validation_done: bool = False
    validation_passed: bool = False
    flowpilot_release_prepared: bool = False
    flowpilot_publish_allowed: bool = False
    companion_repo_written: bool = False
    companion_skill_packaged: bool = False
    companion_skill_published: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def next_safe_states(state: State) -> Iterable[Transition]:
    if not state.manifest_written:
        yield Transition("dependency_manifest_written", replace(state, manifest_written=True))
        return
    if not state.installer_written:
        yield Transition("installer_written", replace(state, installer_written=True))
        return
    if not state.release_checker_written:
        yield Transition(
            "flowpilot_only_release_checker_written",
            replace(state, release_checker_written=True),
        )
        return
    if not state.host_capability_declared:
        yield Transition(
            "host_capability_mapping_declared",
            replace(state, host_capability_declared=True),
        )
        return
    if not state.dependency_sources_checked:
        yield Transition(
            "dependency_sources_checked_ready",
            replace(
                state,
                dependency_sources_checked=True,
                dependency_sources_ready=True,
            ),
        )
        yield Transition(
            "dependency_sources_checked_missing_reported",
            replace(
                state,
                dependency_sources_checked=True,
                dependency_sources_reported_missing=True,
            ),
        )
        return
    if state.dependency_sources_reported_missing:
        return
    if not state.flowpilot_install_checked:
        yield Transition(
            "flowpilot_install_checked",
            replace(state, flowpilot_install_checked=True),
        )
        return
    if not state.missing_dependencies_installed:
        yield Transition(
            "missing_dependencies_installed_without_overwrite",
            replace(state, missing_dependencies_installed=True),
        )
        return
    if not state.privacy_scan_done:
        yield Transition("privacy_scan_passed", replace(state, privacy_scan_done=True))
        return
    if not state.validation_done:
        yield Transition(
            "validation_passed",
            replace(state, validation_done=True, validation_passed=True),
        )
        return
    if not state.flowpilot_release_prepared:
        yield Transition(
            "flowpilot_release_prepared",
            replace(state, flowpilot_release_prepared=True),
        )
        return
    if not state.flowpilot_publish_allowed:
        yield Transition(
            "flowpilot_publish_allowed",
            replace(state, flowpilot_publish_allowed=True),
        )


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.existing_skill_overwritten and not state.overwrite_force_requested:
        failures.append("installer overwrote an existing skill without explicit force")
    if state.missing_dependencies_installed and not (
        state.manifest_written
        and state.installer_written
        and state.dependency_sources_checked
    ):
        failures.append("dependencies were installed before manifest and source checks")
    if state.flowpilot_release_prepared and not (
        state.manifest_written
        and state.release_checker_written
        and state.host_capability_declared
        and state.dependency_sources_checked
        and state.dependency_sources_ready
        and state.privacy_scan_done
        and not state.tracked_private_state_found
        and state.validation_done
        and state.validation_passed
    ):
        failures.append("FlowPilot release was prepared before dependency, privacy, and validation gates passed")
    if state.flowpilot_publish_allowed and not state.flowpilot_release_prepared:
        failures.append("FlowPilot publish was allowed before release preparation")
    if state.dependency_sources_reported_missing and state.flowpilot_publish_allowed:
        failures.append("FlowPilot publish was allowed while dependency sources were missing")
    if state.tracked_private_state_found and state.flowpilot_release_prepared:
        failures.append("FlowPilot release was prepared with tracked private state present")
    if state.companion_repo_written or state.companion_skill_packaged or state.companion_skill_published:
        failures.append("release tooling attempted to write, package, or publish a companion skill")
    if state.host_provider_hardcoded_universal:
        failures.append("release tooling hard-coded a host-specific provider as universal")
    return failures


def hazard_states() -> dict[str, State]:
    return {
        "overwrite_without_force": State(
            manifest_written=True,
            installer_written=True,
            dependency_sources_checked=True,
            existing_skill_overwritten=True,
        ),
        "publish_with_missing_dependency_source": State(
            manifest_written=True,
            installer_written=True,
            release_checker_written=True,
            dependency_sources_checked=True,
            dependency_sources_reported_missing=True,
            flowpilot_release_prepared=True,
            flowpilot_publish_allowed=True,
        ),
        "release_before_privacy_scan": State(
            manifest_written=True,
            installer_written=True,
            release_checker_written=True,
            dependency_sources_checked=True,
            dependency_sources_ready=True,
            validation_done=True,
            validation_passed=True,
            flowpilot_release_prepared=True,
        ),
        "release_with_private_state": State(
            manifest_written=True,
            installer_written=True,
            release_checker_written=True,
            dependency_sources_checked=True,
            dependency_sources_ready=True,
            privacy_scan_done=True,
            tracked_private_state_found=True,
            validation_done=True,
            validation_passed=True,
            flowpilot_release_prepared=True,
        ),
        "companion_skill_packaged": State(
            manifest_written=True,
            installer_written=True,
            release_checker_written=True,
            companion_skill_packaged=True,
        ),
        "companion_skill_published": State(
            manifest_written=True,
            installer_written=True,
            release_checker_written=True,
            companion_skill_published=True,
        ),
        "hardcoded_image_provider": State(
            manifest_written=True,
            installer_written=True,
            release_checker_written=True,
            host_provider_hardcoded_universal=True,
        ),
    }


def check_invariants(state: State) -> InvariantResult:
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()
