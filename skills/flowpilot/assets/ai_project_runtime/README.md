# AI Project Runtime

This directory contains the clean black-box runtime for the AI project
protocol. It is additive: the legacy FlowPilot router remains available as
reference material, but this runtime does not use old `.flowpilot` state,
fixed-role startup, or stale result artifacts as authority.

## Shape

- `runtime.py`: serializable ledger, dynamic leases, sealed packet helpers,
  FlowGuard work-order scheduling, independent review, final closure, and
  public console projection.
- `run_shell.py`: current-run authority files, startup-intake import, append-only
  event history, and materialized sealed envelope/body artifacts under
  `.flowpilot/runs/<run-id>/`.
- `cli.py`: small command-line harness for deterministic scenario checks and
  status rendering.

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
- FlowGuard work orders must name the modeled target before selecting a skill.
- Review must be independent and evidence-aware.
- Final completion must walk backward from the user goal to current route,
  accepted results, reviews, FlowGuard reports, and fresh validation evidence.

## Legacy Reuse

Allowed reference material: startup panel ideas, icons, envelope field names,
install scripts, and historical failure cases.

Forbidden authority: old runtime state, fixed six-agent topology, old chat
memory, stale validation artifacts, or compatibility paths that bypass the new
ledger.
