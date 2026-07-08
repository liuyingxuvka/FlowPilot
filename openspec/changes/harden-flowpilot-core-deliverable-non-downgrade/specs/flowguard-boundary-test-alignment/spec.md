## ADDED Requirements

### Requirement: Non-Downgrade Obligations Bind To Current Tests
FlowPilot model-test alignment SHALL bind core-deliverable non-downgrade obligations to current prompt/card checks, fake-AI profile checks, synthetic replay checks, FlowGuard model checks, and install synchronization checks before claiming the change complete.

#### Scenario: Alignment includes prompt and replay evidence
- **WHEN** the model-test alignment runner inspects non-downgrade obligations
- **THEN** it SHALL find evidence rows for prompt-card instruction coverage, fake-AI profile coverage, synthetic agent replay or coverage matrix rows, FlowGuard model obligations, and install/source-fresh validation.

#### Scenario: Missing evidence blocks broad claim
- **WHEN** a non-downgrade obligation lacks a current evidence row or is backed only by stale, skipped, progress-only, or unrelated tests
- **THEN** model-test alignment SHALL report the gap instead of allowing a broad completion claim.
