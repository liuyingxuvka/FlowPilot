## Design

### Classification

This change keeps the new black-box FlowPilot runtime as the authority. It does
not restore legacy Router as the active execution path. Legacy mechanisms are
used only as design inspiration where they had clear mechanical safeguards:
metadata-only controller visibility, compact status output, explicit liveness
proof before lease action, and terminal status pointer updates.

### Health Closure

Packet reassignment currently overwrites `assigned_lease_id` and leaves older
active leases untouched. The repair is to supersede older active leases for the
same packet when a new lease is assigned. Final preflight then performs an
independent health check: no accepted packet may have active leases other than
the accepted producer lease, and no accepted packet may point to a stale active
replacement.

### Body-Free Controller Projection

The ledger may continue to store sealed bodies as durable run-local state, but
controller status and recovery projections must not serialize those fields by
default. Add a redacted projection helper for public/controller surfaces and
use it from status output. Role packet opening and terminal-summary review
remain explicit exceptions. This is intentionally a soft reading boundary for
review roles: reviewer/PM body visibility through an authorized review path is
not an automatic failure. The hard boundary is command contamination or
authority confusion: one role must not execute another role's body as its own
instruction, submit on another role's behalf, or leak sealed text through
controller/default projections.

### Actionable Recovery Duty

`recover_or_reissue` must stop being a vague label. When the guard can identify
a packet and responsibility, the foreground duty includes a concrete
`recommended_command` payload with `command`, `packet_id`, `responsibility`,
`host_kind`, and stale lease ids to repair or supersede. Controller still
executes the command through the normal CLI, but the runtime names the action.

### Node Context Package Contract

The accepted contract remains top-level `node_context_package`. The runtime
must not normalize `node_acceptance_plan.node_context_package` or any other
nested/legacy shape into the current contract. Missing, nested, or unsupported
shapes block the packet result and require the PM to resubmit a current
structured result.

### Stable Evidence Summary Finalization

Evidence summaries are treated as manifest artifacts. The finalizer excludes
`evidence_summary.md` and `evidence_summary.json` from their own `evidence_files`
set and writes the JSON manifest after all referenced files exist. Existing
role-authored summaries can still be reviewed, but runtime-generated summaries
must be stable by construction.

### Status Pointer and Compact Output

When final preflight allows terminal return, current-run pointer refresh derives
status from closure and terminal permission rather than only from
`ledger.lifecycle.state`. New CLI/status output defaults to the body-free,
compact projection and requires an explicit full/debug option for the complete
ledger.

### Validation

Focused unit tests cover each defect family, including negative coverage for
legacy/nested payload shapes. FlowGuard evidence is provided through the focused
core-runtime runner and the existing control-plane duty model, then broader
router tiers, install checks, and topology checks provide freshness confidence.
