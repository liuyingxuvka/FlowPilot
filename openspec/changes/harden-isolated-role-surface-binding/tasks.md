## 1. Prompt And Protocol Boundaries

- [x] 1.1 Harden `skills/flowpilot/SKILL.md` dispatch guidance with disposition-specific Controller behavior.
- [x] 1.2 Harden `skills/flowpilot/SKILL.md` packet-work guidance so role ACK/open/submit happens only inside an isolated AI execution surface.
- [x] 1.3 Harden `skills/flowpilot/references/protocol.md` role-binding and resume wording around runtime-named surfaces, unreachable reuse surfaces, and host-neutral execution mechanisms.
- [x] 1.4 Add a focused failure-mode entry for fresh-surface substitution during `reuse_existing_role`.
- [x] 1.5 Align `runtime_kit` lifecycle resume wording with host-neutral isolated AI execution surface terminology if current text is narrower.

## 2. Validation Coverage

- [x] 2.1 Add a focused unit test proving active prompt/protocol surfaces contain the disposition table, host-neutral surface contract, foreground role-work prohibition, and unreachable-reuse recovery rule.
- [x] 2.2 Extend the FlowGuard prompt-boundary model and runner checks for the same isolated-surface drift hazards.

## 3. Verification And Sync

- [x] 3.1 Run the OpenSpec verification contract checks for `harden-isolated-role-surface-binding`.
- [x] 3.2 Run targeted prompt-boundary unit and FlowGuard checks.
- [x] 3.3 Run meta and capability FlowGuard regressions, using background artifacts when needed.
- [x] 3.4 Sync the repo-owned FlowPilot skill to the local Codex install and audit installed-skill freshness.
- [x] 3.5 Run install self-checks and topology rebuild/check if changed surfaces require it.
- [x] 3.6 Inspect git status and verify no peer work was reverted or unintentionally included.
