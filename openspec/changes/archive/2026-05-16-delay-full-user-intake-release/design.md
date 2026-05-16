## Context

Current FlowPilot startup prepares a sealed `user_intake` packet from the
startup UI record, delivers PM startup cards, then releases the full
`user_intake` body to PM after the PM card bundle ACK. The reviewer startup
fact report and PM startup activation happen later. The Controller body
boundary is preserved, but PM can read full task details before the formal
startup gate is open. A later partial repair delayed the release, but still
used Router-only release evidence instead of the standard Controller relay
signature.

The desired boundary is stricter: startup activation proves the run is allowed
to begin formal work. PM should only need startup answers and current-run
evidence to open that gate. Full task understanding belongs immediately after
startup activation.

## Goals / Non-Goals

**Goals:**

- Keep full user task text sealed until PM startup activation is approved.
- Preserve early startup metadata so PM and reviewer can validate startup
  facts without reading the full task body.
- Make full `user_intake` the first post-startup PM mail item, delivered by
  the standard Controller relay.
- Preserve the existing formal-mail rule: PM opens the packet only after a
  Controller relay signature.
- Add executable FlowGuard and runtime checks for the new boundary.
- Sync the local installed FlowPilot skill after repository changes.

**Non-Goals:**

- Do not change the three-question startup intake UI.
- Do not let Controller read, summarize, or execute user intake bodies.
- Do not run the heavyweight Meta and Capability model sweeps for this change.
- Do not publish, push, or release.

## Decisions

1. Gate full user intake on `startup_activation_approved`.

   `user_intake_ready` may still be written early as a sealed router-owned
   packet. `user_intake_delivered_to_pm` must not become true until PM has
   submitted a valid startup activation approval and Controller has relayed the
   packet. This preserves sealed preparation while moving PM task-body access
   to the post-startup boundary.

   Alternative considered: keep the current early PM startup intake and rely on
   PM instructions not to plan. Rejected because it depends on discipline
   instead of a state boundary.

2. Keep a startup authorization context before activation.

   Startup cards should reference the startup intake record, startup answers,
   run id, pointers, role/continuation/display evidence, hashes, and receipts.
   They must not require opening the full task body to decide startup
   activation.

   Alternative considered: block all PM contact until after reviewer startup
   fact review. Rejected because PM still owns startup activation and may need
   current-run metadata to make a valid startup decision.

3. Use focused FlowGuard coverage.

   Update the startup control model and prompt isolation model to reject early
   full user intake release and Router-only open authority. Run focused
   startup, prompt isolation, router runtime, packet runtime, and install
   checks. Record Meta and Capability as intentionally skipped by user
   direction because this change touches a narrower startup boundary.

   Alternative considered: run all heavy project sweeps. Rejected for this
   turn because the user explicitly asked to skip the two heaviest sweeps while
   other agents are working.

## Risks / Trade-offs

- Existing tests and helpers assume early `user_intake` delivery -> Update the
  helpers so startup activation completes first, then releases PM user intake.
- Startup activation cards may still mention `user_request_path` -> Keep paths
  to sealed metadata and startup records, but remove any instruction that PM
  must open the full body before activation.
- Release finalizer idempotency may hide stale early-release behavior -> Add a
  regression that finalizer does not release without
  `startup_activation_approved`, and after activation the normal
  `check_packet_ledger` / `deliver_mail` path performs the Controller relay.
- Installed skill can drift from repo changes -> Run the local sync/check path
  after focused tests pass.

## Migration Plan

1. Add FlowGuard hazards and focused checks for early PM full-intake release.
2. Update Router release logic so activation exposes standard Controller mail
   delivery instead of Router-only PM open authority.
3. Update PM startup cards to use startup authorization context before
   activation and reserve full task intake for post-startup.
4. Update runtime tests and helpers for the new sequence.
5. Run focused checks, sync local installed skill, and run install checks.
