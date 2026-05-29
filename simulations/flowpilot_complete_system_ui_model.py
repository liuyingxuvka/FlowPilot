"""FlowGuard UI-flow model for complete FlowPilot startup and Cockpit status."""

from __future__ import annotations

from flowguard import (
    UIControl,
    UIDisplayElement,
    UIFeatureJourney,
    UIInteractionModel,
    UIJourneyCoverage,
    UIJourneyEntryPoint,
    UIRegionRecommendation,
    UIStateNode,
    UIStructureDerivation,
    UITerminalActionAllowance,
    UITransition,
)


MODEL_ID = "flowpilot_complete_system_ui_flow"


def build_interaction_model() -> UIInteractionModel:
    controls = tuple(
        UIControl(control_id, label=control_id, function_key=function_key, rationale=rationale)
        for control_id, function_key, rationale in (
            ("open", "open", "Open native startup intake."),
            ("fallback", "fallback", "Use chat route-sign fallback when Cockpit is unavailable."),
            ("submit", "submit", "Submit sealed startup intake into the current run."),
            ("cancel", "cancel", "Cancel startup without route execution."),
            ("refresh", "refresh", "Refresh public status projection."),
            ("pause", "pause", "Submit a typed pause event through the router."),
            ("stop", "stop", "Submit a typed stop event through the router."),
            ("logs", "logs", "Open public log/proof artifact locations."),
            ("resume", "resume", "Submit a typed resume event through the router."),
        )
    )
    states = (
        UIStateNode(
            "launch",
            visible_controls=("open", "fallback"),
            enabled_controls=("open", "fallback"),
            visible_displays=("status",),
            rationale="Initial operation surface before intake authority exists.",
        ),
        UIStateNode(
            "intake",
            visible_controls=("submit", "cancel"),
            enabled_controls=("submit", "cancel"),
            visible_displays=("intake_summary",),
            rationale="Startup intake is collecting sealed current-run options.",
        ),
        UIStateNode(
            "running",
            terminal=True,
            visible_controls=("refresh", "pause", "stop", "logs"),
            enabled_controls=("refresh", "pause", "stop", "logs"),
            visible_displays=("status", "blockers"),
            rationale="A current run exists and Cockpit is showing public route status.",
        ),
        UIStateNode(
            "paused",
            visible_controls=("refresh", "resume", "stop", "logs"),
            enabled_controls=("refresh", "resume", "stop", "logs"),
            visible_displays=("status", "blockers"),
            rationale="A current run is paused but still has router-owned lifecycle state.",
        ),
        UIStateNode(
            "fallback",
            terminal=True,
            visible_controls=("refresh",),
            enabled_controls=("refresh",),
            visible_displays=("status",),
            rationale="Chat route-sign fallback renders the same projection without Cockpit.",
        ),
        UIStateNode(
            "stopped",
            terminal=True,
            failure=True,
            visible_displays=("status",),
            rationale="Startup or active run was cancelled/stopped.",
        ),
    )
    displays = (
        UIDisplayElement("status", "public_status", label="Status", rationale="Public status projection."),
        UIDisplayElement("intake_summary", "intake", label="Intake", rationale="Startup options without sealed body text."),
        UIDisplayElement("blockers", "blockers", label="Blockers", rationale="Current public blocker summary."),
    )
    transitions = (
        UITransition("open_event", "open", "launch", "intake", function_block="startup_intake", output="open intake", rationale="User starts native intake."),
        UITransition("fallback_event", "fallback", "launch", "fallback", function_block="chat_fallback", output="chat fallback", rationale="Cockpit unavailable or user chooses chat route signs."),
        UITransition("submit_event", "submit", "intake", "running", function_block="sealed_intake", output="sealed record", rationale="Intake writes current-run envelope/body evidence."),
        UITransition("cancel_event", "cancel", "intake", "stopped", function_block="cancel", output="stop", rationale="Cancellation prevents route work."),
        UITransition("refresh_running", "refresh", "running", "running", function_block="projection", output="status", rationale="Refresh derives public projection from ledger."),
        UITransition("pause_event", "pause", "running", "paused", function_block="typed_event", output="pause", rationale="Pause is a typed event consumed by router."),
        UITransition("stop_running", "stop", "running", "stopped", function_block="typed_event", output="stop", rationale="Stop is a typed event consumed by router."),
        UITransition("logs_running", "logs", "running", "running", function_block="open_logs", output="logs", rationale="Open public proof/log locations."),
        UITransition("refresh_paused", "refresh", "paused", "paused", function_block="projection", output="status", rationale="Paused refresh remains projection-only."),
        UITransition("resume_event", "resume", "paused", "running", function_block="typed_event", output="resume", rationale="Resume is a typed event consumed by router."),
        UITransition("stop_paused", "stop", "paused", "stopped", function_block="typed_event", output="stop", rationale="Stop while paused is still router-owned."),
        UITransition("logs_paused", "logs", "paused", "paused", function_block="open_logs", output="logs", rationale="Paused log open does not mutate state."),
        UITransition("refresh_fallback", "refresh", "fallback", "fallback", function_block="projection", output="status", rationale="Chat fallback refresh derives the same projection."),
    )
    return UIInteractionModel(
        MODEL_ID,
        "launch",
        states=states,
        controls=controls,
        transitions=transitions,
        displays=displays,
        source_product_model_id="complete-black-box-flowpilot-system",
        source_product_model_path="openspec/changes/complete-black-box-flowpilot-system/specs/complete-black-box-flowpilot-system/spec.md",
        validation_boundaries=("sealed_body_not_rendered", "projection_only_ui", "typed_events_only"),
        rationale="Models startup intake, Cockpit status, chat fallback, and lifecycle controls as UI event x UI state transitions.",
    )


