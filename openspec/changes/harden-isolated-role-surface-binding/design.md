## Context

FlowPilot already has the current runtime path for role assignment:
`dispatch-current-role` resolves the requested responsibility before any new
surface is opened, and the runtime records `reuse_existing_role`,
`create_new_role`, or `blocked`. Completed design work also established that
role surfaces are host-neutral: a host may provide a background agent, separate
thread, new conversation, worker, independent AI session, or equivalent
isolated addressable AI execution surface.

The observed gap is not the runtime decision. The gap is AI-facing execution
language: a Controller can still read "create or attach" as permission to open
a fresh host surface for a reuse assignment, or to continue in the foreground
when a required surface is unavailable.

## Goals / Non-Goals

**Goals:**

- Preserve the runtime as the sole owner of reuse, replacement, and blocker
  decisions.
- Keep the host-neutral wording from the existing role-surface design.
- Make Controller execution mechanical for each runtime disposition.
- Make foreground role work an explicit prompt/protocol violation.
- Add focused validation so the installed skill cannot drift back to vague
  "background agent only" or single-agent fallback wording.

**Non-Goals:**

- Do not add a new role-assignment algorithm.
- Do not add compatibility aliases, fallback fields, or historical role
  promotion.
- Do not require Codex-specific subagents, threads, or background-agent APIs.
- Do not allow Controller to choose reuse or replacement independently of the
  runtime.

## Decisions

### Decision: Define the AI-facing surface contract in portable terms

Use "host-supported isolated addressable AI execution surface" in
Controller-facing text, with examples only when useful. The required qualities
are isolation from the Controller foreground, addressability for later
handoff, and host support. Product-specific mechanisms remain implementation
examples, not protocol requirements.

Alternative considered: require "background agent" everywhere. Rejected because
the existing host-neutral design intentionally supports separate conversations,
threads, workers, and independent AI sessions in non-Codex hosts.

### Decision: Make dispatch behavior disposition-driven

The prompt must name what the Controller does for each runtime disposition:

- `reuse_existing_role`: deliver the handoff to the existing runtime-named
  `effective_agent_id` surface; do not open a fresh surface.
- `create_new_role`: open a new isolated addressable surface only after the
  runtime asks for one, then retry the runtime command with that surface id.
- `blocked`: follow the blocker or recovery path; do not open, reuse, or
  perform role work in the foreground.

Alternative considered: instruct Controller to "prefer reuse". Rejected because
preference language gives Controller too much discretion; the runtime decision
is already authoritative.

### Decision: Treat unreachable reuse surfaces as recovery evidence, not
create-new permission

If the runtime returns reuse but the host cannot address the existing surface
after resume, compaction, or host limitation, Controller must record or surface
the problem through the current blocker/recovery path. Replacement is allowed
only when the runtime or recovery path authorizes it.

Alternative considered: allow Controller to start a new same-role surface and
seed it from memory. Rejected because that recreates a fallback replacement
path outside runtime ownership.

### Decision: Validate prompt surfaces directly

Add focused checks that inspect the active skill and protocol text for the
runtime-disposition table, host-neutral execution-surface wording, foreground
role-work prohibition, and forbidden drift such as Codex-only wording or
fresh-surface creation during reuse.

## Risks / Trade-offs

- [Risk] More explicit prompt text may feel repetitive.
  -> Mitigation: place the hard rules only at dispatch and packet-work
  boundaries where weak agents actually decide what to do.
- [Risk] "AI execution surface" could become too abstract.
  -> Mitigation: keep the three operational adjectives: host-supported,
  isolated, and addressable, and include examples without making them
  exclusive.
- [Risk] Validation could overfit exact prose.
  -> Mitigation: check for a small set of contract phrases and forbidden drift
  patterns rather than entire paragraphs.
