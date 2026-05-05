<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Return only the decisions, reviews, reports, evidence, blockers, or handoff records that this recipient role is authorized to produce through the current FlowPilot route or packet path.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
-->
# PM Phase Map

FlowPilot proceeds through these phases:

1. `startup_intake`
2. `material_scan`
3. `material_absorb_or_research`
4. `research_package` when material is insufficient
5. `research_absorb_or_mutate` when research was required
6. `material_understanding`
7. `product_architecture`
8. `root_contract`
9. `route_skeleton`
10. `current_node_loop`
11. `review_repair`
12. `final_ledger`
13. `closure`

At each phase, act only from the current phase card, current event cards, and
reviewed mail. If the needed material is missing, request a bounded packet.
If the route no longer fits reviewed facts, request route mutation.