def build_journey_coverage() -> UIJourneyCoverage:
    return UIJourneyCoverage(
        "flowpilot_complete_system_ui_journey",
        MODEL_ID,
        "launch",
        entry_points=(
            UIJourneyEntryPoint("entry_open", "open", "open_event", source_state_ids=("launch",), rationale="Primary Cockpit startup path."),
            UIJourneyEntryPoint("entry_fallback", "fallback", "fallback_event", source_state_ids=("launch",), rationale="Chat route-sign fallback path."),
        ),
        feature_journeys=(
            UIFeatureJourney(
                "startup",
                "Startup to running status",
                entry_point_ids=("entry_open",),
                required_state_ids=("launch", "intake", "running", "paused"),
                required_event_ids=(
                    "open_event",
                    "submit_event",
                    "refresh_running",
                    "pause_event",
                    "resume_event",
                    "logs_running",
                    "logs_paused",
                    "refresh_paused",
                ),
                success_terminal_state_ids=("running",),
                failure_state_ids=("stopped",),
                recovery_event_ids=("resume_event", "refresh_running", "refresh_paused", "pause_event"),
                cancel_event_ids=("cancel_event",),
                exit_event_ids=("stop_running", "stop_paused"),
                validation_boundaries=("startup_to_status", "projection_only_controls"),
                rationale="Covers the main Cockpit journey and all operational controls reachable from status.",
            ),
            UIFeatureJourney(
                "fallback",
                "Chat route-sign fallback status",
                entry_point_ids=("entry_fallback",),
                required_state_ids=("launch", "fallback"),
                required_event_ids=("fallback_event", "refresh_fallback"),
                success_terminal_state_ids=("fallback",),
                recovery_event_ids=("refresh_fallback",),
                validation_boundaries=("chat_fallback_status",),
                rationale="Covers the no-Cockpit display surface without changing runtime authority.",
            ),
        ),
        terminal_action_allowances=(
            UITerminalActionAllowance("intake", "cancel_event", "cancel", "Cancel startup before route execution."),
            UITerminalActionAllowance("running", "refresh_running", "recovery", "Refresh public status projection."),
            UITerminalActionAllowance("running", "pause_event", "recovery", "Pause route via typed router event."),
            UITerminalActionAllowance("running", "logs_running", "export", "Open logs/proof artifacts."),
            UITerminalActionAllowance("running", "stop_running", "exit", "Stop the run from running status."),
            UITerminalActionAllowance("paused", "stop_paused", "exit", "Stop the run from paused status."),
            UITerminalActionAllowance("fallback", "refresh_fallback", "recovery", "Refresh chat fallback projection."),
        ),
        interaction_model_reviewed=True,
        validation_boundaries=("all_reachable_events", "terminal_or_recovery_paths"),
        rationale="Launch-to-terminal/recovery coverage for complete FlowPilot operation surfaces.",
    )


