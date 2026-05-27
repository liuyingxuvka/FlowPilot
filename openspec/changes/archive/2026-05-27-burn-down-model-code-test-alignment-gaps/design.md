## Context

The previous diagnostic pass made FlowPilot's full model-code-test inventory
actionable: every finding now has severity, owner, release relevance, repair
type, and a deduplicated summary. The current result still reports hundreds of
gaps. Many are accounting gaps rather than immediate runtime failures, but they
still mean the model architecture, owner code, and test evidence are not yet
bound tightly enough to claim full external-contract coverage.

The repository is under active multi-agent maintenance. This pass must reduce
the highest-value gaps while preserving public FlowPilot behavior, avoiding
unrelated broad formatting, and not claiming deferred structure work as done.

## Goals / Non-Goals

**Goals:**

- Reduce high-priority release/validation gate gaps by adding stable
  external-contract evidence rather than only internal helper tests.
- Add model bindings for selected code surfaces that are already intentional
  owner modules or public entrypoints.
- Classify truly extra code separately from code that is missing model binding.
- Improve diagnostic accountability for model-check runners and test-tier
  command surfaces through aggregate, fast contract tests.
- Keep generated diagnostic JSON, docs, install sync, FlowGuard adoption
  evidence, and local git state synchronized.

**Non-Goals:**

- Do not publish to GitHub, tag a release, or change remote release state.
- Do not force all 432 current findings to zero in one unsafe pass if doing so
  would require broad architectural rewrites or collide with peer agents.
- Do not rewrite public FlowPilot protocols or route semantics unless a
  concrete model/test/code mismatch exposes a defect.
- Do not count progress-only, stale, skipped, or local-only evidence as full
  validation proof.

## Decisions

1. **Burn down by release relevance and repair type.** The pass prioritizes
   `release_gate` and `validation_gate` findings, especially missing external
   contract evidence, before lower-risk `extra_code` classifications.

2. **Use aggregate contract tests where the surface is broad.** Dozens of
   model-check runner scripts can be validated through import/argument/output
   contract tests instead of one bespoke test per file, as long as the
   aggregate asserts stable external behavior and the diagnostic can recognize
   the evidence.

3. **Separate model binding from structure splitting.** If a module is an
   intentional owner module, add model binding. If it contains multiple
   responsibilities, keep or add a structure-split repair item. Do not perform
   a wide split unless it is clearly isolated.

4. **Keep diagnostic truth conservative.** A covered surface must have model
   binding and external evidence. Internal-only tests remain visible until they
   are upgraded. Release URL checks skipped by CLI flags remain local-only.

5. **Use background agents for analysis, not overlapping edits.** Explorers can
   classify missing model/test/code clusters in parallel. Main-thread edits
   integrate only the scopes that are safe and verified.

## Risks / Trade-offs

- [Risk] Aggregate tests could become shallow and hide per-runner defects.
  Mitigation: assert concrete CLI/import/JSON contract behavior and keep
  per-runner names in diagnostic evidence mapping.
- [Risk] Diagnostic counts could improve by reclassification rather than real
  coverage.
  Mitigation: tests must prove evidence classification, and docs must report
  remaining residual gaps honestly.
- [Risk] Structure split work may collide with peer agents.
  Mitigation: split only isolated surfaces; otherwise record owner, reason,
  and next action as deferred.
- [Risk] Background validation may leave stale artifacts.
  Mitigation: inspect final meta and exit artifacts with the classifier before
  counting evidence.
