# Design

## PM Decision Boundary

`stop_for_user` means PM needs the user to decide project content or authority:
goal, scope, acceptance, waiver authority, cancellation, or another substantive
choice outside FlowPilot's control plane.

`break_glass` means PM has current-run evidence that the FlowPilot control plane
itself cannot form a legal normal next action: missing delivered material,
packet/result contract contradiction, event-authority contradiction, broken
return path, foreground duty contradiction, or another runtime routing defect.

## Runtime Boundary

The runtime will accept `break_glass` in the same PM decision families that
already expose a stop-for-user exit. When submitted, it records the PM decision
and leaves the affected blocker active as a control-plane concern. Router then
returns `control_plane_blocker` for Controller break-glass repair.

The runtime does not treat `break_glass` as:

- a passing gate;
- a waiver;
- a route mutation;
- a completed repair;
- permission to read sealed bodies;
- permission to bypass PM/Reviewer/FlowGuard authority.

## Prompt And Contract Boundary

Cards and packet bodies must explain both exits in the finite option list. PM
should not invent wording such as `glass_break`, `controller_repair`, or
`ask_user_about_runtime_bug`; the machine token is exactly `break_glass`.

## Coverage Boundary

Tests must prove three separate behaviors:

- `stop_for_user` still pauses for explicit user resume.
- `break_glass` routes to Controller control-plane duty without user wait.
- invalid or synonym decisions are still rejected by the current contract.

Model and Cartesian coverage must include fake AI response packages so this is
not only a hand-written unit case.
