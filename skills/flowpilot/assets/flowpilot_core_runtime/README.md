# FlowPilot Core Runtime

This directory contains the current FlowPilot core runtime and protocol
support. It uses only the current run ledger, sealed packets, accepted role
outputs, FlowGuard evidence, and fresh validation artifacts as authority.

## Shape

- `runtime.py`: serializable ledger, dynamic leases, sealed packet helpers,
  symmetric role-packet scheduling, FlowGuard work-order recording,
  independent review, final closure, and public console projection.
- `run_shell.py`: current-run authority files, startup-intake import, append-only
  event history, and materialized sealed envelope/body artifacts under
  `.flowpilot/runs/<run-id>/`.
- `cli.py`: small command-line harness for deterministic scenario checks and
  status rendering.
- `../flowpilot_new.py`: formal new FlowPilot entrypoint that reuses the native
  startup intake UI, then gives authority to the new current-run ledger.

## Rules

- The ledger is the truth.
- `.flowpilot/current.json` points to the current run, but the run ledger is the
  authority.
- ACK and progress are liveness only.
- Closed, expired, or superseded leases cannot submit authoritative output.
- Packet envelopes are public routing metadata; packet bodies stay sealed from
  the public console.
- Startup intake enters the runtime only as a confirmed sealed receipt/body hash
  copied into the current run.
- Formal startup enters through the native startup UI. Headless startup output
  is rehearsal evidence only and cannot prove a formal user launch.
- FlowGuard work orders must name the modeled target before selecting a skill.
- FlowGuard, review, validation, and closure are formal role packets, not
  side-command shortcuts. Each role must receive a packet, ACK it, and submit a
  sealed result before its ledger side effect is recorded.
- Review must be independent and evidence-aware.
- Final completion must walk backward from the user goal to current route,
  accepted results, reviews, FlowGuard reports, and fresh validation evidence.

## Authority Boundary

Reference material may inform implementation, including startup panel ideas,
icons, envelope field names, install scripts, and known failure cases.

Non-authoritative inputs include prior runtime state, prior role topology,
chat memory, stale validation artifacts, and paths that bypass the current
ledger.
