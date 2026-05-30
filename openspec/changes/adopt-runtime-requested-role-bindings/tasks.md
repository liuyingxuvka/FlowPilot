## 1. Prompt And Protocol Text

- [x] 1.1 Update the FlowPilot skill entrypoint and active runtime cards/prompts to use current requested role binding language.
- [x] 1.2 Update public protocol/schema/reviewer/design docs so active guidance no longer presents fixed role counts as current authority.
- [x] 1.3 Update skill reference docs to either use runtime-requested role binding language or mark historical fixed-crew wording as non-authoritative.

## 2. FlowGuard Models And Tests

- [x] 2.1 Update focused runtime/new-entrypoint models that already reject historical role-topology requirements to cover prompt residue.
- [x] 2.2 Update affected development, startup, prompt-isolation, and resume-facing model labels/messages to runtime-required role-binding wording where they touch active guidance.
- [x] 2.3 Update unit tests and runner contracts that assert historical startup role-count wording or broad spawn-policy text.

## 3. Validation And Synchronization

- [x] 3.1 Run focused prompt/card, new-entrypoint, startup/recovery, and OpenSpec validation checks.
- [x] 3.2 Run or background the broader FlowGuard model regressions needed for touched model families and inspect final artifacts.
- [x] 3.3 Rebuild/check the FlowGuard project topology after model, runner, prompt, or evidence-surface changes.
- [x] 3.4 Synchronize the installed FlowPilot skill and run install self-checks.
- [x] 3.5 Stage and commit the completed change after verification.
