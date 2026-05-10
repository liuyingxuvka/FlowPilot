"""FlowGuard release-tooling model for FlowPilot-only publication.

Risk intent: the installer must make FlowPilot's dependency tiers visible,
install or block on missing required dependencies, keep optional UI companions
opt-in, and avoid silently mutating the Python environment without explicit
FlowGuard install authorization. Release tooling still has no authority to
package or publish companion skill repositories.
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
    dependency_bootstrap_notice_emitted: bool = False
    dependency_tiers_declared: bool = False
    required_skill_install_policy_declared: bool = False
    optional_skill_policy_declared: bool = False
    flowguard_public_source_declared: bool = False
    flowguard_install_authorized: bool = False
    flowguard_install_attempted: bool = False
    flowguard_install_verified: bool = False
    optional_install_requested: bool = False
    optional_dependencies_installed: bool = False
    optional_dependencies_skipped_without_include: bool = False
    required_dependencies_ready: bool = False
    dependency_sources_checked: bool = False
    dependency_sources_ready: bool = False
    dependency_sources_reported_missing: bool = False
    flowpilot_install_checked: bool = False
    repo_owned_skill_sync_checked: bool = False
    duplicate_installed_skill_names_checked: bool = False
    duplicate_installed_skill_names_found: bool = False
    cockpit_source_tracked: bool = False
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
    if not state.dependency_bootstrap_notice_emitted:
        yield Transition(
            "dependency_bootstrap_notice_emitted",
            replace(state, dependency_bootstrap_notice_emitted=True),
        )
        return
    if not state.dependency_tiers_declared:
        yield Transition(
            "dependency_tiers_declared",
            replace(state, dependency_tiers_declared=True),
        )
        return
    if not state.required_skill_install_policy_declared:
        yield Transition(
            "required_skill_install_policy_declared",
            replace(state, required_skill_install_policy_declared=True),
        )
        return
    if not state.optional_skill_policy_declared:
        yield Transition(
            "optional_skill_policy_declared",
            replace(
                state,
                optional_skill_policy_declared=True,
                optional_dependencies_skipped_without_include=True,
            ),
        )
        yield Transition(
            "optional_skill_install_requested",
            replace(
                state,
                optional_skill_policy_declared=True,
                optional_install_requested=True,
                optional_dependencies_installed=True,
            ),
        )
        return
    if not state.flowguard_public_source_declared:
        yield Transition(
            "flowguard_public_source_declared",
            replace(state, flowguard_public_source_declared=True),
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
    if not state.repo_owned_skill_sync_checked:
        yield Transition(
            "repo_owned_skill_sync_checked",
            replace(state, repo_owned_skill_sync_checked=True),
        )
        return
    if not state.duplicate_installed_skill_names_checked:
        yield Transition(
            "duplicate_installed_skill_names_absent",
            replace(state, duplicate_installed_skill_names_checked=True),
        )
        return
    if not state.missing_dependencies_installed:
        yield Transition(
            "required_skill_dependencies_installed_without_overwrite",
            replace(state, missing_dependencies_installed=True),
        )
        return
    if not state.flowguard_install_authorized:
        yield Transition(
            "flowguard_install_authorized",
            replace(state, flowguard_install_authorized=True),
        )
        return
    if not state.flowguard_install_attempted:
        yield Transition(
            "flowguard_install_attempted_from_public_source",
            replace(state, flowguard_install_attempted=True),
        )
        return
    if not state.flowguard_install_verified:
        yield Transition(
            "flowguard_install_verified",
            replace(state, flowguard_install_verified=True, required_dependencies_ready=True),
        )
        return
    if not state.cockpit_source_tracked:
        yield Transition(
            "cockpit_source_tracked",
            replace(state, cockpit_source_tracked=True),
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
        and state.dependency_bootstrap_notice_emitted
        and state.dependency_tiers_declared
        and state.required_skill_install_policy_declared
        and state.dependency_sources_checked
    ):
        failures.append("dependencies were installed before manifest and source checks")
    if state.flowguard_install_attempted and not (
        state.flowguard_public_source_declared and state.flowguard_install_authorized
    ):
        failures.append("FlowGuard install was attempted before public source and explicit authorization")
    if state.flowguard_install_verified and not state.flowguard_install_attempted:
        failures.append("FlowGuard was marked verified before install or import check")
    if state.optional_dependencies_installed and not state.optional_install_requested:
        failures.append("optional dependencies were installed without explicit optional request")
    if state.required_dependencies_ready and not (
        state.missing_dependencies_installed and state.flowguard_install_verified
    ):
        failures.append("required dependencies were marked ready before required skills and FlowGuard passed")
    if state.flowpilot_release_prepared and not (
        state.manifest_written
        and state.release_checker_written
        and state.host_capability_declared
        and state.dependency_bootstrap_notice_emitted
        and state.dependency_tiers_declared
        and state.required_skill_install_policy_declared
        and state.optional_skill_policy_declared
        and state.flowguard_public_source_declared
        and state.dependency_sources_checked
        and state.dependency_sources_ready
        and state.required_dependencies_ready
        and state.flowpilot_install_checked
        and state.repo_owned_skill_sync_checked
        and state.duplicate_installed_skill_names_checked
        and not state.duplicate_installed_skill_names_found
        and state.cockpit_source_tracked
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
    if state.duplicate_installed_skill_names_found and state.flowpilot_release_prepared:
        failures.append("FlowPilot release was prepared while duplicate installed skill names existed")
    if state.flowpilot_release_prepared and not state.cockpit_source_tracked:
        failures.append("FlowPilot release was prepared before Cockpit source files were tracked")
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
        "flowguard_install_without_authorization": State(
            manifest_written=True,
            installer_written=True,
            dependency_bootstrap_notice_emitted=True,
            dependency_tiers_declared=True,
            required_skill_install_policy_declared=True,
            flowguard_public_source_declared=True,
            flowguard_install_attempted=True,
        ),
        "flowguard_ready_without_verification": State(
            manifest_written=True,
            installer_written=True,
            dependency_bootstrap_notice_emitted=True,
            dependency_tiers_declared=True,
            required_skill_install_policy_declared=True,
            flowguard_public_source_declared=True,
            flowguard_install_authorized=True,
            required_dependencies_ready=True,
        ),
        "optional_install_without_request": State(
            manifest_written=True,
            installer_written=True,
            dependency_bootstrap_notice_emitted=True,
            dependency_tiers_declared=True,
            optional_skill_policy_declared=True,
            optional_dependencies_installed=True,
        ),
        "release_without_dependency_notice": State(
            manifest_written=True,
            installer_written=True,
            release_checker_written=True,
            host_capability_declared=True,
            dependency_tiers_declared=True,
            required_skill_install_policy_declared=True,
            optional_skill_policy_declared=True,
            flowguard_public_source_declared=True,
            dependency_sources_checked=True,
            dependency_sources_ready=True,
            required_dependencies_ready=True,
            flowpilot_install_checked=True,
            repo_owned_skill_sync_checked=True,
            duplicate_installed_skill_names_checked=True,
            cockpit_source_tracked=True,
            privacy_scan_done=True,
            validation_done=True,
            validation_passed=True,
            flowpilot_release_prepared=True,
        ),
        "publish_with_missing_dependency_source": State(
            manifest_written=True,
            installer_written=True,
            release_checker_written=True,
            dependency_bootstrap_notice_emitted=True,
            dependency_tiers_declared=True,
            required_skill_install_policy_declared=True,
            optional_skill_policy_declared=True,
            flowguard_public_source_declared=True,
            dependency_sources_checked=True,
            dependency_sources_reported_missing=True,
            flowpilot_release_prepared=True,
            flowpilot_publish_allowed=True,
        ),
        "release_before_privacy_scan": State(
            manifest_written=True,
            installer_written=True,
            release_checker_written=True,
            host_capability_declared=True,
            dependency_bootstrap_notice_emitted=True,
            dependency_tiers_declared=True,
            required_skill_install_policy_declared=True,
            optional_skill_policy_declared=True,
            flowguard_public_source_declared=True,
            dependency_sources_checked=True,
            dependency_sources_ready=True,
            required_dependencies_ready=True,
            flowpilot_install_checked=True,
            repo_owned_skill_sync_checked=True,
            duplicate_installed_skill_names_checked=True,
            cockpit_source_tracked=True,
            validation_done=True,
            validation_passed=True,
            flowpilot_release_prepared=True,
        ),
        "release_with_private_state": State(
            manifest_written=True,
            installer_written=True,
            release_checker_written=True,
            host_capability_declared=True,
            dependency_bootstrap_notice_emitted=True,
            dependency_tiers_declared=True,
            required_skill_install_policy_declared=True,
            optional_skill_policy_declared=True,
            flowguard_public_source_declared=True,
            dependency_sources_checked=True,
            dependency_sources_ready=True,
            required_dependencies_ready=True,
            flowpilot_install_checked=True,
            repo_owned_skill_sync_checked=True,
            duplicate_installed_skill_names_checked=True,
            cockpit_source_tracked=True,
            privacy_scan_done=True,
            tracked_private_state_found=True,
            validation_done=True,
            validation_passed=True,
            flowpilot_release_prepared=True,
        ),
        "release_with_duplicate_installed_skill_names": State(
            manifest_written=True,
            installer_written=True,
            release_checker_written=True,
            host_capability_declared=True,
            dependency_bootstrap_notice_emitted=True,
            dependency_tiers_declared=True,
            required_skill_install_policy_declared=True,
            optional_skill_policy_declared=True,
            flowguard_public_source_declared=True,
            dependency_sources_checked=True,
            dependency_sources_ready=True,
            required_dependencies_ready=True,
            flowpilot_install_checked=True,
            repo_owned_skill_sync_checked=True,
            duplicate_installed_skill_names_checked=True,
            duplicate_installed_skill_names_found=True,
            cockpit_source_tracked=True,
            privacy_scan_done=True,
            validation_done=True,
            validation_passed=True,
            flowpilot_release_prepared=True,
        ),
        "release_with_untracked_cockpit_source": State(
            manifest_written=True,
            installer_written=True,
            release_checker_written=True,
            host_capability_declared=True,
            dependency_bootstrap_notice_emitted=True,
            dependency_tiers_declared=True,
            required_skill_install_policy_declared=True,
            optional_skill_policy_declared=True,
            flowguard_public_source_declared=True,
            dependency_sources_checked=True,
            dependency_sources_ready=True,
            required_dependencies_ready=True,
            flowpilot_install_checked=True,
            repo_owned_skill_sync_checked=True,
            duplicate_installed_skill_names_checked=True,
            privacy_scan_done=True,
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
