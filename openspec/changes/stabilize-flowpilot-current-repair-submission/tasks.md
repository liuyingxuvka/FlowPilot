## 1. Preflight And Scope Control

- [x] 1.1 Run FlowGuard package/version/project audit and record the current new-only boundary.
- [x] 1.2 Inspect existing PM repair packet, open-packet, role handoff, PM prompt-card, and focused test surfaces for conflicting short-shape guidance.
- [x] 1.3 Confirm the implementation does not introduce new packet kinds, ledgers, gates, fallback parsers, aliases, or missing-field defaults.

## 2. Runtime Submission Checklist Projection

- [x] 2.1 Add a role-hidden `submission_checklist` to `open-packet` output, derived from the current sealed packet body.
- [x] 2.2 Include current required fields, conditional required fields, forbidden fields, result skeleton, authorized input material count, and required-read ids in the checklist when present.
- [x] 2.3 Update role handoff text to tell the addressed role to use the `open-packet` checklist or packet `minimal_valid_shape` before `submit-result`.

## 3. PM Repair Prompt And Packet Guidance

- [x] 3.1 Replace fixed `decision`/`reason` PM repair examples with guidance that uses the current packet `minimal_valid_shape`.
- [x] 3.2 Move the `repair_evidence_obligations` to `repair_obligation_disposition` rule into prominent PM role and PM repair phase pre-submit guidance.
- [x] 3.3 Ensure prompt/card wording keeps authorized evidence access scoped to `open-packet` delivered materials.

## 4. Focused Test Alignment

- [x] 4.1 Add or update test helpers that complete PM repair results from the actual PM repair packet skeleton.
- [x] 4.2 Update focused positive PM repair tests to include `repair_obligation_disposition` whenever obligations exist.
- [x] 4.3 Keep reason-only PM repair as negative evidence and verify reissue/block behavior remains strict.

## 5. FlowGuard And Model-Test Validation

- [x] 5.1 Run focused high-standard control-flow tests that cover PM repair decisions.
- [x] 5.2 Run lifecycle, model-test alignment, model mesh, and blocker repair information-flow checks for the changed repair path.
- [x] 5.3 Triage any failed validation as implementation defect, stale evidence, model-test mismatch, or broader route gap before continuing.

## 6. Install, Topology, And Sync

- [x] 6.1 Rebuild and check FlowGuard project topology after prompt/runtime/test changes.
- [x] 6.2 Sync repository-owned FlowPilot install artifacts to the local installed skill.
- [x] 6.3 Run local install sync audit and install self-check.
- [x] 6.4 Run repository install self-check and record any remaining scoped caveats.

## 7. Closure

- [x] 7.1 Update FlowGuard adoption notes with changed artifacts, commands, validation results, skipped checks, and remaining risks.
- [x] 7.2 Run OpenSpec status and keep the change ready for archive after implementation.
- [x] 7.3 Inspect final git diff without reverting unrelated peer-agent changes.
