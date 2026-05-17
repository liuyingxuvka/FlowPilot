## 1. OpenSpec And FlowGuard Planning

- [x] 1.1 Create the OpenSpec proposal, design, and requirements.
- [x] 1.2 Verify real FlowGuard import before changing validation artifacts.

## 2. Runtime Oracle Split

- [x] 2.1 Split the monolithic route-mutation runtime oracle into focused child modules.
- [x] 2.2 Keep the old aggregate module as a compatibility load-tests entrypoint.
- [x] 2.3 Ensure the split is mechanical and does not change runtime assertions.

## 3. TestMesh And Alignment Updates

- [x] 3.1 Replace `router_route_mutation_core` in routine tiers with child commands.
- [x] 3.2 Update tier tests to require the focused route-mutation child suites.
- [x] 3.3 Clear stale background artifacts before relaunching a child suite.
- [x] 3.4 Update FlowGuard StructureMesh/TestMesh evidence for child ownership and background artifacts.
- [x] 3.5 Update Model-Test Alignment evidence and docs.

## 4. Documentation And Sync

- [x] 4.1 Update verification, handoff, README, and adoption notes.
- [x] 4.2 Synchronize the local installed FlowPilot skill from the repo-owned source.

## 5. Validation

- [x] 5.1 Run focused child route-mutation tests.
- [x] 5.2 Run parent contract and tier tests.
- [x] 5.3 Run FlowGuard StructureMesh and Model-Test Alignment checks.
- [x] 5.4 Run router-route in background and inspect final artifacts, not progress lines.
- [x] 5.5 Run install sync/audit checks.
- [x] 5.6 Stage and commit the local repository version.
