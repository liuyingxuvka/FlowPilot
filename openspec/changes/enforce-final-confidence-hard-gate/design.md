## Context

FlowGuard and FlowPilot already contain the core pieces needed for strict confidence control: model checks, live-run audits, defect-family gates, Risk Evidence Ledger helpers, claim-chain statuses, TestMesh rules, and background artifact contracts. The current failure mode is not absence of those mechanisms; it is that agents can still quote a passing subcheck while bypassing or not consuming the final evidence boundary.

The design therefore adds a small aggregation layer rather than another model framework. The layer reads or runs the existing evidence producers and fails closed when any required evidence is red, stale, skipped, scoped, progress-only, or incomplete.

## Goals / Non-Goals

**Goals:**
- Provide one named final confidence gate for FlowPilot.
- Make live-run audit failure or skipped live audit block broad confidence.
- Make `full_coverage_ok=false` block broad confidence even when model-test alignment itself is otherwise green.
- Consume known-friction defect-family/Risk Evidence Ledger decisions and block if they are not full/current/external.
- Expose the gate in test-tier planning so it is discoverable and cannot be replaced by a local subcheck summary.
- Keep changes isolated from peer-owned runtime repairs.

**Non-Goals:**
- No router semantic rewrite in this change.
- No cleanup of existing `.flowpilot` runs.
- No remote GitHub push or release publication.
- No claim that finite evidence proves arbitrary future AI semantic quality.

## Decisions

1. Add a dedicated final confidence check script.

   The script will aggregate evidence from existing producers instead of embedding their logic. This keeps the total gate reviewable and avoids duplicating FlowGuard model semantics.

2. Fail closed on missing or skipped required evidence.

   Missing files, skipped live audit, stale/progress-only proof, `ok=false`, scoped ledger confidence, or `full_coverage_ok=false` all produce a `blocked` decision. This is stricter than ordinary diagnostics because the command is explicitly for final confidence.

3. Keep live audit mandatory for the final gate.

   Existing model checks may keep `--skip-live-audit` for narrow abstract-model validation, but the final confidence gate will not expose a skip-live option. Current live audit evidence is required before a broad confidence claim.

4. Add test-tier exposure without making routine fast validation equivalent to final confidence.

   A named `final-confidence` tier makes the command explicit. Routine tiers may still run focused checks, but a completion/release/no-known-bug claim must run the final gate or report that the final gate is not run.

## Risks / Trade-offs

- Current local live-run state may fail the final gate → That is intended; the command should block broad confidence and report the exact live finding.
- The gate can become another broad script → Keep it as an aggregator with small classification helpers and focused tests.
- Parallel AI may be changing runtime files → This change avoids runtime ownership files and verifies without reverting peer edits.
- Long parent regressions can take time → Use the repository background artifact contract and treat progress as liveness only.
