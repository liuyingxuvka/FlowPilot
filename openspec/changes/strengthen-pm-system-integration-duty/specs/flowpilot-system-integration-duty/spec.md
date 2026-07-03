## ADDED Requirements

### Requirement: PM owns the system integration thread
FlowPilot SHALL make the Project Manager the explicit owner of system integration from product architecture through terminal closure.

#### Scenario: Product architecture records root integration intent
- **WHEN** PM creates the product-function architecture
- **THEN** the artifact SHALL record the intended whole-product structure, required continuity, required cross-part callbacks or handoffs, duplicate-vs-reinforcement policy, and artifact-family-specific integration risks.

#### Scenario: Route skeleton records composition duties
- **WHEN** PM drafts or revises the route skeleton
- **THEN** the route SHALL explain how child nodes compose into each parent, how sibling nodes relate, and how producer-before-consumer order preserves the root integration intent.

#### Scenario: Node plan records local integration touchpoint
- **WHEN** PM creates a node acceptance plan
- **THEN** the plan SHALL record the node's upstream input relation, downstream output relation, sibling duplication/conflict risks, and parent contribution outside `node_context_package`.

#### Scenario: PM absorbs result against integration touchpoint
- **WHEN** PM absorbs a worker or role result for the current node
- **THEN** PM SHALL consider whether the result preserves upstream continuity, creates downstream handoff material, avoids sibling conflict, and still contributes to the parent goal.

### Requirement: Parent and final replay judge composition, not only local completion
FlowPilot SHALL reject local-only completion evidence when the effective child or node results do not compose into the parent or root goal.

#### Scenario: Parent replay finds scattered children
- **WHEN** all child nodes have local pass evidence but their outputs do not compose into the parent goal
- **THEN** parent backward replay SHALL classify the finding through the existing parent repair, add-sibling, rebuild-subtree, bubble-up, or PM-stop decisions.

#### Scenario: Final replay starts from delivered artifact
- **WHEN** final backward replay evaluates a delivered software artifact, report, writing artifact, UI, or skill workflow
- **THEN** the Reviewer SHALL judge the delivered artifact as one artifact before relying on node-level evidence.

#### Scenario: Node-local FlowGuard evidence is not terminal integration proof
- **WHEN** scattered node-level FlowGuard notes exist without a final whole-output composition review
- **THEN** terminal closure SHALL NOT treat those notes as sufficient final integration evidence.

### Requirement: Integration misses enter model-miss triage
FlowPilot SHALL treat "locally complete but globally incoherent" as a modelable miss when it escapes earlier FlowGuard, PM, or Reviewer stages.

#### Scenario: Escaped scattered output triggers model-miss analysis
- **WHEN** final or parent review finds a hard scattered-output defect after earlier local passes
- **THEN** PM model-miss triage SHALL ask whether product architecture, route process, node integration touchpoints, parent replay, final replay, or tests failed to model the defect class.

#### Scenario: Advisory integration suggestion stays advisory
- **WHEN** the issue is only a higher-standard simplification or polish opportunity and the current gate minimum is met
- **THEN** PM SHALL record the item as decision support or a nonblocking FlowPilot improvement rather than hard-blocking the route.
