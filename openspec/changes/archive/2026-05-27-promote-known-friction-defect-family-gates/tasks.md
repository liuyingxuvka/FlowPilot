## 1. Model Upgrade

- [x] 1.1 Reuse the existing known-friction regression matrix as the owner for recurring FlowPilot dirty families.
- [x] 1.2 Add derived defect-family ids, recurrence/high-risk metadata, authority boundaries, and required gate markers to every known-friction row.
- [x] 1.3 Build FlowGuard `DefectFamilyGatePlan` and `RiskEvidenceLedgerPlan` objects from the known-friction rows.

## 2. Known-Bad Coverage

- [x] 2.1 Add known-bad cases for missing family promotion, progress-only proof, stale proof, and internal-only proof.
- [x] 2.2 Extend tests so defect-family gates must pass for all accepted rows and known-bad family evidence must fail.

## 3. Documentation And Validation

- [x] 3.1 Update defect-governance guidance to explain when a repeated FlowPilot bug becomes a higher-level defect family.
- [x] 3.2 Run focused known-friction tests, the known-friction matrix script, model-test alignment checks, and OpenSpec strict validation.
- [x] 3.3 Preserve peer-agent test-tier changes and avoid touching their files.
