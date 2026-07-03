## 1. OpenSpec and FlowGuard framing

- [x] 1.1 Capture lifecycle/disposition-based progress semantics in OpenSpec.
- [x] 1.2 Validate the OpenSpec change before implementation.
- [x] 1.3 Ground the implementation in route replanning, route mutation activation, and recursive route execution FlowGuard models.

## 2. Runtime implementation

- [x] 2.1 Update `current_progress_fraction` to count current-run expanded route nodes from `route_nodes`, not active `node_order` alone.
- [x] 2.2 Preserve the display-only initial planning node for the no-node and post-materialization cases.
- [x] 2.3 Keep packet projection permanently disabled and keep control-plane mechanics excluded.
- [x] 2.4 Preserve ended-node semantics for accepted, waived, blocked, and stopped nodes while allowing formally superseded nodes to leave the denominator.

## 3. Regression coverage

- [x] 3.1 Add a regression where a later one-node materialization overwrites active `node_order` but earlier undispositioned nodes still count.
- [x] 3.2 Add or update coverage for formal supersession and active-route short-list behavior.
- [x] 3.3 Re-run focused progress tests and route lifecycle FlowGuard checks.

## 4. Sync and closure

- [x] 4.1 Rebuild/check topology if source/model/test evidence stales it.
- [x] 4.2 Sync the repository-owned FlowPilot skill into the local installed skill directory.
- [x] 4.3 Verify install digests and local install checks.
- [x] 4.4 Commit the scoped repository changes without staging peer-agent artifacts.

## 5. Cartesian coverage hardening

- [x] 5.1 Declare the progress lifecycle finite Cartesian universe and FlowGuard ContractExhaustion/TestMesh evidence path.
- [x] 5.2 Add a dedicated progress lifecycle Cartesian model and runner.
- [x] 5.3 Bind the Cartesian runner to runtime `current_progress_fraction` outputs for every generated cell.
- [x] 5.4 Add pytest coverage for persisted matrix evidence, axis coverage, node_order independence, removed statuses, and TestMesh consumption.
- [x] 5.5 Re-run the expanded verification contract, install sync, and topology checks.
