## Context

The current Router already classifies role-facing system-card dispatch as either `ack_only_prompt` or `output_bearing_work_package`. It also already has return-event ledgers, Controller passive wait rows, Router scheduler rows, external-event wait closure, JSON write-lock wait/retry handling, and dispatch recipient gating. The repair should strengthen those existing paths rather than add a new settlement lane.

## Goals / Non-Goals

**Goals:**

- Use only the existing two categories: ACK-only system cards and output-bearing work packages.
- Close stale ACK waits promptly when valid ACK evidence exists.
- Keep output-bearing work busy until its named report/result/decision event is recorded.
- Apply the rule to PM, workers, reviewers, and officers.
- Preserve current fresh-write-lock wait/retry behavior.

**Non-Goals:**

- Do not create a new card taxonomy.
- Do not treat ACK as semantic work completion.
- Do not add a parallel settlement pipeline.
- Do not run heavyweight Meta or Capability simulations in this pass.

## Decisions

- Extend existing Router reconciliation hooks instead of adding a new flow.
  Alternative rejected: a separate ACK settlement service, because the current Router already owns return ledger, Controller action row, scheduler row, and dispatch-gate reconciliation.
- Keep the dispatch gate as the enforcement point.
  Alternative rejected: prompt-only repair, because stale ledgers can still mislead the runtime even when prompts are correct.
- Treat output-bearing work completion as external-event evidence.
  Alternative rejected: using ACK status to infer completion, because `card_runtime` explicitly records ACK as mechanical proof only.
- Reuse the existing fresh JSON write-lock behavior.
  Alternative rejected: immediate corruption reporting while a writer is active, because the runtime already has `RouterLedgerWriteInProgress` wait/retry semantics.

## Risks / Trade-offs

- [Risk] Closing an ACK wait could accidentally free an output-bearing work package.
  -> Mitigation: dispatch gate must still consult pending expected output, packet holder, or role-work status after ACK wait reconciliation.
- [Risk] Stale rows can appear in Controller ledger summaries after individual action files were fixed.
  -> Mitigation: rebuild the Controller action ledger whenever reconciliation changes action row status.
- [Risk] Heavy models are skipped by request.
  -> Mitigation: run focused FlowGuard models and runtime tests, and record Meta/Capability as intentionally skipped.
