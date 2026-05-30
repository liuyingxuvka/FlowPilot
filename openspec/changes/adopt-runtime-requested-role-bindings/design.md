## Context

The new FlowPilot formal entrypoint uses runtime actions such as `lease_agent`,
`wait_for_ack`, and `wait_for_result`. That runtime contract is already
on-demand: the Controller binds the specific responsibility named by the
current action and records the addressable host id. Older prompt and model
surfaces still carry historical role-topology wording as if it were an active
startup requirement.

The user wants the active prompt language to be natural and future-proof. It
should not explain host internals or earlier topology migrations. Those are
implementation details of the host-supported role mechanism.

## Goals / Non-Goals

**Goals:**

- Make active prompts say only the current rule: bind the role requested by the
  runtime and wait for runtime-visible ACK/result evidence.
- Use neutral language such as requested role, role binding, addressable id,
  and host-supported role mechanism.
- Remove active fixed-count role language from startup, resume, review, PM, and
  Controller prompts.
- Align public docs, reference docs, FlowGuard models, and tests with the
  runtime-requested binding contract.
- Keep the existing evidence safety properties: current-run identity, no stale
  role id reuse, ACK is not completion, Controller cannot read sealed bodies,
  and results must return through runtime paths.

**Non-Goals:**

- Do not explain Codex thread mechanics in active prompts.
- Do not introduce a new role topology.
- Do not weaken PM/reviewer/officer authority, runtime lease ownership, sealed
  body isolation, or final-preflight gates.
- Do not rewrite unrelated FlowPilot protocol areas.

## Decisions

1. **Use positive current-rule wording.** Active prompts will state that the
   Controller handles the current runtime-requested role only.

2. **Treat host mechanism as abstract.** Prompt text will refer to a
   host-supported role mechanism and an addressable role binding. This covers
   current and future host mechanisms without naming them in active
   instructions.

3. **Keep evidence boundaries explicit.** The abstraction stops at the
   mechanism boundary. The runtime still requires a recorded id, current-run
   association, ACK, formal result submission, and sealed-body separation.

4. **Update executable models with behavior names, not historical labels.**
   FlowGuard models and tests should express requested-role readiness and
   runtime-required binding coverage. Historical topology names remain valid
   only in archived tests or explicit known-bad fixtures.

## Risks / Trade-offs

- **Risk:** removing historical topology language could accidentally weaken role
  recovery.  
  **Mitigation:** tests must assert that every runtime-required role binding is
  current, addressable, and recovered or blocked before dependent work resumes.

- **Risk:** abstract host wording may allow fake liveness claims.  
  **Mitigation:** keep evidence requirements concrete: addressable id,
  current-run provenance, ACK/result events, and host quality policy when a
  role binding is opened.

- **Risk:** broad model/test churn can stale existing generated result files.  
  **Mitigation:** run focused checks first, then regenerate touched result
  artifacts and rebuild/check topology before final claims.
