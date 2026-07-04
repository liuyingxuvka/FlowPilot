## Context

FlowPilot already has a current-contract rule: `.flowpilot/runs/<run-id>/`
contains the authoritative ledger, while `.flowpilot/current.json` and
`.flowpilot/index.json` are pointer/catalog metadata. The existing
`flowpilot_runtime_gateway.py` declares those files as Router JSON gateway
surfaces, and `flowpilot_router_io_json.py` already provides an atomic JSON
write helper with lock, replace, fsync, and readback verification.

The current new-run shell bypasses that helper and writes pointer files
directly. The read side correctly rejects invalid JSON and unsupported legacy
fields, but it has no current-contract recovery path for external pointer
corruption. This creates a hard failure even when the run ledger remains valid.

The current packet result runtime also enforces strict JSON object bodies later
in the packet-result path, but the public CLI accepts `--body` as a raw string.
That allows quoting failures to reach deeper runtime code with unclear
feedback.

## Goals / Non-Goals

**Goals:**
- Make pointer writes atomic and verified through the existing Router JSON
  ownership lane.
- Recover corrupt pointer/catalog files only when the target run can be proven
  from current valid evidence.
- Preserve the existing `current.json` and `index.json` shapes; no new business
  fields are added to either file.
- Reject pseudo-JSON result bodies at the CLI boundary with clear feedback.
- Prefer `--body-file` in prompts/cards to avoid PowerShell quoting failures.
- Add FlowGuard Cartesian/model coverage for pointer corruption and body-entry
  fault families.

**Non-Goals:**
- No newest-run fallback.
- No legacy pointer field compatibility.
- No automatic conversion from a JSON string into a JSON object.
- No second pointer ledger, repair ledger, or alternate runtime state family.
- No public release, remote push, or GitHub publication.

## Decisions

### Decision: Reuse the existing Router JSON gateway for pointer writes

Current/index writes should use the same persistence semantics as other
Router-owned JSON surfaces: temp file, flush, fsync, atomic replace, readback
verification, and write-lock settlement. This keeps ownership under the
declared `flowpilot_current_pointer` critical surface instead of introducing a
new storage path.

Alternative considered: add an independent pointer transaction ledger. Rejected
because it would make pointer state heavier and risk creating a second
authority beside the run ledger.

### Decision: Keep pointer file shapes unchanged

Normal recovery rewrites `current.json` and `index.json` using the same fields
already present in the current runtime shape. Corruption backup paths and
recovery reasons stay in command output, existing logs, or diagnostic backup
filenames. They are not persisted as new pointer fields.

Alternative considered: add `recovered_at`, `rebuild_source`, or
`recovery_audit_ref` fields. Rejected per the user's request and the
current-contract repair discipline; these fields could later be mistaken for
runtime authority.

### Decision: Recovery is ambiguity-aware

Recovery is allowed only when one target can be proven:
- current corrupt plus valid index entry;
- index corrupt plus valid current pointer;
- both corrupt plus exactly one valid run candidate.

When multiple valid run candidates exist, FlowPilot returns a structured
ambiguous recovery error and requires an explicit run target or repair command.
It never selects the newest run by timestamp.

### Decision: CLI entry validates body shape before mutation

`submit-result` accepts either `--body` or `--body-file`, exactly one. The
resolved payload must parse as a top-level JSON object before the run ledger is
loaded and before packet result mutation. Non-object JSON, malformed JSON,
empty input, and unreadable files are rejected with payload kind and a safe
prefix/suffix preview.

Alternative considered: allow JSON strings that contain object text and unwrap
them. Rejected because this would normalize a bad caller path and preserve the
PowerShell quoting defect as a compatibility surface.

### Decision: Cartesian coverage is added to existing models

Pointer corruption and body-entry faults are added to existing
control-plane/current-contract/integration Cartesian coverage and consumed by
ContractExhaustionMesh, TestMesh, and Model-Test Alignment. This avoids a
parallel test universe and keeps full coverage claims tied to existing parent
gates.

## Risks / Trade-offs

- [Risk] Pointer recovery could pick the wrong run in a parallel-run project.
  -> Mitigation: recover only from unambiguous evidence; ambiguous candidates
  return a blocker instead of selecting newest.
- [Risk] Extra recovery evidence could become a new authority surface.
  -> Mitigation: no new pointer fields; corrupt backups are diagnostic only.
- [Risk] `--body-file` could be treated as a new result contract.
  -> Mitigation: it is only an input transport; the packet result contract and
  strict JSON object body remain unchanged.
- [Risk] Prompt/card changes can stale installed skill evidence.
  -> Mitigation: run card coverage, install sync, local install audit, install
  check, and topology refresh after implementation.
- [Risk] Broad regressions are slow under a shared workspace.
  -> Mitigation: use focused tests first, background logs for long FlowGuard
  checks, and final artifact inspection before claiming pass.
