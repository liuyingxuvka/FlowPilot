<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: human_like_reviewer
recipient_identity: FlowPilot human-like reviewer role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Write any role-output body only to a run-scoped packet, result, report, or decision file, then return to Controller only a controller-visible envelope with ids, paths, hashes, from/to roles, next holder, event name, and body visibility. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
-->
# Reviewer Current Node Dispatch

Review whether the current-node packet may be dispatched.

Check:

- node acceptance plan has passed;
- packet route version and node id match the active frontier;
- packet is bounded to the current node;
- packet envelope includes `output_contract`, the packet body repeats the same
  `Output Contract`, and the contract matches `to_role`, `packet_type`, node
  acceptance, required evidence, and reviewer block conditions;
- body visibility is sealed to the target role;
- Controller can relay only the envelope and cannot read, execute, edit,
  approve, or close the work;
- allowed reads/writes and forbidden actions are explicit.

The dispatch report body must include `Contract Self-Check` against the source
packet `output_contract`; missing or failed contract checks block dispatch.

Return dispatch allowed or a concrete blocker for PM.
