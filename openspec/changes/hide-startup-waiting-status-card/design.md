## Context

The startup path currently has two separate user-visible displays before a
canonical PM route exists:

- `sync_display_plan` emits `FlowPilot Startup Status` with a single
  `Waiting for PM route` item.
- `write_display_surface_status` emits the startup `FlowPilot Route Sign`
  placeholder.

The first display is useful as controller/host-plan state, but it is not useful
as chat text because the startup banner already confirms FlowPilot activation
and the Route Sign placeholder already owns the visible route surface.

## Goals / Non-Goals

**Goals:**

- Keep the internal waiting state and `none_until_pm_display_plan` authority
  boundary.
- Make startup show only the banner plus the startup Route Sign before PM route
  activation.
- Preserve canonical route display behavior after `flow.json` is activated.
- Add model and test coverage so the waiting card does not reappear as
  user-visible chat output.

**Non-Goals:**

- Do not remove `display_plan.json` or the host visible plan projection.
- Do not let Controller invent route items before PM route approval.
- Do not change Cockpit rendering or PM route activation semantics.

## Decisions

- Treat startup waiting display-plan sync as an internal display sync when no
  canonical route is available. The action may still replace/clear host visible
  plan state, but it no longer requires a user-dialog display confirmation or
  emits `FlowPilot Startup Status`.
- Keep the startup Route Sign action as the only chat-visible startup route
  placeholder. This keeps the user-visible surface stable: banner for startup,
  Route Sign for route progress.
- Record an explicit internal-only reason on the waiting sync payload and
  visible-plan metadata. This preserves auditability without occupying the
  conversation.
- Update the route-display FlowGuard model with a state bit for the removed
  waiting card and a hazard case where it reappears.

## Risks / Trade-offs

- [Risk] A future maintainer could mistake the hidden waiting sync for missing
  display evidence. -> Mitigation: tests assert that startup waiting sync is
  internal-only while startup Route Sign still has a user-dialog display gate.
- [Risk] Removing the user dialog confirmation could weaken proof that startup
  was visible. -> Mitigation: startup Route Sign still records the user dialog
  display ledger entry and generated files alone still do not satisfy display.
- [Risk] Host visible plan might still need to clear stale plan text before PM
  route exists. -> Mitigation: keep `sync_display_plan` and `display_plan.json`
  write behavior; only the chat-facing card is hidden.
