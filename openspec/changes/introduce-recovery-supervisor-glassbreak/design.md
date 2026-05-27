## Context

The existing Controller break-glass model intentionally forbids sealed-body
reads, gate approval, route mutation, project work, publishing, deployment, and
secret handling. That remains the right default for ordinary Controller work.
The new requirement is not to make ordinary Controller stronger; it is to create
a separate emergency identity with explicit entry, evidence, body-access, and
exit rules.

## Goals / Non-Goals

**Goals:**

- Convert severe control-plane failures into mandatory recovery transactions.
- Track current and historical control-plane blockers in one family-aware
  ledger.
- Require FlowGuard same-family repair evidence before recovery closure.
- Allow scoped body access only as an audited Recovery Supervisor grant.
- Force Controller-core reinjection before normal FlowPilot work resumes.

**Non-Goals:**

- Do not change frozen acceptance contracts.
- Do not let ordinary Controller read sealed bodies.
- Do not let Recovery Supervisor approve route gates or terminal completion.
- Do not restart, stop, or resume live user runs as part of repository tests.
- Do not modify parallel role-recovery work unless a final integration conflict
  requires it.

## Design

### Identity State

The runtime identity sequence is:

1. `normal_controller`
2. `recovery_supervisor`
3. `controller_reinjecting`
4. `normal_controller`

The transition to `recovery_supervisor` opens a recovery transaction and marks
ordinary Controller progression as suspended. The transition back to
`normal_controller` requires a reinjection record that names the previous and
new Controller generations plus the Controller core hash or boundary proof.

### Recovery Transaction

Each recovery transaction records:

- trigger summary and failure kind;
- linked break-glass incident;
- blocking control-plane ids;
- defect-family ids;
- normal lanes checked;
- FlowGuard model/check obligations;
- whether scoped body access was requested;
- same-family repair proof;
- Controller reinjection proof.

### Control-Plane Blocker Ledger

The blocker ledger records each blocker with:

- blocker id;
- family id;
- status: `open`, `closed`, `regression`, `quarantined`, or `weak_evidence`;
- current-run/current-transaction status;
- source paths and hashes;
- whether body access is needed;
- linked recovery transaction;
- closure or quarantine notes.

Current open blockers must be repaired or explicitly quarantined before
recovery closure. Historical blockers are not reactivated by default; they feed
same-family regression obligations.

### Scoped Body Access

Recovery Supervisor may request body access only when:

- the recovery transaction is open;
- normal PM/Reviewer/Officer repair lanes are unavailable or contradictory;
- the body path is explicit;
- the justification states why metadata is insufficient;
- the grant is audited and later reviewed after role recovery.

The grant is recorded as Recovery Supervisor access, never normal Controller
access.

### Controller Reinjection

Recovery closure requires a reinjection record:

- previous Controller generation;
- next Controller generation;
- Controller core source/hash or boundary proof;
- proof commands/artifacts;
- confirmation that normal Controller restrictions are active again.

## Validation Plan

- Focused helper tests for ledger, transaction, body grant, and closure gates.
- FlowGuard recovery-supervisor model checks and hazard detections.
- Existing Controller break-glass tests.
- OpenSpec validation for this change.
- Router tier/background and heavy Meta/Capability checks after integration.
