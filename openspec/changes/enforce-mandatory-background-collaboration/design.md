## Context

Current FlowPilot runtime already has the new role-assignment path:
`resolve-role-assignment` decides whether to reuse or create an addressable role
surface, and `lease-agent` commits the runtime-authorized assignment. That path
is current. Fixed startup role prewarming, heartbeat resume automation, and
single-agent role continuity are not current runtime authority.

The existing UI field `background_collaboration_authorized` records an explicit
startup acknowledgement, but current code and models do not yet consistently
turn a disabled acknowledgement or missing host capability into a terminal
startup/recovery stop. Some tests and models still treat `single-agent` as a
valid positive route.

## Decisions

### Decision: Background collaboration is mandatory

FlowPilot must attempt to use a host-supported isolated addressable background
or parallel role surface for runtime-requested responsibilities. The runtime
must not silently continue as a single-agent route when that capability is
disabled, unavailable, or unverified.

### Decision: The UI control is an acknowledgement, not a mode selector

The startup UI may keep a visible control so the user sees the background role
requirement, but its off state cannot authorize a different product mode. If
the user disables it, the result is a structured FlowPilot stop.

### Decision: Capability failure stops instead of falling back

Startup, manual resume rehydration, and role recovery must reject payloads that
lack current background-role capability evidence. Rejection should name the
single owner, current run, current action, missing field or disabled
acknowledgement, and required repair: enable or provide a current host-supported
background role surface.

### Decision: Startup has only Runtime mechanical entry before PM work

Startup no longer has a Reviewer startup fact gate or PM startup activation
gate. Runtime/Router creates the current run, seals startup input, writes the
startup mechanical audit, writes display status, audits current run identity,
and records any structured stop or blocker. When those mechanical conditions
pass, Router delivers the sealed `user_intake` packet to PM for the first
material/intake decision. Reviewer does not re-prove fields, hashes, paths, or
packet ledgers; Reviewer judges quality only after Runtime has accepted
mechanics.

### Decision: Old paths are negative-only

Legacy `runtime_role_assistances=single-agent`, fixed `start_role_slots`,
`create_heartbeat_automation`, `heartbeat_or_manual_resume_requested`, and
`host_records_heartbeat_binding` may remain only in archived history or focused
negative tests. They must not be accepted as normal runtime paths.

### Decision: Do not keyword-delete uncertain current semantics

Fields whose names still contain old words but carry current host-capability
semantics should be classified first. If retained, they should be renamed in
one current direction with tests, not accepted alongside old aliases.

## Implementation Notes

- Prefer a single helper or validation point for "background role capability is
  required" where the router already has startup answers and action context.
- Keep `resolve-role-assignment` / `lease-agent` and current packet ownership
  untouched except for capability gating.
- Do not add compatibility translation from old startup answers to the new
  acknowledgement field.
- For fake-AI tests, assert that bad packages are rejected before protected run
  state advances.

## Risks

- Historical tests may still pass while exercising old paths. Mitigation: add
  negative tests first and update model/test names so current coverage cannot
  hide behind legacy terms.
- A valid current capability field may look old by name. Mitigation: classify
  rename-or-retain decisions in the old/new difference audit before deletion.
