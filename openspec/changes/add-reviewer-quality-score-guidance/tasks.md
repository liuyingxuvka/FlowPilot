## 1. Prompt And Runtime Guidance

- [x] 1.1 Add the strict text-only Reviewer quality score rubric to Reviewer core guidance.
- [x] 1.2 Add score-scale interpretation and PM-owned optimization choice to PM core guidance.
- [x] 1.3 Add score-scale repair decision guidance to the PM review-repair phase card.
- [x] 1.4 Add authorized Reviewer score context handling to Worker core guidance.
- [x] 1.5 Update current-scope repair packet instruction text so repair workers see score/quantity context through existing authorized materials.

## 2. Fake-AI Matrix

- [x] 2.1 Extend review-window fake-AI profile ids with high-score pass, soft low-score pass, quantitative hard blocker, overblocked soft score, and score-context recheck cases.
- [x] 2.2 Generate fake-AI payloads for each new profile using existing review report fields only.
- [x] 2.3 Map new profile ids into the existing Cartesian control-plane mutation canonicalization.

## 3. Tests

- [x] 3.1 Add prompt coverage tests for Reviewer rubric, PM interpretation, PM always-owned optimization choice, and Worker score-context handling.
- [x] 3.2 Add contract-surface tests proving score guidance does not add runtime result fields.
- [x] 3.3 Add runtime tests proving scored Reviewer blocker context reaches PM repair packets and repair workers, while soft sub-9 pass does not create a blocker.
- [x] 3.4 Add fake-AI and matrix tests proving the new score profiles are declared and Cartesian.

## 4. Validation And Sync

- [x] 4.1 Run focused OpenSpec, FlowGuard, prompt, runtime, fake-AI, and matrix validations.
- [x] 4.2 Update version/changelog/readme release text for the local source version.
- [x] 4.3 Rebuild/check topology if changed surfaces require it.
- [x] 4.4 Sync the repo-owned FlowPilot install and audit local install state.
- [x] 4.5 Commit the completed local repository state without reverting peer-agent work.