def build_structure_derivation() -> UIStructureDerivation:
    return UIStructureDerivation(
        "flowpilot_complete_system_ui_structure",
        MODEL_ID,
        "cockpit",
        target_regions=(
            UIRegionRecommendation("root", level="global", placement="shell", stable_across_states=True, validation_boundaries=("root",), rationale="Stable shell."),
            UIRegionRecommendation(
                "startup",
                level="secondary",
                placement="left",
                parent_region_id="root",
                owns_states=("launch", "intake"),
                owns_controls=("open", "fallback", "submit", "cancel"),
                owns_events=("open_event", "fallback_event", "submit_event", "cancel_event"),
                owns_displays=("intake_summary",),
                stable_across_states=True,
                validation_boundaries=("startup_region",),
                rationale="Owns intake and startup choice controls.",
            ),
            UIRegionRecommendation(
                "status",
                level="global",
                placement="main",
                parent_region_id="root",
                owns_states=("running", "paused", "fallback", "stopped"),
                owns_controls=("refresh", "pause", "resume", "stop", "logs"),
                owns_events=(
                    "refresh_running",
                    "pause_event",
                    "resume_event",
                    "stop_running",
                    "stop_paused",
                    "logs_running",
                    "logs_paused",
                    "refresh_paused",
                    "refresh_fallback",
                ),
                owns_displays=("status", "blockers"),
                stable_across_states=True,
                validation_boundaries=("status_region",),
                rationale="Owns public run status, blockers, and lifecycle events.",
            ),
        ),
        interaction_model_reviewed=True,
        state_region_map=(
            ("launch", "startup"),
            ("intake", "startup"),
            ("running", "status"),
            ("paused", "status"),
            ("fallback", "status"),
            ("stopped", "status"),
        ),
        control_region_map=(
            ("open", "startup"),
            ("fallback", "startup"),
            ("submit", "startup"),
            ("cancel", "startup"),
            ("refresh", "status"),
            ("pause", "status"),
            ("resume", "status"),
            ("stop", "status"),
            ("logs", "status"),
        ),
        event_region_map=(
            ("open_event", "startup"),
            ("fallback_event", "startup"),
            ("submit_event", "startup"),
            ("cancel_event", "startup"),
            ("refresh_running", "status"),
            ("pause_event", "status"),
            ("resume_event", "status"),
            ("stop_running", "status"),
            ("stop_paused", "status"),
            ("logs_running", "status"),
            ("logs_paused", "status"),
            ("refresh_paused", "status"),
            ("refresh_fallback", "status"),
        ),
        display_region_map=(("status", "status"), ("blockers", "status"), ("intake_summary", "startup")),
        hierarchy_edges=(("root", "startup"), ("root", "status")),
        persistent_control_ids=("refresh", "stop", "logs"),
        contextual_control_ids=("open", "fallback", "submit", "cancel"),
        stable_region_ids=("root", "startup", "status"),
        validation_boundaries=("projection_only", "no_sealed_body"),
        rationale="Derives Cockpit and chat fallback structure from modeled UI state and controls.",
    )
