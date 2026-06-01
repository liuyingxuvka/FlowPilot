## 1. Scope And Model Preflight

- [x] 1.1 Inventory current prompt, card, template, skill, and installed-skill surfaces that expose old FlowPilot prompt/control paths.
- [x] 1.2 Record FlowGuard route ownership and minimum revalidation plan for prompt-surface cleanup.

## 2. Prompt Surface Cleanup

- [x] 2.1 Remove old role-output return paths from shared prompt-policy fragments and current runtime cards.
- [x] 2.2 Rewrite current role and phase cards to reference only the `flowpilot_new.py` packet lifecycle.
- [x] 2.3 Remove or quarantine current-facing runtime-kit and template text that presents old Router/control-plane behavior as live authority.
- [x] 2.4 Update skill, handoff, topology-oriented docs, and OpenSpec text that describe old prompt/control paths as current authority.

## 3. Validation Hardening

- [x] 3.1 Add focused forbidden-surface validation for repository prompt/card/template/skill surfaces.
- [x] 3.2 Add installed-skill forbidden-surface validation after local install sync.
- [x] 3.3 Update existing prompt/card tests to expect current packet lifecycle authority and reject old submission paths.

## 4. Synchronization And Verification

- [x] 4.1 Rebuild/check project topology if prompt, test, or install ownership surfaces changed.
- [x] 4.2 Sync the local installed FlowPilot skill from repository-owned source.
- [x] 4.3 Run focused prompt/install/runtime validation and start heavyweight FlowGuard regressions using the background artifact contract.
- [x] 4.4 Inspect validation artifacts, fix failures, and rerun minimum required checks until current evidence passes.
- [x] 4.5 Commit the scoped local git result without staging unrelated peer-agent changes.
