"""FlowGuard Risk Purpose Header.

Created with FlowGuard: https://github.com/liuyingxuvka/FlowGuard
Purpose: review the cross-repository observability plan for long FlowGuard
checks before changing FlowGuard skill guidance or FlowPilot legacy runners.
Guards against: scattered logs, missing exit evidence, stdout progress
pollution, final-only runners being misreported as live progress, missing local
skill sync, and pushing the wrong GitHub repository before user approval.
Run: `python simulations/run_long_check_observability_checks.py`
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, Sequence

from flowguard import (
    FunctionResult,
    Invariant,
    InvariantResult,
    Scenario,
    ScenarioExpectation,
    Workflow,
    review_scenarios,
)


@dataclass(frozen=True)
class ObservabilityPlan:
    log_root: str = ""
    artifacts: tuple[str, ...] = ()
    final_report_fields: tuple[str, ...] = ()
    progress_stream: str = ""
    progress_boundary: str = ""
    proof_reuse_reported: bool = False
    flowguard_skill_updated: bool = False
    flowguard_installed_synced: bool = False
    flowpilot_runner_progress: bool = False
    flowpilot_rule_updated: bool = False
    flowpilot_installed_synced: bool = False
    flowguard_local_commit: bool = False
    flowpilot_local_commit: bool = False
    github_push_policy: str = "none"
    finalized: bool = False


@dataclass(frozen=True)
class PlanStep:
    name: str


class ApplyPlanStep:
    name = "ApplyPlanStep"
    reads = ("ObservabilityPlan",)
    writes = ("ObservabilityPlan",)
    input_description = "PlanStep"
    output_description = "ObservabilityPlan"
    idempotency = "same step writes the same plan field"
    accepted_input_type = PlanStep

    def apply(self, input_obj: PlanStep, state: ObservabilityPlan) -> Iterable[FunctionResult]:
        new_state = apply_step(input_obj.name, state)
        yield FunctionResult(
            output=input_obj,
            new_state=new_state,
            label=input_obj.name,
            reason=f"applied observability plan step {input_obj.name}",
        )


def apply_step(step: str, state: ObservabilityPlan) -> ObservabilityPlan:
    if step == "use_fixed_background_root":
        return replace(state, log_root="tmp/flowguard_background")
    if step == "use_task_local_root":
        return replace(state, log_root="tmp/task_local")
    if step == "record_all_artifacts":
        return replace(
            state,
            artifacts=("out", "err", "combined", "exit", "meta"),
        )
    if step == "omit_exit_artifact":
        return replace(state, artifacts=("out", "err", "combined", "meta"))
    if step == "report_all_evidence":
        return replace(
            state,
            final_report_fields=("path", "exit", "last_update", "completion", "proof_reuse"),
        )
    if step == "report_path_only":
        return replace(state, final_report_fields=("path",))
    if step == "progress_to_stderr":
        return replace(state, progress_stream="stderr")
    if step == "progress_to_stdout":
        return replace(state, progress_stream="stdout")
    if step == "declare_custom_runner_boundary":
        return replace(state, progress_boundary="direct_explorer_vs_custom_runner")
    if step == "claim_all_runners_have_explorer_progress":
        return replace(state, progress_boundary="all_runners_live")
    if step == "report_proof_reuse":
        return replace(state, proof_reuse_reported=True)
    if step == "update_flowguard_skill":
        return replace(state, flowguard_skill_updated=True)
    if step == "sync_flowguard_installed_skill":
        return replace(state, flowguard_installed_synced=True)
    if step == "add_flowpilot_runner_progress":
        return replace(state, flowpilot_runner_progress=True)
    if step == "update_flowpilot_repo_rule":
        return replace(state, flowpilot_rule_updated=True)
    if step == "sync_flowpilot_installed_skill":
        return replace(state, flowpilot_installed_synced=True)
    if step == "commit_flowguard_locally":
        return replace(state, flowguard_local_commit=True)
    if step == "commit_flowpilot_locally":
        return replace(state, flowpilot_local_commit=True)
    if step == "hold_github_push":
        return replace(state, github_push_policy="hold_until_user_approval")
    if step == "push_flowpilot_only":
        return replace(state, github_push_policy="pushed_flowpilot_only")
    if step == "push_without_user_approval":
        return replace(state, github_push_policy="pushed_without_user_approval")
    if step == "finalize":
        return replace(state, finalized=True)
    return state


def _active(state: ObservabilityPlan) -> bool:
    return state.finalized


def _pass() -> InvariantResult:
    return InvariantResult.pass_()


def _fail(message: str) -> InvariantResult:
    return InvariantResult.fail(message)


def fixed_log_root_required(state: ObservabilityPlan, _trace: object) -> InvariantResult:
    if not _active(state):
        return _pass()
    if state.log_root != "tmp/flowguard_background":
        return _fail("long checks must default to tmp/flowguard_background")
    return _pass()


def all_log_artifacts_required(state: ObservabilityPlan, _trace: object) -> InvariantResult:
    if not _active(state):
        return _pass()
    required = {"out", "err", "combined", "exit", "meta"}
    if set(state.artifacts) != required:
        return _fail("background evidence must include out, err, combined, exit, and meta artifacts")
    return _pass()


def final_report_has_completion_evidence(state: ObservabilityPlan, _trace: object) -> InvariantResult:
    if not _active(state):
        return _pass()
    required = {"path", "exit", "last_update", "completion", "proof_reuse"}
    if not required.issubset(set(state.final_report_fields)):
        return _fail("final report must cite path, exit status, timestamp, completion, and proof reuse")
    return _pass()


def progress_uses_stderr(state: ObservabilityPlan, _trace: object) -> InvariantResult:
    if not _active(state):
        return _pass()
    if state.progress_stream != "stderr":
        return _fail("progress must go to stderr so stdout reports stay parseable")
    return _pass()


def custom_runner_boundary_is_explicit(state: ObservabilityPlan, _trace: object) -> InvariantResult:
    if not _active(state):
        return _pass()
    if state.progress_boundary != "direct_explorer_vs_custom_runner":
        return _fail("reports must distinguish direct Explorer progress from custom final-only runners")
    return _pass()


def proof_reuse_is_visible(state: ObservabilityPlan, _trace: object) -> InvariantResult:
    if not _active(state):
        return _pass()
    if not state.proof_reuse_reported:
        return _fail("valid proof reuse must be reported instead of implied as a fresh run")
    return _pass()


def both_repositories_are_synced_and_committed(state: ObservabilityPlan, _trace: object) -> InvariantResult:
    if not _active(state):
        return _pass()
    if not state.flowguard_skill_updated or not state.flowguard_installed_synced:
        return _fail("FlowGuard skill source and installed skill must both be updated")
    if not state.flowpilot_runner_progress or not state.flowpilot_rule_updated:
        return _fail("FlowPilot runner progress and project rules must both be updated")
    if not state.flowpilot_installed_synced:
        return _fail("FlowPilot installed skill sync/check must be completed")
    if not state.flowguard_local_commit or not state.flowpilot_local_commit:
        return _fail("both repositories must be committed locally before completion")
    return _pass()


def github_push_waits_for_user(state: ObservabilityPlan, _trace: object) -> InvariantResult:
    if not _active(state):
        return _pass()
    if state.github_push_policy != "hold_until_user_approval":
        return _fail("GitHub push must wait for explicit user approval")
    return _pass()


INVARIANTS = (
    Invariant("fixed_log_root_required", "Long checks use the fixed background log root.", fixed_log_root_required),
    Invariant("all_log_artifacts_required", "Background logs include every evidence artifact.", all_log_artifacts_required),
    Invariant(
        "final_report_has_completion_evidence",
        "Final reports cite concrete completion evidence.",
        final_report_has_completion_evidence,
    ),
    Invariant("progress_uses_stderr", "Progress does not pollute stdout.", progress_uses_stderr),
    Invariant(
        "custom_runner_boundary_is_explicit",
        "Custom runner progress boundaries are explicit.",
        custom_runner_boundary_is_explicit,
    ),
    Invariant("proof_reuse_is_visible", "Proof reuse is reported explicitly.", proof_reuse_is_visible),
    Invariant(
        "both_repositories_are_synced_and_committed",
        "FlowGuard and FlowPilot are synced and committed locally.",
        both_repositories_are_synced_and_committed,
    ),
    Invariant("github_push_waits_for_user", "GitHub push waits for user approval.", github_push_waits_for_user),
)


CORRECT_PLAN = (
    "use_fixed_background_root",
    "record_all_artifacts",
    "report_all_evidence",
    "progress_to_stderr",
    "declare_custom_runner_boundary",
    "report_proof_reuse",
    "update_flowguard_skill",
    "sync_flowguard_installed_skill",
    "add_flowpilot_runner_progress",
    "update_flowpilot_repo_rule",
    "sync_flowpilot_installed_skill",
    "commit_flowguard_locally",
    "commit_flowpilot_locally",
    "hold_github_push",
    "finalize",
)


def _steps(names: Sequence[str]) -> tuple[PlanStep, ...]:
    return tuple(PlanStep(name) for name in names)


def _expect_ok() -> ScenarioExpectation:
    return ScenarioExpectation(
        expected_status="ok",
        required_trace_labels=("finalize",),
        summary="OK; long-check observability plan is safe to implement",
    )


def _expect_violation(name: str) -> ScenarioExpectation:
    return ScenarioExpectation(
        expected_status="violation",
        expected_violation_names=(name,),
        summary=f"VIOLATION; {name}",
    )


def _scenario(
    name: str,
    description: str,
    steps: Sequence[str],
    expected: ScenarioExpectation,
) -> Scenario:
    return Scenario(
        name=name,
        description=description,
        initial_state=ObservabilityPlan(),
        external_input_sequence=_steps(steps),
        expected=expected,
        workflow=Workflow((ApplyPlanStep(),), name="long_check_observability"),
        invariants=INVARIANTS,
        tags=("long_check_observability",),
    )


def long_check_observability_scenarios() -> tuple[Scenario, ...]:
    return (
        _scenario(
            "LCO01_correct_cross_repo_plan_passes",
            "The agreed plan updates FlowGuard guidance and FlowPilot runners, syncs both installs, commits locally, and holds GitHub push.",
            CORRECT_PLAN,
            _expect_ok(),
        ),
        _scenario(
            "LCOB01_task_local_logs_are_not_default",
            "Broken plan keeps ad-hoc task-local logs as the default.",
            ("use_task_local_root",) + CORRECT_PLAN[1:],
            _expect_violation("fixed_log_root_required"),
        ),
        _scenario(
            "LCOB02_missing_exit_artifact_blocks_completion",
            "Broken plan omits exit-status evidence.",
            CORRECT_PLAN[:1] + ("omit_exit_artifact",) + CORRECT_PLAN[2:],
            _expect_violation("all_log_artifacts_required"),
        ),
        _scenario(
            "LCOB03_path_only_report_is_not_enough",
            "Broken plan reports only a log path without completion evidence.",
            CORRECT_PLAN[:2] + ("report_path_only",) + CORRECT_PLAN[3:],
            _expect_violation("final_report_has_completion_evidence"),
        ),
        _scenario(
            "LCOB04_stdout_progress_breaks_final_report_stream",
            "Broken plan writes progress to stdout.",
            CORRECT_PLAN[:3] + ("progress_to_stdout",) + CORRECT_PLAN[4:],
            _expect_violation("progress_uses_stderr"),
        ),
        _scenario(
            "LCOB05_custom_runner_boundary_hidden",
            "Broken plan claims all runners have Explorer progress even when custom runners only emit final reports.",
            CORRECT_PLAN[:4] + ("claim_all_runners_have_explorer_progress",) + CORRECT_PLAN[5:],
            _expect_violation("custom_runner_boundary_is_explicit"),
        ),
        _scenario(
            "LCOB06_proof_reuse_not_reported",
            "Broken plan reuses proof without telling the user.",
            CORRECT_PLAN[:5] + CORRECT_PLAN[6:],
            _expect_violation("proof_reuse_is_visible"),
        ),
        _scenario(
            "LCOB07_flowpilot_install_sync_missing",
            "Broken plan updates FlowPilot source but skips installed skill sync.",
            CORRECT_PLAN[:10] + CORRECT_PLAN[11:],
            _expect_violation("both_repositories_are_synced_and_committed"),
        ),
        _scenario(
            "LCOB08_push_happens_before_user_approval",
            "Broken plan pushes before the user approves the final phase.",
            CORRECT_PLAN[:-2] + ("push_without_user_approval", "finalize"),
            _expect_violation("github_push_waits_for_user"),
        ),
    )


def run_long_check_observability_review():
    return review_scenarios(long_check_observability_scenarios())


__all__ = [
    "ObservabilityPlan",
    "PlanStep",
    "long_check_observability_scenarios",
    "run_long_check_observability_review",
]
