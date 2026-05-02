# Example Task

Build a retry-safe background job processor.

Acceptance criteria:

- A job is not marked complete until its side effect is recorded.
- Replaying the same job does not duplicate the side effect.
- Failed jobs can retry without losing the original job id.
- Completion requires a FlowGuard model check and a focused runtime test.

This is intentionally small, but it exercises the FlowPilot gates that matter:
contract freeze, route check, task-local model, chunk verification, checkpoint,
and final report.
