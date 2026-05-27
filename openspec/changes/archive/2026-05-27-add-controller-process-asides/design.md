## Context

FlowPilot already has a strong formal handoff model: sealed packet bodies,
result bodies, role-output envelopes, card ACKs, Controller action ledgers, and
Router-owned waits. That protects authority boundaries, but it also makes
long-running work opaque. A role can be alive, retrying a runtime command, or
already submitted a formal output while Controller still has to infer that from
several ledgers.

The user wants a small, repeated, natural-language process channel between
Controller and each role. The channel must make roles less operationally
invisible without turning chat or envelope metadata into a second report body.

Relevant existing surfaces:

- packet `controller_status_packet.json`
- role-output controller status packets
- packet/result envelopes
- role core cards and phase/work cards
- `current_status_summary.json`
- Controller action ledger and wait/reminder flow

## Goals / Non-Goals

**Goals:**

- Let each role provide a short Controller-facing process aside on current work.
- Repeat aside guidance in work envelopes and packets so long tasks do not rely
  only on role core-card memory.
- Keep the aside natural-language and useful for operations: started, working,
  delayed, retrying, submitted, waiting, recovered, or mechanically blocked.
- Preserve formal authority: only sealed bodies, reports, decisions, and
  Router events carry formal content, evidence, approvals, and route movement.
- Keep Worker-to-Worker communication forbidden; Controller is the only
  recipient and possible relay for worker asides.

**Non-Goals:**

- Do not add free role-to-role chat.
- Do not let Router semantically inspect aside text.
- Do not make process asides required for every output.
- Do not let asides satisfy ACKs, output contracts, gate evidence, PM
  decisions, reviewer approvals, officer reports, or route mutation.
- Do not add an LLM-based content classifier or broad moderation layer.

## Decisions

### 1. Put the reminder in work surfaces, not only core cards

Role core cards remain the baseline rule, but packet identity boundaries,
result/role-output submission guidance, and generated controller-visible status
surfaces should repeat the aside rule. This keeps the behavior visible after a
long task has moved beyond startup cards.

Alternative considered: only update role core cards. Rejected because long
running roles often follow the most recent packet or runtime instruction.

### 2. Treat `controller_aside` as optional metadata

The aside should be a small optional object or text field carried alongside
packet/result/role-output metadata. It is visible to Controller, but it is not a
formal body field and does not change Router wait semantics.

The object should carry authority flags such as:

- `purpose: "process_note_only"`
- `not_formal_evidence: true`
- `does_not_authorize_progress: true`

These flags are for machine and prompt clarity, not semantic review.

### 3. Router preserves but does not interpret aside text

Router may persist and expose the aside to Controller, but it must not parse
the text for meaning, classify business content, approve it, reject it because
of its meaning, or use it to advance state. If an aside contains bad content,
that is a prompt/process misuse; it is not a Router decision source.

Alternative considered: Router content checking. Rejected because Controller
has already seen the aside when it is delivered, so late content checks create
false confidence and do not prevent exposure.

### 4. Controller may use asides only for operational awareness

Controller can use asides to avoid unnecessary liveness recovery and to explain
plain-language process status to the user. Controller cannot treat an aside as
formal evidence, a gate result, a report summary, a PM decision, or a reviewer
finding.

If Controller sees formal content inside an aside, it should ignore that content
for decision purposes and ask for the formal content to remain in the proper
body/envelope path.

### 5. Validation must prove non-authority, not text quality

FlowGuard and tests should cover structural failures:

- Aside satisfies a formal wait.
- Aside substitutes for a result body.
- Aside becomes reviewer/PM/officer evidence.
- Aside is routed from one worker to another.
- Controller user status exposes formal content from aside as a conclusion.
- Missing aside blocks otherwise valid formal work.

They should not try to prove every possible wording is safe.

## Risks / Trade-offs

- **Risk: Roles leak formal content in asides.** -> Mitigate with repeated
  envelope/work-packet guidance and Controller rules that prevent decision use.
- **Risk: Router starts relying on aside text.** -> Mitigate with FlowGuard
  invariants and tests that asides cannot satisfy waits or outputs.
- **Risk: Aside becomes too noisy.** -> Mitigate with optional use and short
  "one to three sentences" guidance.
- **Risk: Other AI work is active in nearby files.** -> Keep edits scoped,
  inspect dirty files before patching, and avoid unrelated refactors.
