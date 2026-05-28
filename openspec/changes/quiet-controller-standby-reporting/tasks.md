## 1. OpenSpec And FlowGuard Grounding

- [x] 1.1 Validate OpenSpec change artifacts and confirm modified capability scope.
- [x] 1.2 Verify real FlowGuard import and update focused model obligations for patrol cadence and reporting silence.

## 2. Runtime And Prompt Changes

- [x] 2.1 Change the default foreground Controller patrol interval to 60 seconds without changing Router daemon tick or heartbeat thresholds.
- [x] 2.2 Update skill docs, Controller role card, resume/reentry card, and generated table prompt wording to use quiet reporting rules.
- [x] 2.3 Ensure standby payloads and prompt delivery expose the 60-second patrol command consistently.

## 3. Tests And Validation

- [x] 3.1 Update targeted unit tests for default patrol command, prompt rendering, standby payloads, and speak/silence policy.
- [x] 3.2 Run focused FlowGuard and unit checks for controller patrol, process asides, controller status, prompt store, and router foreground behavior.
- [x] 3.3 Run heavyweight meta/capability regression checks in background logs and inspect completion artifacts.

## 4. Install Sync And Git

- [x] 4.1 Sync repo-owned FlowPilot assets into the local installed skill.
- [x] 4.2 Run install audit and install check against the local installed copy.
- [x] 4.3 Review final git status, preserve peer-agent changes, stage scoped files, and create a local git commit.
