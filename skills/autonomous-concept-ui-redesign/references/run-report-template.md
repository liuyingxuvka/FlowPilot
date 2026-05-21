# Run Report Template

Use this shape for final reporting. Keep the actual user-facing answer concise,
but preserve these facts in the run notes or final summary.

```text
Autonomous Concept UI Redesign Report

Route:
- route_type:
- target_surface:
- user_task:
- assumptions:

Concept:
- concept_mode: used | skipped
- concept_source:
- functional_framing:
- display_element_review:
- information_architecture:
- flowguard_gate: triggered | skipped | blocked
- flowguard_skip_reason:
- flowguard_model_id:
- flowguard_structure_contract:
- flowguard_journey_coverage:
- flowguard_text_hierarchy_blueprint:
- flowguard_implementation_validation:
- flowguard_revalidation:
- duplicate_information_decisions:
- duplicate_control_decisions:
- unresolved_model_states:
- design_language:
- candidate_search_rounds:
- concept_diagnosis_summary:
- concept_refinement_rounds:
- candidate_scoring_summary:
- selected_target:
- final_concept_version:
- final_concept_evaluation_package:
- color_background_foreground_contract:
- selected_concept_three_layer_review:
- concept_readiness:
- accepted_visual_cues:
- rejected_or_simplified_cues:

Implementation:
- implementation_skill:
- files_changed:
- design_system_followed:
- preserved_behavior:

App Icon:
- applicable: yes | no
- selected_icon_source:
- exported_icon_assets:
- runtime_window_icon:
- taskbar_or_dock_icon:
- tray_or_menu_bar_icon:
- package_or_shortcut_icon:
- in_ui_mark_consistency:
- host_runtime_icon_risk:
- result: pass | partial | blocked

Iteration:
- iteration_skill:
- rounds_run:
- concept_evaluation_reused:
- color_background_foreground_checks:
- issues_fixed:
- stopped_reason:

Deviation Review:
- reviewer_skill:
- baseline_type:
- major_deviations:
- visual_style_alignment:
- functional_structure_fit:
- flowguard_contract_alignment:
- presentation_readability_interaction:
- accepted_deviations:
- fixed_deviations:

Geometry QA:
- sizes_checked:
- native_desktop_capture:
- flowguard_modeled_states_checked:
- flowguard_stable_regions_checked:
- flowguard_overlay_and_control_ownership_checked:
- text_overflow:
- overlap:
- horizontal_scroll:
- fixed_overlay_coverage:
- popup_bounds:
- high_dpi_notes:

Evidence:
- screenshots:
- post_interaction_evidence:
- functional_walkthrough:
- geometry_reports:
- screenshot_trust_notes:
- content_localization_checks:
- asset_motion_depth_checks:
- skipped_states:

Integrated Acceptance:
- ledger_rows:
  - gate: <flowguard_ui_structure | concept_readiness | frontend_implementation | design_iteration | deviation_review | functional_walkthrough | geometry_screenshot_qa | content_localization | motion_assets | app_icon_realization>
    triggered: yes | no
    status: pass | accepted_deviation | skipped_with_reason | partial | blocked
    evidence:
    evidence_freshness: current | stale | not_run | not_applicable
    evidence_version_or_timestamp:
    skip_or_deviation_reason:
    final_verdict_impact: none | downgrade_to_partial | downgrade_to_blocked
- child_skill_standards_referenced:
- accepted_deviations:
- justified_skips:
- stale_or_missing_evidence:
- final_verdict_downgrades:

Final:
- verdict: pass | partial | blocked
- remaining_risks:
- next_action_if_any:
```
